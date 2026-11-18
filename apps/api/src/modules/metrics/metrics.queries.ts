import { assertTenant, type Db } from '../../lib/db';

/** Raw SQL for aggregates Prisma cannot express (percentiles, FILTER). Always tenant-filtered. */
export function metricsQueries(db: Db) {
  return {
    async statusCounts(tenantId: string) {
      assertTenant(tenantId);
      return db.$queryRaw<Array<{ status: string; count: bigint }>>`
        SELECT status::text AS status, count(*) AS count
        FROM documents WHERE tenant_id = ${tenantId}::uuid GROUP BY status`;
    },

    async runStats(tenantId: string, since: Date) {
      assertTenant(tenantId);
      const rows = await db.$queryRaw<
        Array<{
          runs: bigint;
          auto: bigint;
          total_cost: number | null;
          p50: number | null;
          p95: number | null;
        }>
      >`
        SELECT count(*) AS runs,
               count(*) FILTER (WHERE decision = 'auto_approve') AS auto,
               sum(cost_usd) AS total_cost,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms) AS p50,
               percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95
        FROM extraction_runs
        WHERE tenant_id = ${tenantId}::uuid AND created_at >= ${since}`;
      return rows[0];
    },

    /** Closed audit tasks and how many of them needed no correction at all. */
    async auditStats(tenantId: string, since: Date) {
      assertTenant(tenantId);
      const rows = await db.$queryRaw<Array<{ audited: bigint; clean: bigint }>>`
        SELECT count(*) AS audited,
               count(*) FILTER (WHERE t.outcome = 'approved' AND t.corrections = 0) AS clean
        FROM (
          SELECT rt.id, rt.outcome, count(c.id) AS corrections
          FROM review_tasks rt
          LEFT JOIN corrections c ON c.review_task_id = rt.id
          WHERE rt.tenant_id = ${tenantId}::uuid AND rt.type = 'audit'
            AND rt.status = 'closed' AND rt.closed_at >= ${since}
          GROUP BY rt.id, rt.outcome
        ) t`;
      return rows[0];
    },

    /** Fields shown to reviewers in closed tasks, and how many of them were corrected. */
    async correctionStats(tenantId: string, since: Date) {
      assertTenant(tenantId);
      const rows = await db.$queryRaw<
        Array<{ reviewed_fields: bigint; corrections: bigint; flagged: bigint }>
      >`
        WITH closed AS (
          SELECT rt.id, rt.document_id FROM review_tasks rt
          WHERE rt.tenant_id = ${tenantId}::uuid AND rt.status = 'closed' AND rt.closed_at >= ${since}
        ),
        latest_runs AS (
          SELECT DISTINCT ON (r.document_id) r.id, r.document_id
          FROM extraction_runs r JOIN closed ON closed.document_id = r.document_id
          ORDER BY r.document_id, r.attempt DESC
        )
        SELECT
          (SELECT count(*) FROM extracted_fields f JOIN latest_runs lr ON lr.id = f.run_id
            WHERE f.value IS NOT NULL OR EXISTS (
              SELECT 1 FROM corrections c WHERE c.document_id = f.document_id AND c.field_path = f.path))
            AS reviewed_fields,
          (SELECT count(*) FROM corrections c JOIN closed ON closed.id = c.review_task_id) AS corrections,
          (SELECT count(*) FROM corrections c JOIN closed ON closed.id = c.review_task_id
            WHERE c.had_validator_issue) AS flagged`;
      return rows[0];
    },

    async openQueue(tenantId: string) {
      assertTenant(tenantId);
      return db.$queryRaw<Array<{ type: string; count: bigint }>>`
        SELECT type::text AS type, count(*) AS count FROM review_tasks
        WHERE tenant_id = ${tenantId}::uuid AND status = 'open' GROUP BY type`;
    },
  };
}
