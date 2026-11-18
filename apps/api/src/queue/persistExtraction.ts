import { Prisma, type Document, type DocumentStatus, type PrismaClient } from '@prisma/client';
import type { ExtractResponse } from '../extractor/extractorSchemas';
import { recordAudit } from '../modules/audit/auditLog';
import { documentsRepository } from '../modules/documents/documents.repository';
import { fieldsRepository } from '../modules/extraction/fields.repository';
import { runsRepository } from '../modules/extraction/runs.repository';
import { buildInvoiceRecord } from '../modules/invoices/invoiceRecord';
import { invoicesRepository } from '../modules/invoices/invoices.repository';
import { shouldAudit } from '../modules/review/auditSampling';
import { reviewTasksRepository } from '../modules/review/reviewTasks.repository';

export type PersistOutcome =
  | {
      kind: 'stored';
      status: DocumentStatus;
      runId: string;
      duplicateOf: string | null;
      audited: boolean;
    }
  | { kind: 'already_processed' };

function isUniqueViolation(err: unknown): boolean {
  return err instanceof Prisma.PrismaClientKnownRequestError && err.code === 'P2002';
}

function statusFor(decision: ExtractResponse['decision'], isDuplicate: boolean): DocumentStatus {
  if (decision === 'reject') return 'rejected';
  // A possible duplicate always gets human eyes, however confident the extraction was.
  if (isDuplicate || decision === 'needs_review') return 'needs_review';
  return 'auto_approved';
}

/**
 * Stores one extraction result atomically: run, fields, document status, and the follow-up
 * (review task, or invoice record plus optional audit task). The unique (document, attempt)
 * index makes a retried job a no-op instead of a second copy.
 */
export async function persistExtraction(
  db: PrismaClient,
  doc: Document,
  attempt: number,
  result: ExtractResponse,
  auditRate: number,
): Promise<PersistOutcome> {
  const tenantId = doc.tenantId;
  try {
    return await db.$transaction(async (tx) => {
      const run = await runsRepository(tx).create(tenantId, {
        documentId: doc.id,
        attempt,
        model: result.model ?? 'none',
        tokensIn: result.tokens_in,
        tokensOut: result.tokens_out,
        costUsd: result.cost_usd,
        latencyMs: result.latency_ms,
        nodeTimings: result.node_timings,
        repairAttempts: result.repair_attempts,
        decision: result.decision,
        documentConfidence: result.document_confidence,
        result: result as unknown as Prisma.InputJsonValue,
      });
      await fieldsRepository(tx).createMany(
        tenantId,
        doc.id,
        run.id,
        result.fields.map((f) => ({
          path: f.path,
          value: f.value,
          confidence: f.confidence,
          page: f.page,
          bbox: f.bbox,
          issues: f.issues,
        })),
      );

      const record = buildInvoiceRecord(result.fields);
      const docs = documentsRepository(tx);
      const duplicate = record.dedupeKey
        ? await docs.findByDedupeKey(tenantId, record.dedupeKey, doc.id)
        : null;
      const status = statusFor(result.decision, duplicate !== null);
      await docs.update(tenantId, doc.id, {
        status,
        pages: result.pages,
        dedupeKey: record.dedupeKey,
        duplicateOfId: duplicate?.id ?? null,
        documentConfidence: result.document_confidence,
        errorMessage: status === 'rejected' ? result.decision_reason : null,
      });

      const tasks = reviewTasksRepository(tx);
      let audited = false;
      if (status === 'needs_review') await tasks.create(tenantId, doc.id, 'needs_review');
      if (status === 'auto_approved') {
        await invoicesRepository(tx).upsertForDocument(tenantId, doc.id, record, 'auto');
        audited = shouldAudit(doc.id, auditRate);
        if (audited) await tasks.create(tenantId, doc.id, 'audit');
      }
      await recordAudit(tx, {
        tenantId,
        actorId: null,
        action: `document.${status}`,
        entityType: 'document',
        entityId: doc.id,
        meta: { attempt, runId: run.id, duplicateOf: duplicate?.id ?? null, audited },
      });
      return {
        kind: 'stored' as const,
        status,
        runId: run.id,
        duplicateOf: duplicate?.id ?? null,
        audited,
      };
    });
  } catch (err) {
    if (isUniqueViolation(err)) return { kind: 'already_processed' };
    throw err;
  }
}
