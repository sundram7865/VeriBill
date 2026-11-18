import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { documentsRepository } from '../../src/modules/documents/documents.repository';
import { reviewTasksRepository } from '../../src/modules/review/reviewTasks.repository';
import { authHeader, startTestApp, type TestContext } from '../helpers/app';
import { createTenant, resetDatabase, type TenantFixture } from '../helpers/db';
import { tinyPdf, uploadForm } from '../helpers/files';
import { call } from '../helpers/http';

let ctx: TestContext;
let acme: TenantFixture;
let globex: TenantFixture;

beforeAll(async () => {
  ctx = await startTestApp();
});
afterAll(async () => ctx.close());
beforeEach(async () => {
  await resetDatabase(ctx.deps.db);
  acme = await createTenant(ctx.deps.db, 'Acme');
  globex = await createTenant(ctx.deps.db, 'Globex');
});

async function uploadAsAcme(): Promise<string> {
  const res = await call(ctx.baseUrl, '/documents', {
    method: 'POST',
    headers: authHeader(acme.admin),
    body: await uploadForm([{ name: 'a.pdf', data: tinyPdf('acme'), type: 'application/pdf' }]),
  });
  expect(res.status).toBe(201);
  return res.body.documents[0].id;
}

describe('tenant isolation', () => {
  it('repositories cannot read another tenant’s rows', async () => {
    const id = await uploadAsAcme();
    const docs = documentsRepository(ctx.deps.db);
    expect(await docs.findById(acme.tenantId, id)).not.toBeNull();
    expect(await docs.findById(globex.tenantId, id)).toBeNull();
    expect(await docs.detail(globex.tenantId, id)).toBeNull();
    expect(await docs.update(globex.tenantId, id, { status: 'approved' })).toBe(false);
    expect((await docs.findById(acme.tenantId, id))?.status).toBe('uploaded');

    const task = await reviewTasksRepository(ctx.deps.db).create(acme.tenantId, id, 'needs_review');
    expect(await reviewTasksRepository(ctx.deps.db).findById(globex.tenantId, task.id)).toBeNull();
  });

  it('repositories refuse to run without a tenant id', async () => {
    expect(() => documentsRepository(ctx.deps.db).findById('', 'x')).toThrow(/tenantId/);
  });

  it('HTTP reads of another tenant’s document return 404', async () => {
    const id = await uploadAsAcme();
    const other = authHeader(globex.admin);
    expect((await call(ctx.baseUrl, `/documents/${id}`, { headers: other })).status).toBe(404);
    expect((await call(ctx.baseUrl, `/documents/${id}/file`, { headers: other })).status).toBe(404);
    const list = await call(ctx.baseUrl, '/documents', { headers: other });
    expect(list.body.total).toBe(0);
    expect(
      (await call(ctx.baseUrl, `/documents/${id}`, { headers: authHeader(acme.reviewer) })).status,
    ).toBe(200);
  });

  it('a review task cannot be submitted from another tenant', async () => {
    const id = await uploadAsAcme();
    const task = await reviewTasksRepository(ctx.deps.db).create(acme.tenantId, id, 'needs_review');
    const res = await call(ctx.baseUrl, `/review-tasks/${task.id}/submit`, {
      method: 'POST',
      headers: authHeader(globex.reviewer),
      json: { action: 'approve', corrections: [] },
    });
    expect(res.status).toBe(404);
  });
});
