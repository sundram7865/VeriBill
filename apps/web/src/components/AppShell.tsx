'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, type ReactNode } from 'react';
import { useAuth } from '@/lib/auth';
import { Spinner } from './States';

const NAV = [
  { href: '/documents', label: 'Documents' },
  { href: '/queue', label: 'Review queue' },
  { href: '/metrics', label: 'Metrics' },
];

/** Page frame for signed-in screens; sends anonymous visitors to /login. */
export function AppShell({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) router.replace('/login');
  }, [loading, user, router]);

  if (loading || !user) return <Spinner label="Checking your session…" />;

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4">
          <span className="font-semibold">InvoiceIQ</span>
          <nav className="flex gap-4 text-sm">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={
                  pathname?.startsWith(item.href)
                    ? 'font-medium text-slate-900'
                    : 'text-slate-500 hover:text-slate-800'
                }
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm text-slate-600">
            <span>
              {user.email}{' '}
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{user.role}</span>
            </span>
            <button onClick={() => void logout()} className="text-slate-500 hover:text-slate-900">
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className={wide ? 'px-4 py-4' : 'mx-auto max-w-7xl px-4 py-6'}>{children}</main>
    </div>
  );
}
