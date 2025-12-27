// Login page wrapper around the shared auth form.
import Link from 'next/link';

import { AuthForm } from '../../components/auth-form';

export default function LoginPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col gap-6 px-6 py-12">
      <Link href="/" className="text-sm text-emerald-300 underline decoration-emerald-300/60">
        ← Back home
      </Link>
      <AuthForm variant="login" />
    </main>
  );
}
