// Authenticated menus dashboard page.
import Link from 'next/link';

import { ApiStatus } from '../../components/api-status';
import { CurrentUser } from '../../components/current-user';
import { MenuDashboard } from '../../components/menu-dashboard';

export default function MenusPage() {
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

      <section className="space-y-2">
        <p className="text-xs uppercase tracking-wide text-emerald-300">Menus & courses</p>
        <h1 className="text-3xl font-semibold text-white">Shape menus around your courses.</h1>
        <p className="text-sm text-slate-300">
          Browse menus in a sidebar or expand them in place to focus on course flow and curation.
        </p>
      </section>

      <MenuDashboard />
    </main>
  );
}
