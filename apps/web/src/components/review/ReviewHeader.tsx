import { StatusBadge } from '@/components/Badges';
import { formatMs, formatPercent, formatUsd } from '@/lib/format';
import type { DocumentDetail } from '@/lib/types';

interface Props {
  detail: DocumentDetail;
  correctionCount: number;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
  onHelp: () => void;
}

export function ReviewHeader({
  detail,
  correctionCount,
  busy,
  onApprove,
  onReject,
  onHelp,
}: Props) {
  const { document: doc, run, openTask } = detail;
  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-slate-200 pb-3">
      <div className="min-w-0">
        <h1 className="truncate font-semibold">{doc.originalName}</h1>
        <p className="text-xs text-slate-500">
          {run
            ? `${run.decision.replace('_', ' ')} · ${run.decisionReason ?? ''} · confidence ${formatPercent(run.documentConfidence, 0)} · ${run.repairAttempts} repair(s) · ${formatMs(run.latencyMs)} · ${formatUsd(run.costUsd)}${run.usedOcr ? ' · OCR' : ''}`
            : 'Not extracted yet'}
        </p>
      </div>
      <StatusBadge status={doc.status} />
      {doc.duplicateOfId && (
        <a href={`/review?id=${doc.duplicateOfId}`} className="text-xs text-amber-700 underline">
          possible duplicate of an earlier document
        </a>
      )}
      <div className="ml-auto flex items-center gap-2 text-sm">
        <button
          onClick={onHelp}
          className="text-slate-500 hover:text-slate-800"
          title="Keyboard shortcuts (?)"
        >
          ⌨ shortcuts
        </button>
        {openTask ? (
          <>
            <span className="text-xs text-slate-500">
              {openTask.type === 'audit' ? 'Audit sample' : 'Needs review'} · {correctionCount}{' '}
              correction(s)
            </span>
            <button
              onClick={onReject}
              disabled={busy}
              className="rounded-md px-3 py-1.5 text-rose-700 ring-1 ring-rose-300 hover:bg-rose-50 disabled:opacity-50"
            >
              Reject (Shift+R)
            </button>
            <button
              onClick={onApprove}
              disabled={busy}
              className="rounded-md bg-emerald-600 px-3 py-1.5 font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              Approve (Ctrl+Enter)
            </button>
          </>
        ) : (
          <span className="text-xs text-slate-500">No open review task: read-only</span>
        )}
      </div>
    </div>
  );
}
