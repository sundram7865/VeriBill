'use client';

import { useMemo, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import type { ExtractedField } from '@/lib/types';
import { BoxOverlay } from './BoxOverlay';

// Served from our own origin (copied into public/ at install time), so no CDN is involved.
pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';

interface Props {
  data: ArrayBuffer;
  width: number;
  fields: ExtractedField[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
  pageRefs: React.RefObject<Map<number, HTMLDivElement>>;
}

export default function PdfViewer({
  data,
  width,
  fields,
  selectedPath,
  onSelect,
  pageRefs,
}: Props) {
  const [pageCount, setPageCount] = useState(0);
  const [sizes, setSizes] = useState<Record<number, { width: number; height: number }>>({});
  // pdf.js transfers the buffer to its worker, so give it a copy and keep it stable.
  const file = useMemo(() => ({ data: new Uint8Array(data.slice(0)) }), [data]);

  return (
    <Document
      file={file}
      onLoadSuccess={({ numPages }) => setPageCount(numPages)}
      loading="Rendering document…"
    >
      {Array.from({ length: pageCount }, (_, i) => i + 1).map((pageNumber) => (
        <div
          key={pageNumber}
          ref={(el) => {
            if (el) pageRefs.current?.set(pageNumber, el);
          }}
          className="relative mb-4 shadow ring-1 ring-slate-200"
        >
          <Page
            pageNumber={pageNumber}
            width={width}
            renderTextLayer={false}
            renderAnnotationLayer={false}
            onRenderSuccess={(page) =>
              setSizes((s) => ({ ...s, [pageNumber]: { width: page.width, height: page.height } }))
            }
          />
          {sizes[pageNumber] && (
            <BoxOverlay
              fields={fields.filter((f) => f.page === pageNumber)}
              width={sizes[pageNumber].width}
              height={sizes[pageNumber].height}
              selectedPath={selectedPath}
              onSelect={onSelect}
            />
          )}
        </div>
      ))}
    </Document>
  );
}
