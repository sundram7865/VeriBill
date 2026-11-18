'use client';

import { useEffect, useRef } from 'react';
import { groupFields } from '@/lib/fields';
import type { ExtractedField } from '@/lib/types';
import { FieldRow } from './FieldRow';

interface Props {
  fields: ExtractedField[];
  drafts: Record<string, string>;
  selectedPath: string | null;
  editRequest: number; // bumps when the user presses e/Enter to edit the selected field
  readOnly: boolean;
  onSelect: (path: string) => void;
  onChange: (path: string, value: string) => void;
}

export function FieldPanel({
  fields,
  drafts,
  selectedPath,
  editRequest,
  readOnly,
  onSelect,
  onChange,
}: Props) {
  const inputs = useRef(new Map<string, HTMLInputElement>());

  useEffect(() => {
    if (selectedPath) inputs.current.get(selectedPath)?.scrollIntoView({ block: 'nearest' });
  }, [selectedPath]);

  useEffect(() => {
    if (editRequest > 0 && selectedPath && !readOnly) inputs.current.get(selectedPath)?.focus();
  }, [editRequest, selectedPath, readOnly]);

  return (
    <div className="space-y-4">
      {groupFields(fields).map((group) => (
        <section key={group.key}>
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            {group.title}
          </h3>
          <div className="space-y-0.5">
            {group.fields.map((field) => {
              const original = field.value ?? '';
              const value = drafts[field.path] ?? original;
              return (
                <FieldRow
                  key={field.path}
                  ref={(el) => {
                    if (el) inputs.current.set(field.path, el);
                  }}
                  field={field}
                  value={value}
                  edited={value !== original}
                  selected={field.path === selectedPath}
                  readOnly={readOnly}
                  onSelect={() => onSelect(field.path)}
                  onChange={(v) => onChange(field.path, v)}
                />
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
