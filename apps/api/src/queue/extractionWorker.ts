import { UnrecoverableError, Worker, type Job } from 'bullmq';
import type { Redis } from 'ioredis';
import { logger } from '../lib/logger';
import { EXTRACTION_QUEUE_NAME, type ExtractionJobData } from './extractionQueue';
import {
  markFailed,
  processDocument,
  UnrecoverableJobError,
  type ProcessDeps,
} from './processDocument';

function isLastAttempt(job: Job<ExtractionJobData>): boolean {
  return job.attemptsMade + 1 >= (job.opts.attempts ?? 1);
}

/**
 * BullMQ consumer. Retries with exponential backoff come from the job options; this wrapper
 * decides when a failure is final and records it on the document.
 */
export function createExtractionWorker(
  connection: Redis,
  deps: ProcessDeps,
  concurrency: number,
): Worker<ExtractionJobData> {
  const worker = new Worker<ExtractionJobData>(
    EXTRACTION_QUEUE_NAME,
    async (job) => {
      const log = logger.child({ jobId: job.id, documentId: job.data.documentId });
      try {
        const outcome = await processDocument(job.data, deps);
        log.info(
          { outcome: outcome.kind, status: 'status' in outcome ? outcome.status : undefined },
          'job done',
        );
        return outcome;
      } catch (err) {
        const unrecoverable = err instanceof UnrecoverableJobError;
        const message = err instanceof Error ? err.message : String(err);
        log.warn({ attempt: job.attemptsMade + 1, unrecoverable, error: message }, 'job failed');
        if (unrecoverable || isLastAttempt(job)) await markFailed(deps.db, job.data, message);
        if (unrecoverable) throw new UnrecoverableError(message);
        throw err;
      }
    },
    { connection, concurrency },
  );
  worker.on('error', (err) => logger.error({ err }, 'worker error'));
  return worker;
}
