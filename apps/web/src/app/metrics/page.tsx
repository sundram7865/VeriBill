'use client';

import { useState } from 'react';
import { AppShell } from '@/components/AppShell';
import { ErrorState, Spinner } from '@/components/States';
import { useMetrics } from '@/hooks/queries';
import { formatMs, formatPercent, formatUsd } from '@/lib/format';

function Card({ title, value, hint }: { title: string; value: string; hint: string }) {
  return (
    <div className="rounded-lg bg-white p-4 ring-1 ring-slate-200">
      <p className="text-xs uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{hint}</p>
    </div>
  );
}

export default function MetricsPage() {
  const [days, setDays] = useState(30);
  const metrics = useMetrics(days);
  const m = metrics.data;

  return (
    <AppShell>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-semibold">Metrics</h1>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="rounded-md border border-slate-300 px-2 py-1 text-sm"
          >
            {[7, 30, 90].map((d) => (
              <option key={d} value={d}>
                Last {d} days
              </option>
            ))}
          </select>
        </div>
        {metrics.isLoading && <Spinner />}
        {metrics.error && (
          <ErrorState error={metrics.error} onRetry={() => void metrics.refetch()} />
        )}
        {m && (
          <>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Card
                title="Auto-approval rate"
                value={formatPercent(m.autoApprovalRate)}
                hint={`of ${m.extractionRuns} extraction runs`}
              />
              <Card
                title="Audited accuracy"
                value={formatPercent(m.auditedAccuracy)}
                hint={`${m.auditedDocuments} auto-approved docs audited by a human`}
              />
              <Card
                title="Field correction rate"
                value={formatPercent(m.fieldCorrectionRate, 2)}
                hint={`${m.corrections} corrections in closed reviews`}
              />
              <Card
                title="Validator catch rate"
                value={formatPercent(m.validatorCatchRate)}
                hint="corrected fields a validator had flagged"
              />
              <Card
                title="Cost per document"
                value={formatUsd(m.costPerDocumentUsd)}
                hint={`total ${formatUsd(m.totalCostUsd)} (estimate from pricing.json)`}
              />
              <Card
                title="Latency p50"
                value={formatMs(m.latencyMs.p50)}
                hint="end-to-end extraction time"
              />
              <Card
                title="Latency p95"
                value={formatMs(m.latencyMs.p95)}
                hint="slowest 5% of extractions"
              />
              <Card
                title="Open review tasks"
                value={String(
                  (m.openReviewTasks.needs_review ?? 0) + (m.openReviewTasks.audit ?? 0),
                )}
                hint={`${m.openReviewTasks.needs_review ?? 0} uncertain · ${m.openReviewTasks.audit ?? 0} audits`}
              />
            </div>
            <div className="rounded-lg bg-white p-4 ring-1 ring-slate-200">
              <p className="mb-2 text-sm font-medium">Documents by status (all time)</p>
              <div className="flex flex-wrap gap-4 text-sm">
                {Object.entries(m.documentsByStatus).map(([status, count]) => (
                  <span key={status}>
                    <span className="text-slate-500">{status.replace('_', ' ')}:</span> {count}
                  </span>
                ))}
                {Object.keys(m.documentsByStatus).length === 0 && (
                  <span className="text-slate-500">No documents yet.</span>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
