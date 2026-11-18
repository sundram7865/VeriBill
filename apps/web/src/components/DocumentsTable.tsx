import Link from 'next/link';
import { formatDateTime, formatMoney, formatPercent } from '@/lib/format';
import type { DocumentSummary } from '@/lib/types';
import { StatusBadge } from './Badges';

export function DocumentsTable({ items }: { items: DocumentSummary[] }) {
  return (
    <div className="overflow-x-auto rounded-lg bg-white ring-1 ring-slate-200">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-500">
          <tr>
            <th className="px-3 py-2">File</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Confidence</th>
            <th className="px-3 py-2">Supplier</th>
            <th className="px-3 py-2">Invoice #</th>
            <th className="px-3 py-2 text-right">Grand total</th>
            <th className="px-3 py-2">Uploaded</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {items.map((doc) => (
            <tr key={doc.id} className="hover:bg-slate-50">
              <td className="px-3 py-2">
                <Link
                  href={`/review?id=${doc.id}`}
                  className="font-medium text-blue-700 hover:underline"
                >
                  {doc.originalName}
                </Link>
                {doc.duplicateOfId && (
                  <span className="ml-2 text-xs text-amber-700">possible duplicate</span>
                )}
                {doc.errorMessage && <p className="text-xs text-rose-700">{doc.errorMessage}</p>}
              </td>
              <td className="px-3 py-2">
                <StatusBadge status={doc.status} />
              </td>
              <td className="px-3 py-2">{formatPercent(doc.documentConfidence, 0)}</td>
              <td className="px-3 py-2">{doc.supplierName ?? '—'}</td>
              <td className="px-3 py-2">{doc.invoiceNumber ?? '—'}</td>
              <td className="px-3 py-2 text-right">{formatMoney(doc.grandTotal)}</td>
              <td className="px-3 py-2 text-slate-500">{formatDateTime(doc.createdAt)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
