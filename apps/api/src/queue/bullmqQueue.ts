import { Queue } from 'bullmq';
import type { Redis } from 'ioredis';
import {
  EXTRACTION_QUEUE_NAME,
  extractionJobId,
  type ExtractionJobData,
  type ExtractionQueue,
} from './extractionQueue';

interface BullQueueOptions {
  attempts: number;
  backoffMs: number;
}

export class BullExtractionQueue implements ExtractionQueue {
  private readonly queue: Queue<ExtractionJobData>;

  constructor(
    connection: Redis,
    private readonly options: BullQueueOptions,
  ) {
    this.queue = new Queue<ExtractionJobData>(EXTRACTION_QUEUE_NAME, { connection });
  }

  async enqueue(job: ExtractionJobData): Promise<void> {
    await this.queue.add('extract', job, {
      jobId: extractionJobId(job),
      attempts: this.options.attempts,
      backoff: { type: 'exponential', delay: this.options.backoffMs },
      removeOnComplete: { age: 24 * 3600, count: 1000 },
      removeOnFail: { age: 7 * 24 * 3600 },
    });
  }

  async close(): Promise<void> {
    await this.queue.close();
  }
}
