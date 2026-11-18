'use client';

import { useRouter } from 'next/navigation';
import { useMemo, useState } from 'react';
import { EmptyState, ErrorState, Spinner } from '@/components/States';
import {
  useDocument,
  useReviewTasks,
  useSubmitReview,
  type CorrectionDraft,
} from '@/hooks/queries';
import { orderedFields } from '@/lib/fields';
import type { ReviewAction } from '@/lib/shortcuts';
import { DocumentViewer } from './DocumentViewer';
import { FieldPanel } from './FieldPanel';
import { ReviewHeader } from './ReviewHeader';
import { ShortcutHelp } from './ShortcutHelp';
import { useReviewKeyboard } from './useReviewKeyboard';

export function ReviewScreen({ documentId }: { documentId: string }) {
  const router = useRouter();
  const detail = useDocument(documentId);
  const queue = useReviewTasks();
  const submit = useSubmitReview();
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [editRequest, setEditRequest] = useState(0);
  const [showHelp, setShowHelp] = useState(false);

  const fields = useMemo(() => orderedFields(detail.data?.fields ?? []), [detail.data]);
  const task = detail.data?.openTask ?? null;

  const corrections: CorrectionDraft[] = fields
    .filter((f) => drafts[f.path] !== undefined && drafts[f.path] !== (f.value ?? ''))
    .map((f) => ({
      fieldPath: f.path,
      after: drafts[f.path] === '' ? null : (drafts[f.path] as string),
    }));

  function nextDocumentId(): string | null {
    return queue.data?.items.find((t) => t.documentId !== documentId)?.documentId ?? null;
  }

  function finish(action: 'approve' | 'reject') {
    if (!task || submit.isPending) return;
    if (action === 'reject' && !window.confirm('Reject this document?')) return;
    submit.mutate(
      { taskId: task.id, action, corrections: action === 'approve' ? corrections : [] },
      {
        onSuccess: () => {
          setDrafts({});
          const next = nextDocumentId();
          router.push(next ? `/review?id=${next}` : '/queue');
        },
      },
    );
  }

  function move(step: 1 | -1) {
    if (fields.length === 0) return;
    const index = fields.findIndex((f) => f.path === selectedPath);
    const nextIndex = index < 0 ? 0 : Math.min(fields.length - 1, Math.max(0, index + step));
    setSelectedPath(fields[nextIndex]?.path ?? null);
  }

  function onAction(action: ReviewAction) {
    if (action === 'next') move(1);
    else if (action === 'previous') move(-1);
    else if (action === 'edit') setEditRequest((n) => n + 1);
    else if (action === 'approve') finish('approve');
    else if (action === 'reject') finish('reject');
    else if (action === 'help') setShowHelp((v) => !v);
  }
  useReviewKeyboard(onAction, Boolean(detail.data));

  if (detail.isLoading) return <Spinner label="Loading document…" />;
  if (detail.error)
    return <ErrorState error={detail.error} onRetry={() => void detail.refetch()} />;
  if (!detail.data) return null;
  const { document: doc } = detail.data;

  return (
    <div className="flex h-[calc(100vh-5.5rem)] flex-col gap-3">
      <ReviewHeader
        detail={detail.data}
        correctionCount={corrections.length}
        busy={submit.isPending}
        onApprove={() => finish('approve')}
        onReject={() => finish('reject')}
        onHelp={() => setShowHelp(true)}
      />
      {submit.error && <ErrorState error={submit.error} />}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-2">
        <DocumentViewer
          documentId={doc.id}
          mime={doc.mime}
          fields={fields}
          selectedPath={selectedPath}
          onSelect={setSelectedPath}
        />
        <div className="overflow-y-auto pr-1">
          {fields.length === 0 ? (
            <EmptyState
              title={
                doc.status === 'processing' || doc.status === 'uploaded'
                  ? 'Extraction in progress…'
                  : 'No extracted fields'
              }
            >
              {doc.errorMessage ??
                'This view refreshes automatically while the document is processed.'}
            </EmptyState>
          ) : (
            <FieldPanel
              fields={fields}
              drafts={drafts}
              selectedPath={selectedPath}
              editRequest={editRequest}
              readOnly={!task}
              onSelect={setSelectedPath}
              onChange={(path, value) => setDrafts((d) => ({ ...d, [path]: value }))}
            />
          )}
        </div>
      </div>
      {showHelp && <ShortcutHelp onClose={() => setShowHelp(false)} />}
    </div>
  );
}
