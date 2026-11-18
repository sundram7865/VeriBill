'use client';

import { useState } from 'react';
import { AppShell } from '@/components/AppShell';
import { DocumentsTable } from '@/components/DocumentsTable';
import { ExportButtons } from '@/components/ExportButtons';
import { EmptyState, ErrorState, Spinner } from '@/components/States';
import { UploadDropzone } from '@/components/UploadDropzone';
import { useDocuments } from '@/hooks/queries';
import { useAuth } from '@/lib/auth';
import type { DocumentStatus } from '@/lib/types';

const FILTERS: Array<DocumentStatus | 'all'> = [
  'all',
  'processing',
  'needs_review',
  'auto_approved',
  'approved',
  'rejected',
  'failed',
];

export default function DocumentsPage() {
  const { user } = useAuth();
  const [status, setStatus] = useState<DocumentStatus | 'all'>('all');
  const [page, setPage] = useState(1);
  const documents = useDocuments(status, page);
  const pageCount = documents.data
    ? Math.max(1, Math.ceil(documents.data.total / documents.data.pageSize))
    : 1;

  return (
    <AppShell>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-lg font-semibold">Documents</h1>
          {user?.role === 'admin' && <ExportButtons />}
        </div>
        <UploadDropzone />
        <div className="flex flex-wrap gap-1 text-sm">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => {
                setStatus(f);
                setPage(1);
              }}
              className={`rounded-full px-3 py-1 ${status === f ? 'bg-slate-900 text-white' : 'bg-white ring-1 ring-slate-200'}`}
            >
              {f.replace('_', ' ')}
            </button>
          ))}
        </div>
        {documents.isLoading && <Spinner />}
        {documents.error && (
          <ErrorState error={documents.error} onRetry={() => void documents.refetch()} />
        )}
        {documents.data && documents.data.items.length === 0 && (
          <EmptyState title="No documents here yet">
            Upload an invoice above to get started.
          </EmptyState>
        )}
        {documents.data && documents.data.items.length > 0 && (
          <>
            <DocumentsTable items={documents.data.items} />
            <div className="flex items-center justify-end gap-3 text-sm">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="disabled:opacity-40"
              >
                ← Previous
              </button>
              <span className="text-slate-500">
                Page {page} of {pageCount} · {documents.data.total} documents
              </span>
              <button
                disabled={page >= pageCount}
                onClick={() => setPage(page + 1)}
                className="disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
