'use client';

// Current user panel that syncs session state across tabs.
import Link from 'next/link';
import { useEffect, useMemo, useRef, useState } from 'react';
import { apiFetch } from '../lib/api';
import { SESSION_EVENT, SESSION_FLAG_KEY, User, logout, refreshTokens } from '../lib/auth';

function readSessionFlag() {
  // Local storage flag provides a lightweight session hint for the UI.
  if (typeof window === 'undefined') return false;
  try {
    return window.localStorage.getItem(SESSION_FLAG_KEY) === '1';
  } catch {
    return false;
  }
}

type CurrentUserProps = {
  variant?: 'panel' | 'compact';
};

export function CurrentUser({ variant = 'panel' }: CurrentUserProps) {
  const [profile, setProfile] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hadSession, setHadSession] = useState<boolean>(() => readSessionFlag());
  const hadSessionRef = useRef(hadSession);

  useEffect(() => {
    hadSessionRef.current = hadSession;
  }, [hadSession]);

  useEffect(() => {
    // Listen to storage and custom events to keep session state in sync.
    function syncFromStorage(event: StorageEvent) {
      if (event.key !== SESSION_FLAG_KEY) return;
      setHadSession(event.newValue === '1');
    }

    function handleSessionEvent(event: Event) {
      const custom = event as CustomEvent<{ hasSession: boolean }>;
      setHadSession(Boolean(custom.detail?.hasSession));
    }

    window.addEventListener('storage', syncFromStorage);
    window.addEventListener(SESSION_EVENT, handleSessionEvent as EventListener);
    return () => {
      window.removeEventListener('storage', syncFromStorage);
      window.removeEventListener(SESSION_EVENT, handleSessionEvent as EventListener);
    };
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    apiFetch<User>('/me', undefined, { isServer: false })
      .then((user) => {
        setProfile(user);
        setError(null);
      })
      .catch((err) => {
        setProfile(null);
        const message = err instanceof Error ? err.message : 'Failed to fetch profile.';
        const normalized = message.toLowerCase();
        if (normalized.includes('token') || normalized.includes('unauthorized')) {
          if (hadSessionRef.current) {
            setError('Session expired. Please log in again.');
          } else {
            setError(null);
          }
        } else {
          setError(message);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const statusText = useMemo(() => {
    if (!profile && !loading && !error) return 'Not signed in.';
    if (loading) return 'Checking session...';
    if (error) return error;
    if (profile) return `Signed in as ${profile.display_name || profile.email}`;
    return 'Signed in.';
  }, [loading, error, profile]);

  const compactStatus = useMemo(() => {
    if (loading) return 'Checking...';
    if (error) return 'Session issue';
    if (profile) return profile.display_name || profile.email;
    return 'Signed out';
  }, [loading, error, profile]);

  async function handleRefresh() {
    setLoading(true);
    setError(null);
    try {
      await refreshTokens();
      const user = await apiFetch<User>('/me', undefined, { isServer: false });
      setProfile(user);
    } catch (err) {
      setProfile(null);
      const message = err instanceof Error ? err.message : 'Failed to refresh session.';
      const normalized = message.toLowerCase();
      if (normalized.includes('token') || normalized.includes('unauthorized')) {
        setError('Session expired. Please log in again.');
      } else {
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    await logout();
    setProfile(null);
    setError(null);
  }

  if (variant === 'compact') {
    return (
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-200">
        <span className="text-[10px] font-semibold uppercase tracking-wide text-emerald-300">
          Account
        </span>
        <span className="text-slate-200">{compactStatus}</span>
        {profile ? (
          <>
            <Link
              href="/account"
              className="rounded-full border border-emerald-400/60 px-2 py-0.5 text-[11px] font-semibold text-emerald-100 transition hover:border-emerald-300 hover:text-emerald-50"
            >
              My account
            </Link>
            <button
              onClick={handleRefresh}
              className="rounded-full border border-slate-800 px-2 py-0.5 text-[11px] font-semibold text-white transition hover:border-emerald-400/60"
            >
              Refresh
            </button>
            <button
              onClick={handleLogout}
              className="rounded-full bg-slate-800 px-2 py-0.5 text-[11px] font-semibold text-white transition hover:bg-slate-700"
            >
              Log out
            </button>
          </>
        ) : (
          <>
            <Link
              href="/login"
              className="rounded-full border border-slate-800 px-2 py-0.5 text-[11px] font-semibold text-white transition hover:border-emerald-400/60"
            >
              Log in
            </Link>
            <Link
              href="/register"
              className="rounded-full border border-slate-800 px-2 py-0.5 text-[11px] font-semibold text-white transition hover:border-emerald-400/60"
            >
              Register
            </Link>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-300">Account</p>
          <p className="text-sm text-slate-200">{statusText}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {profile ? (
            <>
              <Link
                href="/account"
                className="rounded-full border border-emerald-400/60 px-3 py-1 text-[11px] font-semibold text-emerald-100 transition hover:border-emerald-300 hover:text-emerald-50"
              >
                My account
              </Link>
              <button
                onClick={handleRefresh}
                className="rounded-full border border-slate-800 px-3 py-1 text-[11px] font-semibold text-white transition hover:border-emerald-400/60"
              >
                Refresh
              </button>
              <button
                onClick={handleLogout}
                className="rounded-full bg-slate-800 px-3 py-1 text-[11px] font-semibold text-white transition hover:bg-slate-700"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="rounded-full border border-slate-800 px-3 py-1 text-[11px] font-semibold text-white transition hover:border-emerald-400/60"
              >
                Log in
              </Link>
              <Link
                href="/register"
                className="rounded-full border border-slate-800 px-3 py-1 text-[11px] font-semibold text-white transition hover:border-emerald-400/60"
              >
                Register
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
