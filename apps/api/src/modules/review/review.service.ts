import type { ExtractedField, ReviewTaskStatus, ReviewTaskType } from '@prisma/client';
import type { AppDeps } from '../../app.deps';
import { badRequest, conflict, notFound } from '../../lib/errors';
import type { AuthContext } from '../auth/auth.types';
import { recordAudit } from '../audit/auditLog';
import { documentsRepository } from '../documents/documents.repository';
import { fieldsRepository } from '../extraction/fields.repository';
import { runsRepository } from '../extraction/runs.repository';
import { valueProblem } from '../invoices/fieldTypes';
import { buildInvoiceRecord } from '../invoices/invoiceRecord';
import { invoicesRepository } from '../invoices/invoices.repository';
import { correctionsRepository, type NewCorrection } from './corrections.repository';
import { reviewTasksRepository } from './reviewTasks.repository';

export interface CorrectionInput {
  fieldPath: string;
  after: string | null;
  reason?: string;
}

export interface SubmitInput {
  action: 'approve' | 'reject';
  corrections: CorrectionInput[];
}

function normalizeAfter(value: string | null): string | null {
  const trimmed = value?.trim() ?? '';
  return trimmed === '' ? null : trimmed;
}

function validateCorrections(corrections: CorrectionInput[], byPath: Map<string, ExtractedField>) {
  const problems = corrections.flatMap((c) => {
    if (!byPath.has(c.fieldPath)) return [{ path: c.fieldPath, message: 'unknown field' }];
    const problem = valueProblem(c.fieldPath, normalizeAfter(c.after));
    return problem ? [{ path: c.fieldPath, message: problem }] : [];
  });
  if (problems.length > 0) throw badRequest('Some corrections are invalid', problems);
}

export function reviewService(deps: AppDeps) {
  return {
    list(
      ctx: AuthContext,
      query: { status?: ReviewTaskStatus; type?: ReviewTaskType; limit: number },
    ) {
      return reviewTasksRepository(deps.db).list(ctx.tenantId, {
        status: query.status,
        type: query.type,
        take: query.limit,
      });
    },

    /**
     * Applies corrections, then approves or rejects, in one transaction. Corrections record the
     * before/after values, which become labelled data for evals and few-shot hints.
     */
    async submit(ctx: AuthContext, taskId: string, input: SubmitInput) {
      return deps.db.$transaction(async (tx) => {
        const tasks = reviewTasksRepository(tx);
        const task = await tasks.findById(ctx.tenantId, taskId);
        if (!task) throw notFound('Review task not found');
        if (task.status !== 'open') throw conflict('Review task is already closed');
        const run = await runsRepository(tx).latest(ctx.tenantId, task.documentId);
        if (!run) throw conflict('Document has no extraction to review');

        const fieldsRepo = fieldsRepository(tx);
        const fields = await fieldsRepo.listForRun(ctx.tenantId, run.id);
        const byPath = new Map(fields.map((f) => [f.path, f]));
        validateCorrections(input.corrections, byPath);

        const corrections: NewCorrection[] = [];
        for (const c of input.corrections) {
          const field = byPath.get(c.fieldPath) as ExtractedField;
          const after = normalizeAfter(c.after);
          if (after === field.value) continue; // not actually a change
          corrections.push({
            reviewTaskId: task.id,
            documentId: task.documentId,
            fieldPath: c.fieldPath,
            before: field.value,
            after,
            reason: c.reason?.trim() || null,
            hadValidatorIssue: Array.isArray(field.issues) && field.issues.length > 0,
            createdById: ctx.userId,
          });
          await fieldsRepo.updateValue(ctx.tenantId, field.id, after);
          byPath.set(c.fieldPath, { ...field, value: after });
        }
        await correctionsRepository(tx).createMany(ctx.tenantId, corrections);

        const outcome = input.action === 'approve' ? 'approved' : 'rejected';
        if (!(await tasks.close(ctx.tenantId, task.id, outcome, ctx.userId))) {
          throw conflict('Review task was closed by someone else');
        }

        const docs = documentsRepository(tx);
        const invoices = invoicesRepository(tx);
        if (input.action === 'approve') {
          const record = buildInvoiceRecord([...byPath.values()]);
          await invoices.upsertForDocument(ctx.tenantId, task.documentId, record, 'review');
          // An audited document stays "auto_approved": the audit checks the machine's decision.
          const status = task.type === 'audit' ? 'auto_approved' : 'approved';
          await docs.update(ctx.tenantId, task.documentId, { status, dedupeKey: record.dedupeKey });
        } else {
          await invoices.deleteForDocument(ctx.tenantId, task.documentId);
          await docs.update(ctx.tenantId, task.documentId, { status: 'rejected' });
        }
        await recordAudit(tx, {
          tenantId: ctx.tenantId,
          actorId: ctx.userId,
          action: `review.${outcome}`,
          entityType: 'review_task',
          entityId: task.id,
          meta: { documentId: task.documentId, type: task.type, corrections: corrections.length },
        });
        return { taskId: task.id, outcome, corrections: corrections.length };
      });
    },
  };
}
