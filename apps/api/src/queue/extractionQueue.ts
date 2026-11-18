export const EXTRACTION_QUEUE_NAME = 'extraction';

export interface ExtractionJobData {
  documentId: string;
  tenantId: string;
  /** Processing attempt for the document; part of the job id for idempotency. */
  attempt: number;
}

/** Producer side of the extraction queue, as seen by the HTTP app. */
export interface ExtractionQueue {
  enqueue(job: ExtractionJobData): Promise<void>;
  close(): Promise<void>;
}

/** Same document + attempt always maps to the same job id, so double-enqueues are no-ops. */
export function extractionJobId(job: Pick<ExtractionJobData, 'documentId' | 'attempt'>): string {
  return `extract-${job.documentId}-${job.attempt}`;
}
