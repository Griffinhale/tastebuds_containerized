// Library and log hub page.
import Link from 'next/link';

import { LibraryDashboard } from '../../components/library-dashboard';

export default function LibraryPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-6 py-12">
      <div className="flex flex-wrap items-center gap-4 text-sm">
        <Link href="/" className="text-emerald-300 underline decoration-emerald-300/60">
          ← Back home
        </Link>
        <Link href="/menus" className="text-emerald-300 underline decoration-emerald-300/60">
          Menus dashboard
        </Link>
      </div>

      <header className="space-y-2">
        <p className="text-sm uppercase tracking-wide text-emerald-300">Library + Log</p>
        <h1 className="text-3xl font-semibold text-white">Track your media diet.</h1>
        <p className="text-base text-slate-200">
          Log progress, capture goals, and keep status tracking in one place. The next-up queue
          surfaces quick actions so you can start, log progress, or finish items without leaving the
          hub.
        </p>
      </header>

      <LibraryDashboard />
    </main>
  );
}
