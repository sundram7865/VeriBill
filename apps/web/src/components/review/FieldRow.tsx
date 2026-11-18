'use client';

import { forwardRef } from 'react';
import { ConfidenceBadge } from '@/components/Badges';
import { fieldLabel } from '@/lib/fields';
import type { ExtractedField } from '@/lib/types';

interface Props {
  field: ExtractedField;
  value: string;
  edited: boolean;
  selected: boolean;
  readOnly: boolean;
  onChange: (value: string) => void;
  onSelect: () => void;
}

export const FieldRow = forwardRef<HTMLInputElement, Props>(function FieldRow(
  { field, value, edited, selected, readOnly, onChange, onSelect },
  inputRef,
) {
  const hasError = field.issues.some((i) => i.severity === 'error');
  return (
    <div
      onClick={onSelect}
      className={`rounded-md px-2 py-1.5 ${selected ? 'bg-blue-50 ring-1 ring-blue-300' : hasError ? 'bg-rose-50/60' : ''}`}
    >
      <div className="flex items-center gap-2">
        <label className="w-40 shrink-0 text-xs text-slate-600" htmlFor={field.id}>
          {fieldLabel(field.path)}
        </label>
        <input
          id={field.id}
          ref={inputRef}
          value={value}
          readOnly={readOnly}
          onFocus={onSelect}
          onChange={(e) => onChange(e.target.value)}
          className={`min-w-0 flex-1 rounded border px-2 py-1 text-sm ${edited ? 'border-blue-400 bg-blue-50' : 'border-slate-200'} ${readOnly ? 'bg-slate-50' : ''}`}
        />
        <ConfidenceBadge value={field.confidence} />
      </div>
      {field.issues.length > 0 && (
        <ul className="mt-1 space-y-0.5 pl-40 text-xs">
          {field.issues.map((issue) => (
            <li
              key={issue.code}
              className={issue.severity === 'error' ? 'text-rose-700' : 'text-amber-700'}
            >
              {issue.severity === 'error' ? '✖' : '⚠'} {issue.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
});
