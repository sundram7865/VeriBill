'use client';

import dynamic from 'next/dynamic';
import { useEffect, useRef } from 'react';
import { ErrorState, Spinner } from '@/components/States';
import { useDocumentFile } from '@/hooks/queries';
import { useElementWidth } from '@/hooks/useElementWidth';
import type { ExtractedField } from '@/lib/types';
import { ImageViewer } from './ImageViewer';

// pdf.js needs browser APIs, so it is loaded on the client only (the page is a static export).
const PdfViewer = dynamic(() => import('./PdfViewer'), {
  ssr: false,
  loading: () => <Spinner label="Loading viewer…" />,
});

interface Props {
  documentId: string;
  mime: string;
  fields: ExtractedField[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
}

export function DocumentViewer({ documentId, mime, fields, selectedPath, onSelect }: Props) {
  const file = useDocumentFile(documentId);
  const { ref, width } = useElementWidth<HTMLDivElement>();
  const pageRefs = useRef(new Map<number, HTMLDivElement>());

  // Bring the selected field's page into view (the box itself is highlighted in the overlay).
  const selectedPage = fields.find((f) => f.path === selectedPath)?.page ?? null;
  useEffect(() => {
    if (selectedPage)
      pageRefs.current.get(selectedPage)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [selectedPage, selectedPath]);

  return (
    <div ref={ref} className="h-full overflow-y-auto pr-2">
      {file.isLoading && <Spinner label="Loading document…" />}
      {file.error && <ErrorState error={file.error} onRetry={() => void file.refetch()} />}
      {file.data && width > 0 && mime === 'application/pdf' && (
        <PdfViewer
          data={file.data}
          width={width - 8}
          fields={fields}
          selectedPath={selectedPath}
          onSelect={onSelect}
          pageRefs={pageRefs}
        />
      )}
      {file.data && mime !== 'application/pdf' && (
        <ImageViewer
          data={file.data}
          mime={mime}
          fields={fields}
          selectedPath={selectedPath}
          onSelect={onSelect}
          pageRefs={pageRefs}
        />
      )}
    </div>
  );
}
