"use client";

import { useEffect, useMemo, useRef, useState } from 'react';
import { apiFetch } from '../lib/api';
import { SESSION_EVENT, SESSION_FLAG_KEY, User, logout, refreshTokens } from '../lib/auth';

function readSessionFlag() {
  if (typeof window === 'undefined') return false;
  try {
    return window.localStorage.getItem(SESSION_FLAG_KEY) === '1';
  } catch {
    return false;
  }
}

export function CurrentUser() {
  const [profile, setProfile] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hadSession, setHadSession] = useState<boolean>(() => readSessionFlag());
  const hadSessionRef = useRef(hadSession);

  useEffect(() => {
    hadSessionRef.current = hadSession;
  }, [hadSession]);

  useEffect(() => {
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
    if (!profile && !loading && !error) return 'Not signed in yet. Log in or register to see your profile.';
    if (loading) return 'Fetching your profile...';
    if (error) return error;
    if (profile) return `Signed in as ${profile.display_name || profile.email}`;
    return 'Signed in.';
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

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-emerald-300">Signed-in status</p>
          <p className="text-sm text-slate-200">{statusText}</p>
        </div>
        {profile && (
          <div className="flex gap-2">
            <button
              onClick={handleRefresh}
              className="rounded-md border border-slate-800 px-3 py-1 text-xs font-semibold text-white transition hover:border-emerald-400/60"
            >
              Refresh
            </button>
            <button
              onClick={handleLogout}
              className="rounded-md bg-slate-800 px-3 py-1 text-xs font-semibold text-white transition hover:bg-slate-700"
            >
              Log out
            </button>
          </div>
        )}
      </div>

      {profile && (
        <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-200">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-white">{profile.display_name || profile.email}</span>
            <span className="text-xs text-slate-400">User ID: {profile.id}</span>
          </div>
          <p className="text-xs text-slate-300">Email: {profile.email}</p>
        </div>
      )}
    </div>
  );
}
