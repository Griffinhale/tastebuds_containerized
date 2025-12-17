import Link from 'next/link';
import { ApiStatus } from '../components/api-status';
import { CurrentUser } from '../components/current-user';

export default function Home() {
  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 px-6 py-12">
      <header className="space-y-2">
        <p className="text-sm uppercase tracking-wide text-emerald-300">Tastebuds Frontend</p>
        <h1 className="text-3xl font-semibold text-white">
          Next.js is wired up - connect to the FastAPI backend and start building menus.
        </h1>
        <p className="text-base text-slate-200">
          This placeholder checks the API base URL and gives you a jumping-off point for auth, search,
          and menu flows.
        </p>
      </header>

      <ApiStatus />

      <CurrentUser />

      <div className="flex flex-wrap gap-3">
        <Link
          href="/login"
          className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400"
        >
          Log in
        </Link>
        <Link
          href="/register"
          className="rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm font-semibold text-white transition hover:border-emerald-400/60 hover:text-emerald-200"
        >
          Create account
        </Link>
      </div>

      <section className="grid gap-4 sm:grid-cols-2">
        <Card title="Auth flows" description="Login/register UI now hits the FastAPI auth endpoints." href="/login" />
        <Card
          title="Menus & courses"
          description="View your menus and create new ones via the FastAPI backend."
          href="/menus"
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

function Card({
  title,
  description,
  href
}: {
  title: string;
  description: string;
  href: string;
}) {
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
