import Link from 'next/link';

import { MenuDashboard } from '../../components/menu-dashboard';

export default function MenusPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-12">
      <Link href="/" className="text-sm text-emerald-300 underline decoration-emerald-300/60">
        ← Back home
      </Link>

      <header className="space-y-2">
        <p className="text-sm uppercase tracking-wide text-emerald-300">Menus & courses</p>
        <h1 className="text-3xl font-semibold text-white">Create and manage your menus.</h1>
        <p className="text-base text-slate-200">
          Menus are ordered collections of courses and course items. Start with the basics here,
          then expand into per-course editors and drag-and-drop workflows as the UI evolves.
        </p>
      </header>

      <MenuDashboard />
    </main>
  );
}
