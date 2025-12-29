// Account hub for profile details and integrations.
import Link from 'next/link';

import { ApiStatus } from '../../components/api-status';
import { AccountOverview } from '../../components/account-overview';
import { CurrentUser } from '../../components/current-user';
import { IntegrationDashboard } from '../../components/integration-dashboard';

export default function AccountPage() {
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
      <section
        id="profile"
        className="scroll-mt-24 space-y-5 rounded-2xl border border-slate-800 bg-slate-950/60 p-6 shadow-lg shadow-emerald-500/10"
      >
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-wide text-emerald-300">My account</p>
          <h1 className="text-3xl font-semibold text-white">Your account details.</h1>
          <p className="text-sm text-slate-300">
            Review your profile, keep credentials up to date, and manage external services.
          </p>
        </div>
        <AccountOverview />
      </section>

      <section id="integrations" className="scroll-mt-24">
        <IntegrationDashboard />
      </section>
    </main>
  );
}
