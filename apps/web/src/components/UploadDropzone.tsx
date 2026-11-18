'use client';

import { useRef, useState, type DragEvent } from 'react';
import { useUpload } from '@/hooks/queries';
import type { UploadResult } from '@/lib/types';
import { ErrorState } from './States';

const ACCEPT = 'application/pdf,image/png,image/jpeg';

export function UploadDropzone() {
  const upload = useUpload();
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);

  function send(files: FileList | null) {
    if (!files || files.length === 0) return;
    setResult(null);
    upload.mutate([...files], { onSuccess: setResult });
  }

  function onDrop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    send(event.dataTransfer.files);
  }

  return (
    <div className="space-y-2">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 text-sm transition ${
          dragging ? 'border-blue-400 bg-blue-50' : 'border-slate-300 bg-white'
        }`}
      >
        <p className="text-slate-600">
          Drop GST invoices here (PDF, PNG or JPG, up to 10 MB and 20 pages each)
        </p>
        <button
          type="button"
          className="mt-3 rounded-md bg-slate-900 px-3 py-1.5 font-medium text-white disabled:opacity-50"
          onClick={() => input.current?.click()}
          disabled={upload.isPending}
        >
          {upload.isPending ? 'Uploading…' : 'Choose files'}
        </button>
        <input
          ref={input}
          type="file"
          accept={ACCEPT}
          multiple
          hidden
          onChange={(e) => {
            send(e.target.files);
            e.target.value = '';
          }}
        />
      </div>
      {upload.error && <ErrorState error={upload.error} />}
      {result && (result.documents.length > 0 || result.rejected.length > 0) && (
        <div className="rounded-md bg-white p-3 text-sm ring-1 ring-slate-200">
          {result.documents.length > 0 && (
            <p className="text-emerald-700">
              Uploaded {result.documents.length} file(s); processing has started.
            </p>
          )}
          {result.rejected.map((r) => (
            <p key={r.name} className="text-rose-700">
              {r.name}: {r.message}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
