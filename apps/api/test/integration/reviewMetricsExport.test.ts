import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { documentsRepository } from '../../src/modules/documents/documents.repository';
import { processDocument } from '../../src/queue/processDocument';
import { authHeader, startTestApp, type TestContext } from '../helpers/app';
import { createTenant, resetDatabase, type TenantFixture } from '../helpers/db';
import { CLEAN_FIELDS, FakeExtractor, fakeResponse } from '../helpers/fakeExtractor';
import { tinyPdf } from '../helpers/files';
import { call } from '../helpers/http';

let ctx: TestContext;
let acme: TenantFixture;

beforeAll(async () => {
  ctx = await startTestApp();
});
afterAll(async () => ctx.close());
beforeEach(async () => {
  await resetDatabase(ctx.deps.db);
  acme = await createTenant(ctx.deps.db, 'Acme');
});

const MISREAD = { ...CLEAN_FIELDS, 'totals.grand_total': '1130.00' };

/** A processed document: needs_review with a flagged (wrong) grand total, or auto-approved. */
async function processed(label: string, kind: 'review' | 'auto' | 'audit') {
  const stored = await ctx.deps.storage.put(tinyPdf(label), {
    tenantId: acme.tenantId,
    mime: 'application/pdf',
  });
  const doc = await documentsRepository(ctx.deps.db).create(acme.tenantId, {
    uploadedById: acme.admin.id,
    storageProvider: stored.provider,
    storagePublicId: stored.publicId,
    storageResourceType: stored.resourceType,
    originalName: `${label}.pdf`,
    mime: 'application/pdf',
    sizeBytes: 100,
    pages: 1,
    contentHash: label,
  });
  const extractor = new FakeExtractor([
    (input) =>
      kind === 'review'
        ? fakeResponse(input, { decision: 'needs_review' }, MISREAD, ['totals.grand_total'])
        : fakeResponse(input, {}, { ...CLEAN_FIELDS, 'header.invoice_number': `INV-${label}` }),
  ]);
  const config = {
    AUDIT_SAMPLE_RATE: kind === 'audit' ? 1 : 0,
    FEW_SHOT_MAX_SUPPLIERS: 50,
    FEW_SHOT_PER_SUPPLIER: 3,
  };
  await processDocument(
    { documentId: doc.id, tenantId: acme.tenantId, attempt: 1 },
    { db: ctx.deps.db, storage: ctx.deps.storage, extractor, config },
  );
  const task = await ctx.deps.db.reviewTask.findFirst({ where: { documentId: doc.id } });
  return { doc, task };
}

function submit(taskId: string, body: unknown) {
  return call(ctx.baseUrl, `/review-tasks/${taskId}/submit`, {
    method: 'POST',
    headers: authHeader(acme.reviewer),
    json: body,
  });
}

describe('review', () => {
  it('lists open tasks and shows the document with fields, boxes and issues', async () => {
    const { doc, task } = await processed('r1', 'review');
    const tasks = await call(ctx.baseUrl, '/review-tasks', { headers: authHeader(acme.reviewer) });
    expect(tasks.body.items).toHaveLength(1);
    const detail = await call(ctx.baseUrl, `/documents/${doc.id}`, {
      headers: authHeader(acme.reviewer),
    });
    expect(detail.body.openTask.id).toBe(task?.id);
    const total = detail.body.fields.find((f: { path: string }) => f.path === 'totals.grand_total');
    expect(total).toMatchObject({ value: '1130.00', page: 1, bbox: [0.1, 0.1, 0.3, 0.12] });
    expect(total.issues[0].severity).toBe('error');
  });

  it('records corrections and approves into a normalized invoice', async () => {
    const { doc, task } = await processed('r2', 'review');
    const res = await submit(task!.id, {
      action: 'approve',
      corrections: [
        { fieldPath: 'totals.grand_total', after: '1,180.00', reason: 'misread 8 as 3' },
        { fieldPath: 'header.buyer_name', after: 'Deccan Foods LLP' }, // unchanged: not a correction
      ],
    });
    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({ outcome: 'approved', corrections: 1 });

    const corrections = await ctx.deps.db.correction.findMany();
    expect(corrections).toMatchObject([
      {
        fieldPath: 'totals.grand_total',
        before: '1130.00',
        after: '1,180.00',
        hadValidatorIssue: true,
      },
    ]);
    const invoice = await ctx.deps.db.invoice.findUnique({ where: { documentId: doc.id } });
    expect(invoice?.grandTotal?.toNumber()).toBe(1180);
    expect(invoice?.approvedVia).toBe('review');
    expect((await ctx.deps.db.document.findUnique({ where: { id: doc.id } }))?.status).toBe(
      'approved',
    );

    expect((await submit(task!.id, { action: 'approve' })).status).toBe(409); // already closed
  });

  it('validates corrected values by field type', async () => {
    const { task } = await processed('r3', 'review');
    const res = await submit(task!.id, {
      action: 'approve',
      corrections: [
        { fieldPath: 'header.invoice_date', after: '15/03/2026' },
        { fieldPath: 'totals.grand_total', after: 'eleven hundred' },
        { fieldPath: 'header.not_a_field', after: 'x' },
      ],
    });
    expect(res.status).toBe(400);
    expect(res.body.error.details).toHaveLength(3);
  });

  it('rejects a document', async () => {
    const { doc, task } = await processed('r4', 'review');
    expect((await submit(task!.id, { action: 'reject' })).body.outcome).toBe('rejected');
    expect((await ctx.deps.db.document.findUnique({ where: { id: doc.id } }))?.status).toBe(
      'rejected',
    );
  });
});

describe('metrics and export', () => {
  it('computes metrics from real activity', async () => {
    const review = await processed('m1', 'review');
    await submit(review.task!.id, {
      action: 'approve',
      corrections: [{ fieldPath: 'totals.grand_total', after: '1180.00' }],
    });
    const audit = await processed('m2', 'audit');
    await submit(audit.task!.id, { action: 'approve', corrections: [] });
    await processed('m3', 'auto');

    const res = await call(ctx.baseUrl, '/metrics?days=30', { headers: authHeader(acme.reviewer) });
    expect(res.status).toBe(200);
    const m = res.body;
    expect(m.extractionRuns).toBe(3);
    expect(m.autoApprovalRate).toBeCloseTo(2 / 3);
    expect(m.auditedDocuments).toBe(1);
    expect(m.auditedAccuracy).toBe(1);
    expect(m.corrections).toBe(1);
    expect(m.validatorCatchRate).toBe(1);
    expect(m.fieldCorrectionRate).toBeGreaterThan(0);
    expect(m.costPerDocumentUsd).toBeCloseTo(0.00054);
    expect(m.latencyMs.p50).toBe(1800);
    expect(m.documentsByStatus).toMatchObject({ approved: 1, auto_approved: 2 });
  });

  it('exports approved invoices as CSV and JSON for admins only', async () => {
    await processed('e1', 'auto');
    await processed('e2', 'review'); // still in review: not exported

    const forbidden = await call(ctx.baseUrl, '/export/invoices.csv', {
      headers: authHeader(acme.reviewer),
    });
    expect(forbidden.status).toBe(403);

    const csv = await call<string>(ctx.baseUrl, '/export/invoices.csv', {
      headers: authHeader(acme.admin),
    });
    const lines = csv.body.trim().split('\r\n');
    expect(lines[0]).toContain('line_no,document_id,invoice_number');
    expect(lines).toHaveLength(2);
    expect(lines[1]).toContain('INV-e1');
    expect(lines[1]).toContain('Copper Wire 2.5 sq mm');

    const json = await call(ctx.baseUrl, '/export/invoices.json', {
      headers: authHeader(acme.admin),
    });
    expect(json.body.invoices).toHaveLength(1);
    expect(json.body.invoices[0].totals.grandTotal).toBe(1180);
  });
});
