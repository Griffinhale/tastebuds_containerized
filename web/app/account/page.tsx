// Account hub for integrations, taste profile, and workspace links.
import Link from 'next/link';

import { IntegrationDashboard } from '../../components/integration-dashboard';
import { TasteProfileDashboard } from '../../components/taste-profile-dashboard';

export default function AccountPage() {
  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-10 px-6 py-12">
      <div className="flex flex-wrap items-center gap-4 text-sm">
        <Link href="/" className="text-emerald-300 underline decoration-emerald-300/60">
          {'<- Back home'}
        </Link>
        <Link href="/library" className="text-emerald-300 underline decoration-emerald-300/60">
          Library
        </Link>
        <Link href="/menus" className="text-emerald-300 underline decoration-emerald-300/60">
          Menus
        </Link>
        <Link href="/search" className="text-emerald-300 underline decoration-emerald-300/60">
          Search
        </Link>
      </div>

      <header className="space-y-5 rounded-2xl border border-slate-800 bg-slate-950/60 p-6 shadow-lg shadow-emerald-500/10">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-wide text-emerald-300">My account</p>
          <h1 className="text-3xl font-semibold text-white">Your Tastebuds workspace.</h1>
          <p className="text-sm text-slate-300">
            Manage what you track, connect services, and monitor background syncs.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <AccountCard
            title="Library"
            description="Review logs, queue items, and status."
            href="/library"
          />
          <AccountCard
            title="Menus"
            description="Manage menus and export flows."
            href="/menus"
          />
          <AccountCard title="Search" description="Find new media." href="/search" />
        </div>
      </header>

      <section className="space-y-3">
        <p className="text-xs uppercase tracking-wide text-emerald-300">Workspace</p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <AccountCard
            title="Taste profile"
            description="View your latest signals."
            href="/account#taste-profile"
          />
          <AccountCard
            title="Integrations"
            description="Manage connected services."
            href="/account#integrations"
          />
          <AccountCard
            title="Queue"
            description="Monitor background syncs."
            href="/account#integrations"
          />
        </div>
      </section>

      <section id="taste-profile" className="scroll-mt-24">
        <TasteProfileDashboard />
      </section>

      <section id="integrations" className="scroll-mt-24">
        <IntegrationDashboard />
      </section>
    </main>
  );
}

function AccountCard({
  title,
  description,
  href,
}: {
  title: string;
  description: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 transition hover:border-emerald-400/60"
    >
      <p className="text-sm font-semibold text-white">{title}</p>
      <p className="mt-1 text-xs text-slate-300">{description}</p>
    </Link>
  );
}
