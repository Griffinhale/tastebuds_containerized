// Home dashboard combining health widgets and discovery cards.
import Link from 'next/link';

import { ApiStatus } from '../components/api-status';
import { CurrentUser } from '../components/current-user';
import { QueueStatus } from '../components/queue-status';
import { MediaSearchExplorer } from '../components/media-search-explorer';
import { LibraryDashboard } from '../components/library-dashboard';

export default function Home() {
  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-10 px-6 py-12">
      <header className="space-y-5 rounded-2xl border border-slate-800 bg-slate-950/60 p-6 shadow-lg shadow-emerald-500/10">
        <div className="space-y-3">
          <p className="text-sm uppercase tracking-wide text-emerald-300">Tastebuds home</p>
          <h1 className="text-3xl font-semibold text-white">
            Library first. Search next. Menus when you are ready.
          </h1>
          <p className="text-base leading-relaxed text-slate-200">
            Keep your library moving, pull in new finds, then shape shareable menus when inspiration
            hits.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <ActionCard
            title="Library + log"
            description="Capture progress, queue next-up items, and log a quick update."
            href="/library"
            tone="primary"
          />
          <ActionCard
            title="Search workspace"
            description="Run a focused search across your catalog and external sources."
            href="#search"
          />
          <ActionCard
            title="Menus dashboard"
            description="Build menus, create courses, and share the final flow."
            href="/menus"
          />
        </div>
        <nav className="flex flex-wrap gap-2 text-xs" aria-label="Secondary">
          <SecondaryLink href="/integrations">Integrations</SecondaryLink>
          <SecondaryLink href="/taste-profile">Taste profile</SecondaryLink>
          <SecondaryLink href="/login">Log in</SecondaryLink>
          <SecondaryLink href="/register">Create account</SecondaryLink>
        </nav>
      </header>

      <section className="grid gap-6 lg:grid-cols-[1.3fr,0.7fr]">
        <div className="space-y-6">
          <LibraryDashboard />
        </div>
        <div className="space-y-4">
          <CurrentUser />
          <QueueStatus />
          <ApiStatus />
        </div>
      </section>

      <div id="search" className="scroll-mt-24">
        <MediaSearchExplorer />
      </div>
    </main>
  );
}

function ActionCard({
  title,
  description,
  href,
  tone = 'default',
}: {
  title: string;
  description: string;
  href: string;
  tone?: 'default' | 'primary';
}) {
  const toneClass =
    tone === 'primary'
      ? 'border-emerald-400/50 bg-emerald-500/10 shadow-emerald-500/20'
      : 'border-slate-800 bg-slate-900/60 shadow-transparent';
  const titleClass = tone === 'primary' ? 'text-emerald-100' : 'text-white';
  return (
    <Link
      href={href}
      className={`group rounded-xl border p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-400/60 hover:shadow-lg hover:shadow-emerald-500/10 ${toneClass}`}
    >
      <h2 className={`text-lg font-semibold ${titleClass} group-hover:text-emerald-200`}>
        {title}
      </h2>
      <p className="mt-2 text-sm text-slate-200">{description}</p>
    </Link>
  );
}

function SecondaryLink({ href, children }: { href: string; children: string }) {
  return (
    <Link
      href={href}
      className="rounded-full border border-slate-800 bg-slate-900/60 px-3 py-1 text-xs font-semibold text-white transition hover:border-emerald-400/60 hover:text-emerald-200"
    >
      {children}
    </Link>
  );
}
