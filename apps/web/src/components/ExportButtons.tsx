'use client';

import { useState } from 'react';
import { downloadFile } from '@/lib/download';

/** Admin-only (the API enforces it too): approved invoices as CSV or JSON. */
export function ExportButtons() {
  const [error, setError] = useState<string | null>(null);

  async function run(format: 'csv' | 'json') {
    setError(null);
    try {
      await downloadFile(`/export/invoices.${format}`, `invoices.${format}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    }
  }

  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-slate-500">Export approved:</span>
      <button
        className="rounded-md px-2 py-1 ring-1 ring-slate-300 hover:bg-slate-100"
        onClick={() => void run('csv')}
      >
        CSV
      </button>
      <button
        className="rounded-md px-2 py-1 ring-1 ring-slate-300 hover:bg-slate-100"
        onClick={() => void run('json')}
      >
        JSON
      </button>
      {error && <span className="text-rose-700">{error}</span>}
    </div>
  );
}
