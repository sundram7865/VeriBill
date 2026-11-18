'use client';

import Link from 'next/link';
import { AppShell } from '@/components/AppShell';
import { StatusBadge } from '@/components/Badges';
import { EmptyState, ErrorState, Spinner } from '@/components/States';
import { useReviewTasks } from '@/hooks/queries';
import { formatDateTime, formatPercent } from '@/lib/format';

export default function QueuePage() {
  const tasks = useReviewTasks();
  const items = tasks.data?.items ?? [];

  return (
    <AppShell>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-semibold">Review queue</h1>
          {items[0] && (
            <Link
              href={`/review?id=${items[0].documentId}`}
              className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white"
            >
              Start reviewing →
            </Link>
          )}
        </div>
        {tasks.isLoading && <Spinner />}
        {tasks.error && <ErrorState error={tasks.error} onRetry={() => void tasks.refetch()} />}
        {tasks.data && items.length === 0 && (
          <EmptyState title="Nothing to review">
            Uncertain documents and audit samples will appear here.
          </EmptyState>
        )}
        {items.length > 0 && (
          <ul className="divide-y divide-slate-100 rounded-lg bg-white ring-1 ring-slate-200">
            {items.map((task) => (
              <li key={task.id} className="flex items-center gap-4 px-4 py-3 text-sm">
                <span
                  className={`rounded px-2 py-0.5 text-xs font-medium ${
                    task.type === 'audit'
                      ? 'bg-violet-100 text-violet-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}
                >
                  {task.type === 'audit' ? 'audit sample' : 'needs review'}
                </span>
                <Link
                  href={`/review?id=${task.documentId}`}
                  className="font-medium text-blue-700 hover:underline"
                >
                  {task.document.originalName}
                </Link>
                <StatusBadge status={task.document.status} />
                <span className="text-slate-500">
                  confidence {formatPercent(task.document.documentConfidence, 0)}
                </span>
                <span className="ml-auto text-slate-400">{formatDateTime(task.openedAt)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </AppShell>
  );
}
