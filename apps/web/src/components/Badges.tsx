import { confidenceLevel, formatPercent } from '@/lib/format';
import type { DocumentStatus } from '@/lib/types';

const STATUS_STYLES: Record<DocumentStatus, string> = {
  uploaded: 'bg-slate-100 text-slate-700',
  processing: 'bg-blue-100 text-blue-800',
  auto_approved: 'bg-emerald-100 text-emerald-800',
  needs_review: 'bg-amber-100 text-amber-800',
  approved: 'bg-emerald-100 text-emerald-800',
  rejected: 'bg-rose-100 text-rose-800',
  failed: 'bg-red-100 text-red-800',
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      {status.replace('_', ' ')}
    </span>
  );
}

const CONFIDENCE_STYLES = {
  high: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  medium: 'bg-amber-50 text-amber-700 ring-amber-200',
  low: 'bg-rose-50 text-rose-700 ring-rose-200',
};

export function ConfidenceBadge({ value }: { value: number }) {
  const level = confidenceLevel(value);
  return (
    <span
      className={`inline-flex rounded px-1.5 py-0.5 text-[11px] font-medium ring-1 ${CONFIDENCE_STYLES[level]}`}
      title={`Confidence ${formatPercent(value)} (from grounding, validators, OCR and repair agreement)`}
    >
      {formatPercent(value, 0)}
    </span>
  );
}
