'use client';

import { useEffect, useMemo, useState } from 'react';
import type { ExtractedField } from '@/lib/types';
import { BoxOverlay } from './BoxOverlay';

interface Props {
  data: ArrayBuffer;
  mime: string;
  fields: ExtractedField[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
  pageRefs: React.RefObject<Map<number, HTMLDivElement>>;
}

export function ImageViewer({ data, mime, fields, selectedPath, onSelect, pageRefs }: Props) {
  const [size, setSize] = useState<{ width: number; height: number } | null>(null);
  const url = useMemo(() => URL.createObjectURL(new Blob([data], { type: mime })), [data, mime]);
  // Free the object URL when the image changes or the viewer unmounts.
  useEffect(() => () => URL.revokeObjectURL(url), [url]);

  return (
    <div
      ref={(el) => {
        if (el) pageRefs.current?.set(1, el);
      }}
      className="relative shadow ring-1 ring-slate-200"
    >
      {/* eslint-disable-next-line @next/next/no-img-element -- a local object URL, not a remote image */}
      <img
        src={url}
        alt="Uploaded invoice"
        className="block w-full"
        onLoad={(e) =>
          setSize({ width: e.currentTarget.clientWidth, height: e.currentTarget.clientHeight })
        }
      />
      {size && (
        <BoxOverlay
          fields={fields.filter((f) => f.page === 1)}
          width={size.width}
          height={size.height}
          selectedPath={selectedPath}
          onSelect={onSelect}
        />
      )}
    </div>
  );
}
