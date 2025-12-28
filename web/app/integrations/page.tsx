// Integrations hub page.
import Link from 'next/link';

import { IntegrationDashboard } from '../../components/integration-dashboard';

export default function IntegrationsPage() {
  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-10 px-6 py-12">
      <div className="flex flex-wrap items-center gap-4 text-sm">
        <Link href="/" className="text-emerald-300 underline decoration-emerald-300/60">
          ← Back home
        </Link>
        <Link href="/menus" className="text-emerald-300 underline decoration-emerald-300/60">
          Menus dashboard
        </Link>
      </div>
      <IntegrationDashboard />
    </main>
  );
}
