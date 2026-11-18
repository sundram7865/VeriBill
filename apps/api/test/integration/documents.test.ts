import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { authHeader, startTestApp, type TestContext } from '../helpers/app';
import { createTenant, resetDatabase, type TenantFixture } from '../helpers/db';
import { pdfWithPages, tinyPdf, tinyPng, uploadForm } from '../helpers/files';
import { call } from '../helpers/http';

let ctx: TestContext;
let acme: TenantFixture;

beforeAll(async () => {
  ctx = await startTestApp();
});
afterAll(async () => ctx.close());
beforeEach(async () => {
  await resetDatabase(ctx.deps.db);
  ctx.deps.queue.jobs = [];
  acme = await createTenant(ctx.deps.db, 'Acme');
});

async function upload(files: Array<{ name: string; data: Buffer; type: string }>) {
  return call(ctx.baseUrl, '/documents', {
    method: 'POST',
    headers: authHeader(acme.reviewer),
    body: await uploadForm(files),
  });
}

describe('uploads', () => {
  it('stores valid files, queues them and reports rejects per file', async () => {
    const res = await upload([
      { name: 'invoice.pdf', data: tinyPdf('one'), type: 'application/pdf' },
      { name: 'scan.png', data: tinyPng(), type: 'image/png' },
      // Lies about its type: the magic bytes decide, not the name or content-type.
      { name: 'evil.pdf', data: Buffer.from('MZ not a pdf'), type: 'application/pdf' },
    ]);
    expect(res.status).toBe(201);
    expect(res.body.documents).toHaveLength(2);
    expect(res.body.rejected).toEqual([
      expect.objectContaining({ name: 'evil.pdf', code: 'unsupported_type' }),
    ]);
    expect(ctx.deps.queue.jobs).toHaveLength(2);
    expect(ctx.deps.queue.jobs[0]).toMatchObject({ tenantId: acme.tenantId, attempt: 1 });
  });

  it('rejects PDFs over the page limit', async () => {
    const res = await upload([
      { name: 'long.pdf', data: pdfWithPages(21), type: 'application/pdf' },
    ]);
    expect(res.status).toBe(422);
    expect(res.body.rejected[0].code).toBe('too_many_pages');
  });

  it('refuses the exact same file twice', async () => {
    const data = tinyPdf('same');
    const first = await upload([{ name: 'a.pdf', data, type: 'application/pdf' }]);
    const second = await upload([{ name: 'b.pdf', data, type: 'application/pdf' }]);
    expect(second.body.rejected[0]).toMatchObject({
      code: 'duplicate_file',
      existingDocumentId: first.body.documents[0].id,
    });
  });

  it('streams the file back after auth, without exposing storage ids', async () => {
    const data = tinyPdf('stream me');
    const res = await upload([{ name: 'inv.pdf', data, type: 'application/pdf' }]);
    const doc = res.body.documents[0];
    expect(JSON.stringify(doc)).not.toContain('storage');

    const file = await fetch(`${ctx.baseUrl}/documents/${doc.id}/file`, {
      headers: authHeader(acme.reviewer),
    });
    expect(file.status).toBe(200);
    expect(file.headers.get('content-type')).toBe('application/pdf');
    expect(file.headers.get('cache-control')).toContain('no-store');
    expect(Buffer.from(await file.arrayBuffer()).equals(data)).toBe(true);
    expect((await fetch(`${ctx.baseUrl}/documents/${doc.id}/file`)).status).toBe(401);
  });

  it('lists documents newest first with status filter', async () => {
    await upload([{ name: 'a.pdf', data: tinyPdf('a'), type: 'application/pdf' }]);
    await upload([{ name: 'b.pdf', data: tinyPdf('b'), type: 'application/pdf' }]);
    const all = await call(ctx.baseUrl, '/documents', { headers: authHeader(acme.admin) });
    expect(all.body.total).toBe(2);
    expect(all.body.items[0].originalName).toBe('b.pdf');
    const none = await call(ctx.baseUrl, '/documents?status=approved', {
      headers: authHeader(acme.admin),
    });
    expect(none.body.total).toBe(0);
  });

  it('only admins can reprocess', async () => {
    const res = await upload([{ name: 'a.pdf', data: tinyPdf('r'), type: 'application/pdf' }]);
    const id = res.body.documents[0].id;
    await ctx.deps.db.document.update({ where: { id }, data: { status: 'failed' } });
    const asReviewer = await call(ctx.baseUrl, `/documents/${id}/reprocess`, {
      method: 'POST',
      headers: authHeader(acme.reviewer),
    });
    expect(asReviewer.status).toBe(403);
    const asAdmin = await call(ctx.baseUrl, `/documents/${id}/reprocess`, {
      method: 'POST',
      headers: authHeader(acme.admin),
    });
    expect(asAdmin.status).toBe(202);
    expect(asAdmin.body.attempt).toBe(2);
    expect(ctx.deps.queue.jobs.at(-1)).toMatchObject({ documentId: id, attempt: 2 });
  });
});
