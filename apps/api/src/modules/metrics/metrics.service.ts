import type { AppDeps } from '../../app.deps';
import type { AuthContext } from '../auth/auth.types';
import { metricsQueries } from './metrics.queries';

function ratio(numerator: number, denominator: number): number | null {
  return denominator > 0 ? numerator / denominator : null;
}

const n = (value: bigint | number | null | undefined): number => Number(value ?? 0);

/**
 * Product metrics, computed from real activity in the database:
 *  - auto-approval rate: share of extraction runs the pipeline routed to auto_approve
 *  - audited accuracy: share of closed audit tasks approved with zero corrections
 *  - field correction rate: corrected fields / fields shown in closed review tasks
 *  - validator catch rate: share of human corrections on fields a validator had flagged
 *  - cost per document and p50/p95 latency from extraction_runs
 */
export function metricsService(deps: AppDeps) {
  const queries = metricsQueries(deps.db);
  return {
    async summary(ctx: AuthContext, days: number) {
      const since = new Date(Date.now() - days * 86_400_000);
      const [statuses, runs, audits, corrections, queue] = await Promise.all([
        queries.statusCounts(ctx.tenantId),
        queries.runStats(ctx.tenantId, since),
        queries.auditStats(ctx.tenantId, since),
        queries.correctionStats(ctx.tenantId, since),
        queries.openQueue(ctx.tenantId),
      ]);
      const runCount = n(runs?.runs);
      return {
        windowDays: days,
        documentsByStatus: Object.fromEntries(statuses.map((s) => [s.status, n(s.count)])),
        openReviewTasks: Object.fromEntries(queue.map((q) => [q.type, n(q.count)])),
        extractionRuns: runCount,
        autoApprovalRate: ratio(n(runs?.auto), runCount),
        auditedAccuracy: ratio(n(audits?.clean), n(audits?.audited)),
        auditedDocuments: n(audits?.audited),
        fieldCorrectionRate: ratio(n(corrections?.corrections), n(corrections?.reviewed_fields)),
        corrections: n(corrections?.corrections),
        validatorCatchRate: ratio(n(corrections?.flagged), n(corrections?.corrections)),
        costPerDocumentUsd: runCount > 0 ? n(runs?.total_cost) / runCount : null,
        totalCostUsd: n(runs?.total_cost),
        latencyMs: { p50: runs?.p50 ?? null, p95: runs?.p95 ?? null },
      };
    },
  };
}
