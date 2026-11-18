import type { Worker } from 'bullmq';
import { Queue } from 'bullmq';
import { Redis } from 'ioredis';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { ExtractorHttpError } from '../../src/extractor/extractorClient';
import { documentsRepository } from '../../src/modules/documents/documents.repository';
import { BullExtractionQueue } from '../../src/queue/bullmqQueue';
import { EXTRACTION_QUEUE_NAME, type ExtractionJobData } from '../../src/queue/extractionQueue';
import { createExtractionWorker } from '../../src/queue/extractionWorker';
import { processDocument } from '../../src/queue/processDocument';
import { startTestApp, type TestContext } from '../helpers/app';
import { createTenant, resetDatabase, type TenantFixture } from '../helpers/db';
import { CLEAN_FIELDS, FakeExtractor, fakeResponse } from '../helpers/fakeExtractor';
import { tinyPdf } from '../helpers/files';

let ctx: TestContext;
let acme: TenantFixture;
let connection: Redis;
let queue: BullExtractionQueue;
let worker: Worker<ExtractionJobData> | undefined;

const config = { AUDIT_SAMPLE_RATE: 0, FEW_SHOT_MAX_SUPPLIERS: 50, FEW_SHOT_PER_SUPPLIER: 3 };

beforeAll(async () => {
  ctx = await startTestApp();
  connection = new Redis(ctx.deps.config.REDIS_URL, { maxRetriesPerRequest: null });
  queue = new BullExtractionQueue(connection, { attempts: 3, backoffMs: 50 });
});
afterAll(async () => {
  await queue.close();
  await connection.quit();
  await ctx.close();
});
beforeEach(async () => {
  await resetDatabase(ctx.deps.db);
  const raw = new Queue(EXTRACTION_QUEUE_NAME, { connection });
  await raw.obliterate({ force: true });
  await raw.close();
  acme = await createTenant(ctx.deps.db, 'Acme');
});
afterEach(async () => {
  await worker?.close();
  worker = undefined;
});

async function newDocument(label: string) {
  const stored = await ctx.deps.storage.put(tinyPdf(label), {
    tenantId: acme.tenantId,
    mime: 'application/pdf',
  });
  return documentsRepository(ctx.deps.db).create(acme.tenantId, {
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
}

function startWorker(extractor: FakeExtractor) {
  worker = createExtractionWorker(
    connection,
    { db: ctx.deps.db, storage: ctx.deps.storage, extractor, config },
    1,
  );
}

async function waitForStatus(id: string, statuses: string[], timeoutMs = 15_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const doc = await ctx.deps.db.document.findUnique({ where: { id } });
    if (doc && statuses.includes(doc.status)) return doc;
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error(`document ${id} never reached ${statuses.join('/')}`);
}

const http = (status: number, code: string) => () => {
  throw new ExtractorHttpError(status, code, `fake ${status}`);
};

describe('extraction queue', () => {
  it('happy path: stores the run, fields and invoice, and auto-approves', async () => {
    const extractor = new FakeExtractor([(input) => fakeResponse(input)]);
    startWorker(extractor);
    const doc = await newDocument('happy');
    await queue.enqueue({ documentId: doc.id, tenantId: acme.tenantId, attempt: 1 });

    const done = await waitForStatus(doc.id, ['auto_approved', 'failed']);
    expect(done.status).toBe('auto_approved');
    expect(extractor.calls[0]?.bytes.equals(tinyPdf('happy'))).toBe(true);
    expect(extractor.calls[0]?.metadata).toMatchObject({ document_id: doc.id, attempt: 1 });
    const runs = await ctx.deps.db.extractionRun.findMany({ where: { documentId: doc.id } });
    expect(runs).toHaveLength(1);
    expect(runs[0]).toMatchObject({ attempt: 1, tokensIn: 2400, decision: 'auto_approve' });
    expect(await ctx.deps.db.extractedField.count({ where: { documentId: doc.id } })).toBe(
      Object.keys(CLEAN_FIELDS).length,
    );
    const invoice = await ctx.deps.db.invoice.findUnique({ where: { documentId: doc.id } });
    expect(invoice?.grandTotal?.toNumber()).toBe(1180);
    expect(invoice?.approvedVia).toBe('auto');
  });

  it('routes uncertain documents to a review task', async () => {
    startWorker(
      new FakeExtractor([
        (input) =>
          fakeResponse(input, { decision: 'needs_review' }, CLEAN_FIELDS, ['totals.grand_total']),
      ]),
    );
    const doc = await newDocument('unsure');
    await queue.enqueue({ documentId: doc.id, tenantId: acme.tenantId, attempt: 1 });
    await waitForStatus(doc.id, ['needs_review']);
    const tasks = await ctx.deps.db.reviewTask.findMany({ where: { documentId: doc.id } });
    expect(tasks).toMatchObject([{ type: 'needs_review', status: 'open' }]);
    expect(await ctx.deps.db.invoice.count()).toBe(0);
  });

  it('retries a transient extractor failure, then succeeds', async () => {
    const extractor = new FakeExtractor([
      http(503, 'internal_error'),
      (input) => fakeResponse(input),
    ]);
    startWorker(extractor);
    const doc = await newDocument('flaky');
    await queue.enqueue({ documentId: doc.id, tenantId: acme.tenantId, attempt: 1 });
    expect((await waitForStatus(doc.id, ['auto_approved', 'failed'])).status).toBe('auto_approved');
    expect(extractor.calls).toHaveLength(2);
  });

  it('marks the document failed after the last retry', async () => {
    const extractor = new FakeExtractor([http(502, 'llm_error')]);
    startWorker(extractor);
    const doc = await newDocument('broken');
    await queue.enqueue({ documentId: doc.id, tenantId: acme.tenantId, attempt: 1 });
    const failed = await waitForStatus(doc.id, ['failed']);
    expect(extractor.calls).toHaveLength(3);
    expect(failed.errorMessage).toContain('fake 502');
  });

  it('does not retry a request that can never succeed (4xx, budget cap)', async () => {
    const extractor = new FakeExtractor([http(429, 'llm_budget_exceeded')]);
    startWorker(extractor);
    const doc = await newDocument('over-budget');
    await queue.enqueue({ documentId: doc.id, tenantId: acme.tenantId, attempt: 1 });
    const failed = await waitForStatus(doc.id, ['failed']);
    expect(extractor.calls).toHaveLength(1);
    expect(failed.errorMessage).toContain('llm_budget_exceeded');
  });

  it('is idempotent on document id + attempt', async () => {
    const extractor = new FakeExtractor([(input) => fakeResponse(input)]);
    const doc = await newDocument('twice');
    const job = { documentId: doc.id, tenantId: acme.tenantId, attempt: 1 };
    const deps = { db: ctx.deps.db, storage: ctx.deps.storage, extractor, config };
    expect((await processDocument(job, deps)).kind).toBe('stored');
    expect(await processDocument(job, deps)).toEqual({
      kind: 'skipped',
      reason: 'already processed',
    });
    expect(await processDocument({ ...job, attempt: 0 }, deps)).toEqual({
      kind: 'skipped',
      reason: 'stale attempt',
    });
    expect(await ctx.deps.db.extractionRun.count({ where: { documentId: doc.id } })).toBe(1);
    expect(extractor.calls).toHaveLength(1);
  });

  it('flags a re-scan of an existing invoice as a duplicate for review', async () => {
    const extractor = new FakeExtractor([(input) => fakeResponse(input)]);
    const deps = { db: ctx.deps.db, storage: ctx.deps.storage, extractor, config };
    const first = await newDocument('original');
    const second = await newDocument('rescan');
    await processDocument({ documentId: first.id, tenantId: acme.tenantId, attempt: 1 }, deps);
    await processDocument({ documentId: second.id, tenantId: acme.tenantId, attempt: 1 }, deps);
    const dup = await ctx.deps.db.document.findUnique({ where: { id: second.id } });
    expect(dup).toMatchObject({ status: 'needs_review', duplicateOfId: first.id });
  });

  it('samples auto-approved documents into audit tasks', async () => {
    const extractor = new FakeExtractor([(input) => fakeResponse(input)]);
    const deps = {
      db: ctx.deps.db,
      storage: ctx.deps.storage,
      extractor,
      config: { ...config, AUDIT_SAMPLE_RATE: 1 },
    };
    const doc = await newDocument('audit-me');
    await processDocument({ documentId: doc.id, tenantId: acme.tenantId, attempt: 1 }, deps);
    const tasks = await ctx.deps.db.reviewTask.findMany({ where: { documentId: doc.id } });
    expect(tasks).toMatchObject([{ type: 'audit', status: 'open' }]);
    expect((await ctx.deps.db.document.findUnique({ where: { id: doc.id } }))?.status).toBe(
      'auto_approved',
    );
  });
});
