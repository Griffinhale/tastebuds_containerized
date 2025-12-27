// Skeleton loader for public menu page.
export default function LoadingPublicMenu() {
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-12">
      <div className="h-4 w-24 animate-pulse rounded bg-slate-800" />
      <section className="space-y-3 rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
        <div className="h-4 w-20 animate-pulse rounded bg-slate-800" />
        <div className="h-8 w-2/3 animate-pulse rounded bg-slate-800" />
        <div className="h-20 w-full animate-pulse rounded bg-slate-900" />
        <div className="grid gap-4 pt-4 sm:grid-cols-3">
          {[1, 2, 3].map((index) => (
            <div key={index} className="space-y-2">
              <div className="h-3 w-12 animate-pulse rounded bg-slate-800" />
              <div className="h-6 w-full animate-pulse rounded bg-slate-800" />
            </div>
          ))}
        </div>
      </section>

      {[1, 2].map((section) => (
        <article
          key={section}
          className="space-y-3 rounded-2xl border border-slate-800 bg-slate-950/40 p-6"
        >
          <div className="space-y-2">
            <div className="h-3 w-24 animate-pulse rounded bg-slate-800" />
            <div className="h-6 w-1/3 animate-pulse rounded bg-slate-800" />
            <div className="h-4 w-full animate-pulse rounded bg-slate-900" />
          </div>
          <div className="space-y-3">
            {[1, 2, 3].map((item) => (
              <div
                key={item}
                className="h-20 animate-pulse rounded-xl border border-slate-800 bg-slate-900/60"
              />
            ))}
          </div>
        </article>
      ))}

      <section className="space-y-4 rounded-2xl border border-emerald-500/30 bg-slate-950/40 p-6">
        <div className="space-y-2">
          <div className="h-3 w-32 animate-pulse rounded bg-emerald-700/40" />
          <div className="h-6 w-2/3 animate-pulse rounded bg-emerald-700/40" />
          <div className="h-4 w-full animate-pulse rounded bg-emerald-700/20" />
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          {[1, 2, 3].map((item) => (
            <div
              key={item}
              className="h-36 animate-pulse rounded-xl border border-white/10 bg-white/5"
            />
          ))}
        </div>
        <div className="flex flex-wrap gap-3">
          <div className="h-10 w-32 animate-pulse rounded bg-white/40" />
          <div className="h-10 w-28 animate-pulse rounded border border-white/30" />
        </div>
      </section>
    </main>
  );
}
