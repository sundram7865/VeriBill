import type { PrismaClient } from '@prisma/client';
import { ZodError } from 'zod';
import type { Env } from '../config/env';
import { ExtractorHttpError, type ExtractorClient } from '../extractor/extractorClient';
import { recordAudit } from '../modules/audit/auditLog';
import { documentsRepository } from '../modules/documents/documents.repository';
import { runsRepository } from '../modules/extraction/runs.repository';
import { fewShotRepository } from '../modules/fewShot/fewShot.repository';
import type { StorageProvider } from '../storage/storageProvider';
import type { ExtractionJobData } from './extractionQueue';
import { persistExtraction, type PersistOutcome } from './persistExtraction';

/** Retrying cannot help (bad file, budget exhausted, contract violation). */
export class UnrecoverableJobError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'UnrecoverableJobError';
  }
}

export interface ProcessDeps {
  db: PrismaClient;
  storage: StorageProvider;
  extractor: ExtractorClient;
  config: Pick<Env, 'AUDIT_SAMPLE_RATE' | 'FEW_SHOT_MAX_SUPPLIERS' | 'FEW_SHOT_PER_SUPPLIER'>;
}

export type ProcessOutcome = PersistOutcome | { kind: 'skipped'; reason: string };

function classify(err: unknown): Error {
  if (err instanceof ExtractorHttpError && !err.retryable) {
    return new UnrecoverableJobError(`${err.code}: ${err.message}`);
  }
  if (err instanceof ZodError) {
    return new UnrecoverableJobError('Extractor response did not match the contract');
  }
  return err instanceof Error ? err : new Error(String(err));
}

export async function processDocument(
  job: ExtractionJobData,
  deps: ProcessDeps,
): Promise<ProcessOutcome> {
  const docs = documentsRepository(deps.db);
  const doc = await docs.findById(job.tenantId, job.documentId);
  if (!doc) throw new UnrecoverableJobError('Document not found');
  // Idempotency: an outdated job, or one whose run is already stored, does nothing.
  if (doc.processingAttempt !== job.attempt) return { kind: 'skipped', reason: 'stale attempt' };
  if (await runsRepository(deps.db).find(job.tenantId, doc.id, job.attempt)) {
    return { kind: 'skipped', reason: 'already processed' };
  }
  if (doc.status !== 'uploaded' && doc.status !== 'processing') {
    return { kind: 'skipped', reason: `status is ${doc.status}` };
  }

  await docs.update(job.tenantId, doc.id, { status: 'processing', errorMessage: null });
  const bytes = await deps.storage.get({
    publicId: doc.storagePublicId,
    resourceType: doc.storageResourceType,
  });
  const fewShot = await fewShotRepository(deps.db).forTenant(
    job.tenantId,
    deps.config.FEW_SHOT_MAX_SUPPLIERS,
    deps.config.FEW_SHOT_PER_SUPPLIER,
  );

  let result;
  try {
    result = await deps.extractor.extract({
      bytes,
      filename: doc.originalName,
      mime: doc.mime,
      metadata: {
        document_id: doc.id,
        attempt: job.attempt,
        filename: doc.originalName,
        few_shot: fewShot,
      },
    });
  } catch (err) {
    throw classify(err);
  }
  return persistExtraction(deps.db, doc, job.attempt, result, deps.config.AUDIT_SAMPLE_RATE);
}

/** Final failure: the document leaves "processing" with a reason the UI can show. */
export async function markFailed(
  db: PrismaClient,
  job: ExtractionJobData,
  reason: string,
): Promise<void> {
  const docs = documentsRepository(db);
  const updated = await docs.update(job.tenantId, job.documentId, {
    status: 'failed',
    errorMessage: reason.slice(0, 500),
  });
  if (updated) {
    await recordAudit(db, {
      tenantId: job.tenantId,
      actorId: null,
      action: 'document.failed',
      entityType: 'document',
      entityId: job.documentId,
      meta: { attempt: job.attempt },
    });
  }
}
