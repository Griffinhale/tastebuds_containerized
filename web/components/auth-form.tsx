'use client';

// Shared login/register form with simple client-side state handling.

import Link from 'next/link';
import { FormEvent, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { login, register } from '../lib/auth';

type Variant = 'login' | 'register';

const copy: Record<
  Variant,
  {
    title: string;
    actionLabel: string;
    helper: string;
    helperHref: string;
    helperText: string;
  }
> = {
  login: {
    title: 'Log in',
    actionLabel: 'Sign in',
    helper: "Don't have an account?",
    helperHref: '/register',
    helperText: 'Create one',
  },
  register: {
    title: 'Create account',
    actionLabel: 'Register',
    helper: 'Already registered?',
    helperHref: '/login',
    helperText: 'Go to login',
  },
};

export function AuthForm({ variant }: { variant: Variant }) {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentCopy = useMemo(() => copy[variant], [variant]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (variant === 'login') {
        await login(email, password);
      } else {
        // Fall back to email as a display name when none is provided.
        await register(email, password, displayName || email);
      }
      router.push('/');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-6 shadow-lg shadow-emerald-500/5">
      <div className="mb-4">
        <p className="text-sm uppercase tracking-wide text-emerald-300">{currentCopy.title}</p>
        <h1 className="text-2xl font-semibold text-white">Use your Tastebuds account</h1>
      </div>

      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-1">
          <label className="text-sm text-slate-200" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <div className="space-y-1">
          <label className="text-sm text-slate-200" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            autoComplete={variant === 'login' ? 'current-password' : 'new-password'}
            className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        {variant === 'register' && (
          <div className="space-y-1">
            <label className="text-sm text-slate-200" htmlFor="display_name">
              Display name
            </label>
            <input
              id="display_name"
              type="text"
              placeholder="Optional"
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </div>
        )}

        {error && (
          <p className="text-sm text-red-300" role="alert">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-70"
        >
          {loading ? 'Working...' : currentCopy.actionLabel}
        </button>
      </form>

      <p className="mt-4 text-sm text-slate-200">
        {currentCopy.helper}{' '}
        <Link
          className="text-emerald-300 underline decoration-emerald-300/60"
          href={currentCopy.helperHref}
        >
          {currentCopy.helperText}
        </Link>
      </p>
    </div>
  );
}
