'use client';

// Fork action for public menus.

import Link from 'next/link';
import { useState } from 'react';

import { forkMenu, Menu } from '../lib/menus';

export function ForkMenuActions({ menuId, menuTitle }: { menuId: string; menuTitle: string }) {
  const [forked, setForked] = useState<Menu | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFork() {
    if (working) return;
    setWorking(true);
    setError(null);
    try {
      const created = await forkMenu(menuId, { title: `${menuTitle} (Fork)` });
      setForked(created);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fork menu.';
      const normalized = message.toLowerCase();
      if (normalized.includes('unauthorized') || normalized.includes('token')) {
        setError('Log in to fork this menu.');
      } else {
        setError(message);
      }
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="rounded-xl border border-emerald-500/30 bg-slate-950/60 p-4 text-sm text-slate-200">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-emerald-200">Fork this menu</p>
          <p className="text-xs text-slate-300">
            Copy the menu into your dashboard and remix the courses.
          </p>
        </div>
        <button
          onClick={handleFork}
          className="rounded-md bg-emerald-500 px-3 py-2 text-xs font-semibold text-slate-950 transition hover:bg-emerald-400"
          disabled={working}
        >
          {working ? 'Forking...' : 'Create fork'}
        </button>
      </div>
      {forked && (
        <p className="mt-3 text-xs text-emerald-100">
          Fork created.{' '}
          <Link href="/menus" className="underline decoration-emerald-300/60">
            Open your menus
          </Link>
          .
        </p>
      )}
      {error && <p className="mt-2 text-xs text-red-300">{error}</p>}
    </div>
  );
}
