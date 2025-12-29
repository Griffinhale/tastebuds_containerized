'use client';

// Home dashboard builder for signed-in users, with placeholders for guests.

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { apiFetch } from '../lib/api';
import { SESSION_EVENT, SESSION_FLAG_KEY, type User } from '../lib/auth';

type ModuleOption = {
  id: string;
  label: string;
  description: string;
  href: string;
};

const MODULE_OPTIONS: ModuleOption[] = [
  {
    id: 'library',
    label: 'Library',
    description: 'Track progress and logs.',
    href: '/library',
  },
  {
    id: 'menus',
    label: 'Menus',
    description: 'Build and share menus.',
    href: '/menus',
  },
  {
    id: 'search',
    label: 'Search',
    description: 'Find new items.',
    href: '/search',
  },
  {
    id: 'account',
    label: 'Account',
    description: 'Profile, security, and preferences.',
    href: '/account#profile',
  },
  {
    id: 'integrations',
    label: 'External integrations',
    description: 'Connect your services.',
    href: '/account#integrations',
  },
];

const STORAGE_KEY = 'tastebuds_home_modules';

function readPinnedModules() {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((value): value is string => typeof value === 'string');
  } catch {
    return [];
  }
}

function writePinnedModules(modules: string[]) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(modules));
  } catch {
    // Ignore local storage failures (private mode, etc.).
  }
}

export function HomeDashboard() {
  const [profile, setProfile] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [pinned, setPinned] = useState<string[]>([]);
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    setPinned(readPinnedModules());
  }, []);

  useEffect(() => {
    writePinnedModules(pinned);
  }, [pinned]);

  useEffect(() => {
    let cancelled = false;
    apiFetch<User>('/me', undefined, { isServer: false })
      .then((user) => {
        if (!cancelled) setProfile(user);
      })
      .catch(() => {
        if (!cancelled) setProfile(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const syncSession = (hasSession: boolean) => {
      if (!hasSession) {
        setProfile(null);
        setLoading(false);
        return;
      }
      setLoading(true);
      apiFetch<User>('/me', undefined, { isServer: false })
        .then((user) => {
          if (!cancelled) setProfile(user);
        })
        .catch(() => {
          if (!cancelled) setProfile(null);
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    };

    function syncFromStorage(event: StorageEvent) {
      if (event.key !== SESSION_FLAG_KEY) return;
      syncSession(event.newValue === '1');
    }

    function handleSessionEvent(event: Event) {
      const custom = event as CustomEvent<{ hasSession: boolean }>;
      syncSession(Boolean(custom.detail?.hasSession));
    }

    window.addEventListener('storage', syncFromStorage);
    window.addEventListener(SESSION_EVENT, handleSessionEvent as EventListener);
    return () => {
      cancelled = true;
      window.removeEventListener('storage', syncFromStorage);
      window.removeEventListener(SESSION_EVENT, handleSessionEvent as EventListener);
    };
  }, []);

  const pinnedModules = useMemo(
    () => MODULE_OPTIONS.filter((module) => pinned.includes(module.id)),
    [pinned]
  );
  const unpinnedModules = useMemo(
    () => MODULE_OPTIONS.filter((module) => !pinned.includes(module.id)),
    [pinned]
  );

  const togglePinned = (id: string) => {
    setPinned((current) =>
      current.includes(id) ? current.filter((moduleId) => moduleId !== id) : [...current, id]
    );
  };

  if (loading) {
    return (
      <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
        <p className="text-sm text-slate-300">Loading your dashboard...</p>
      </section>
    );
  }

  if (!profile) {
    return (
      <section className="grid gap-4 md:grid-cols-2">
        <PlaceholderCard
          title="Top lists"
          description="Placeholder component for featured lists."
        />
        <PlaceholderCard
          title="Most favorited items"
          description="Placeholder component for favorites."
        />
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-2xl font-semibold text-white">Your dashboard</h2>
        <button
          type="button"
          onClick={() => setEditing((current) => !current)}
          className="rounded-full border border-emerald-400/50 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-100 transition hover:border-emerald-300 hover:text-emerald-50"
        >
          {editing ? 'Done' : 'Edit pins'}
        </button>
      </div>

      {editing ? (
        <div className="grid gap-6 lg:grid-cols-[1.05fr,0.95fr]">
          <div className="space-y-3">
            <p className="text-xs uppercase tracking-wide text-slate-400">Pinned modules</p>
            {pinnedModules.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 p-6 text-sm text-slate-300">
                No modules pinned yet.
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {pinnedModules.map((module) => (
                  <ModuleToggle
                    key={module.id}
                    module={module}
                    pinned
                    onToggle={togglePinned}
                  />
                ))}
              </div>
            )}
          </div>

          <div className="space-y-3">
            <p className="text-xs uppercase tracking-wide text-slate-400">Available modules</p>
            {unpinnedModules.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 p-6 text-sm text-slate-300">
                All modules pinned.
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {unpinnedModules.map((module) => (
                  <ModuleToggle
                    key={module.id}
                    module={module}
                    pinned={false}
                    onToggle={togglePinned}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      ) : pinnedModules.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 p-6 text-sm text-slate-300">
          No modules pinned yet. Click Edit pins to start.
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {pinnedModules.map((module) => (
            <Link
              key={module.id}
              href={module.href}
              className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 transition hover:border-emerald-400/60"
            >
              <p className="text-sm font-semibold text-white">{module.label}</p>
              <p className="mt-1 text-xs text-slate-300">{module.description}</p>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}

function ModuleToggle({
  module,
  pinned,
  onToggle,
}: {
  module: ModuleOption;
  pinned: boolean;
  onToggle: (id: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onToggle(module.id)}
      aria-pressed={pinned}
      className={`rounded-xl border p-4 text-left transition ${
        pinned
          ? 'border-emerald-400/60 bg-emerald-500/10'
          : 'border-slate-800 bg-slate-900/60 hover:border-emerald-400/40'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">{module.label}</p>
          <p className="mt-1 text-xs text-slate-300">{module.description}</p>
        </div>
        <span className={`text-[10px] font-semibold ${pinned ? 'text-emerald-200' : 'text-slate-400'}`}>
          {pinned ? 'Pinned' : 'Pin'}
        </span>
      </div>
    </button>
  );
}

function PlaceholderCard({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 p-6">
      <p className="text-xs uppercase tracking-wide text-slate-400">{title}</p>
      <p className="mt-2 text-sm text-slate-300">{description}</p>
    </div>
  );
}
