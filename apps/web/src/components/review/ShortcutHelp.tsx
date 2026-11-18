import { SHORTCUTS } from '@/lib/shortcuts';

export function ShortcutHelp({ onClose }: { onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40"
      onClick={onClose}
    >
      <div
        className="w-80 rounded-lg bg-white p-4 shadow-lg"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Keyboard shortcuts"
      >
        <h2 className="mb-2 font-semibold">Keyboard shortcuts</h2>
        <dl className="space-y-1 text-sm">
          {SHORTCUTS.map((s) => (
            <div key={s.keys} className="flex justify-between gap-4">
              <dt className="font-mono text-slate-700">{s.keys}</dt>
              <dd className="text-slate-500">{s.action}</dd>
            </div>
          ))}
        </dl>
        <button className="mt-3 text-sm text-blue-700" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}
