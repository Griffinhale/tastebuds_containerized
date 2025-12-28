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
      <header className="space-y-3 rounded-2xl border border-slate-800 bg-slate-950/60 p-6 shadow-lg shadow-emerald-500/10">
        <p className="text-sm uppercase tracking-wide text-emerald-300">Tastebuds</p>
        <h1 className="text-3xl font-semibold text-white">
          Welcome back—your library is the home base.
        </h1>
        <p className="text-base leading-relaxed text-slate-200">
          Jump into your Library + Log hub to keep momentum, then move into search and menu edits
          without losing context.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/library"
            className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400"
          >
            Open library
          </Link>
          <Link
            href="/menus"
            className="rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm font-semibold text-white transition hover:border-emerald-400/60 hover:text-emerald-200"
          >
            Open menus
          </Link>
          <Link
            href="/integrations"
            className="rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm font-semibold text-white transition hover:border-emerald-400/60 hover:text-emerald-200"
          >
            Connect integrations
          </Link>
        </div>
      </header>

      <section className="grid gap-6 lg:grid-cols-[1.3fr,0.7fr]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-emerald-500/20 bg-slate-950/70 p-4">
            <p className="text-xs uppercase tracking-wide text-emerald-200">Returning home</p>
            <h2 className="mt-2 text-xl font-semibold text-white">Library + Log hub</h2>
            <p className="text-sm text-slate-200">
              Capture your latest progress, queue what’s next, and keep your media diet moving.
            </p>
          </div>
          <LibraryDashboard />
        </div>
        <div className="space-y-4">
          <CurrentUser />
          <ApiStatus />
          <QueueStatus />
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 text-sm text-slate-200">
            <p className="text-sm font-semibold text-emerald-300">Quick jumps</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link
                href="/menus"
                className="rounded-full border border-slate-800 px-3 py-1 text-xs font-semibold text-white transition hover:border-emerald-400/60"
              >
                Menus dashboard
              </Link>
              <Link
                href="/integrations"
                className="rounded-full border border-slate-800 px-3 py-1 text-xs font-semibold text-white transition hover:border-emerald-400/60"
              >
                Integrations
              </Link>
              <Link
                href="/taste-profile"
                className="rounded-full border border-slate-800 px-3 py-1 text-xs font-semibold text-white transition hover:border-emerald-400/60"
              >
                Taste profile
              </Link>
              <Link
                href="/login"
                className="rounded-full border border-slate-800 px-3 py-1 text-xs font-semibold text-white transition hover:border-emerald-400/60"
              >
                Log in
              </Link>
              <Link
                href="/register"
                className="rounded-full border border-slate-800 px-3 py-1 text-xs font-semibold text-white transition hover:border-emerald-400/60"
              >
                Create account
              </Link>
            </div>
          </div>
        </div>
      </section>

      <MediaSearchExplorer />

      <section className="grid gap-4 sm:grid-cols-2">
        <Card
          title="Auth flows"
          description="Login/register UI now hits the FastAPI auth endpoints."
          href="/login"
        />
        <Card
          title="Menus & courses"
          description="View your menus and create new ones via the FastAPI backend."
          href="/menus"
        />
        <Card
          title="Library & log"
          description="Track status, goals, and progress across your media diet."
          href="/library"
        />
        <Card
          title="Taste profile"
          description="See your media balance, tags, and log-derived signals."
          href="/taste-profile"
        />
        <Card
          title="Integrations"
          description="Link Spotify, Arr, Jellyfin, and Plex with tokens and webhooks."
          href="/integrations"
        />
        <Card
          title="Search & ingestion"
          description="Hit /api/search with include_external=true and import results inline."
          href="https://nextjs.org/docs/app/building-your-application/data-fetching/server-actions-and-mutations"
        />
        <Card
          title="Public pages"
          description="Mark a menu public and share it at /menus/[slug]."
          href="/menus"
        />
      </section>
    </main>
  );
}

function Card({ title, description, href }: { title: string; description: string; href: string }) {
  // Reusable card link styling for homepage sections.
  return (
    <Link
      href={href}
      className="group rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-400/60 hover:shadow-lg hover:shadow-emerald-500/10"
    >
      <h2 className="text-lg font-semibold text-white group-hover:text-emerald-200">{title}</h2>
      <p className="mt-2 text-sm text-slate-200">{description}</p>
    </Link>
  );
}
