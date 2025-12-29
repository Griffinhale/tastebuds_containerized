'use client';

import { useEffect, useMemo, useState } from 'react';

import { ApiError, apiFetch } from '../lib/api';
import type { User } from '../lib/auth';

const EMPTY_VALUE = 'Not set';

export function AccountOverview() {
  const [profile, setProfile] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiFetch<User>('/me', undefined, { isServer: false })
      .then((user) => {
        if (!cancelled) {
          setProfile(user);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setProfile(null);
          setError(err instanceof ApiError ? err.message : 'Unable to load account details.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const username = useMemo(() => {
    if (!profile) return EMPTY_VALUE;
    const displayName = profile.display_name?.trim();
    if (displayName) return displayName;
    const email = profile.email || '';
    return email.split('@')[0] || EMPTY_VALUE;
  }, [profile]);

  const memberSince = useMemo(() => {
    if (!profile?.created_at) return 'Unknown';
    const parsed = new Date(profile.created_at);
    if (Number.isNaN(parsed.getTime())) return profile.created_at;
    return parsed.toLocaleDateString();
  }, [profile?.created_at]);

  const detailRows = [
    { label: 'Username', value: username },
    { label: 'Associated email', value: profile?.email || EMPTY_VALUE },
    { label: 'Member since', value: memberSince },
    { label: 'Bio', value: 'No bio on file yet.' },
  ];

  return (
    <div className="grid gap-4 lg:grid-cols-[1.1fr,0.9fr]">
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <p className="text-xs uppercase tracking-wide text-emerald-200">Account details</p>
        {loading ? (
          <p className="mt-3 text-sm text-slate-300">Loading your profile...</p>
        ) : error ? (
          <p className="mt-3 rounded-lg border border-rose-500/40 bg-rose-500/10 p-3 text-sm">
            {error}
          </p>
        ) : profile ? (
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {detailRows.map((detail) => (
              <div
                key={detail.label}
                className="rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-2"
              >
                <p className="text-[10px] uppercase tracking-wide text-slate-500">{detail.label}</p>
                <p className="text-xs font-semibold text-white">{detail.value}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-300">Sign in to view your account details.</p>
        )}
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <p className="text-xs uppercase tracking-wide text-emerald-200">Account maintenance</p>
        <p className="mt-2 text-xs text-slate-300">
          Manage login credentials and security options for your account.
        </p>
        <div className="mt-4 grid gap-2">
          <button
            type="button"
            disabled
            className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60"
          >
            Change password
          </button>
          <button
            type="button"
            disabled
            className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60"
          >
            Update email
          </button>
          <button
            type="button"
            disabled
            className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60"
          >
            Manage sessions
          </button>
        </div>
        <p className="mt-3 text-[11px] text-slate-400">Self-service updates are coming soon.</p>
      </section>
    </div>
  );
}
