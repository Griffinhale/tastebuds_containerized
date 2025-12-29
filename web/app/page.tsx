// Home dashboard with customizable shortcuts and status widgets.
import Link from 'next/link';

import { ApiStatus } from '../components/api-status';
import { CurrentUser } from '../components/current-user';
import { HomeDashboard } from '../components/home-dashboard';

export default function Home() {
  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-10 px-6 py-10">
      <header className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-950/40 px-4 py-2">
        <Link
          href="/"
          className="text-lg font-semibold text-emerald-200 transition hover:text-emerald-100"
        >
          Tastebuds.
        </Link>
        <div className="flex flex-wrap items-center gap-3 text-xs lg:flex-nowrap">
          <CurrentUser variant="compact" />
          <ApiStatus variant="compact" />
        </div>
      </header>

      <HomeDashboard />
    </main>
  );
}
