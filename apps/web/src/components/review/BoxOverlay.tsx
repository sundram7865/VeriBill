import { toPixels } from '@/lib/bbox';
import { fieldLabel } from '@/lib/fields';
import type { ExtractedField } from '@/lib/types';

interface Props {
  fields: ExtractedField[]; // fields located on this page
  width: number;
  height: number;
  selectedPath: string | null;
  onSelect: (path: string) => void;
}

function boxColor(field: ExtractedField, selected: boolean): string {
  if (selected) return 'border-blue-600 bg-blue-500/20 ring-2 ring-blue-500';
  if (field.issues.some((i) => i.severity === 'error')) return 'border-rose-500/70 bg-rose-400/10';
  return 'border-emerald-500/50 bg-emerald-400/5';
}

/** Highlights where each extracted value was found on the page. */
export function BoxOverlay({ fields, width, height, selectedPath, onSelect }: Props) {
  return (
    <div className="pointer-events-none absolute inset-0">
      {fields.map((field) => {
        if (!field.bbox) return null;
        const box = toPixels(field.bbox, width, height);
        const selected = field.path === selectedPath;
        return (
          <button
            key={field.path}
            type="button"
            title={`${fieldLabel(field.path)}: ${field.value ?? ''}`}
            onClick={() => onSelect(field.path)}
            className={`pointer-events-auto absolute rounded-sm border ${boxColor(field, selected)}`}
            style={{ left: box.left, top: box.top, width: box.width, height: box.height }}
          />
        );
      })}
    </div>
  );
}
