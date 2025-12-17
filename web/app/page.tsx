import Link from 'next/link';
import { ApiStatus } from '../components/api-status';

export default function Home() {
  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 px-6 py-12">
      <header className="space-y-2">
        <p className="text-sm uppercase tracking-wide text-emerald-300">
          Tastebuds Frontend
        </p>
        <h1 className="text-3xl font-semibold text-white">
          Next.js is wired — connect to the FastAPI backend and start building
          menus.
        </h1>
        <p className="text-base text-slate-200">
          This placeholder checks the API base URL and gives you a jumping-off
          point for auth, search, and menu flows.
        </p>
      </header>

      <ApiStatus />

      <section className="grid gap-4 sm:grid-cols-2">
        <Card
          title="Auth flows"
          description="Add login/register pages with JWT refresh handling."
          href="https://nextjs.org/docs/app/building-your-application/routing"
        />
        <Card
          title="Menus & courses"
          description="Build the editor with optimistic updates over the FastAPI schema."
          href="https://nextjs.org/docs/app/building-your-application/data-fetching/fetching"
        />
        <Card
          title="Search & ingestion"
          description="Hit /api/search with include_external=true and import results inline."
          href="https://nextjs.org/docs/app/building-your-application/data-fetching/server-actions-and-mutations"
        />
        <Card
          title="Public pages"
          description="Server-render /menus/[slug] against /api/public/menus/{slug}."
          href="https://nextjs.org/docs/app/building-your-application/rendering/server-components"
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
      <h2 className="text-lg font-semibold text-white group-hover:text-emerald-200">
        {title}
      </h2>
      <p className="mt-2 text-sm text-slate-200">{description}</p>
    </Link>
  );
}
