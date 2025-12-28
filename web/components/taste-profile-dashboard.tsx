'use client';

// Taste profile dashboard for preference signals.

import { useEffect, useMemo, useState } from 'react';

import { TasteProfile, getTasteProfile, refreshTasteProfile } from '../lib/taste-profile';

export function TasteProfileDashboard() {
  const [profile, setProfile] = useState<TasteProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const summary = profile?.profile.summary;
  const topTags = profile?.profile.top_tags ?? [];
  const mediaTypeCounts = profile?.profile.media_type_counts ?? {};
  const menuMediaTypeCounts = profile?.profile.menu_media_type_counts ?? {};
  const logCounts = profile?.profile.log_counts ?? {};

  useEffect(() => {
    setLoading(true);
    getTasteProfile()
      .then((data) => {
        setProfile(data);
        setError(null);
      })
      .catch((err) => {
        const message = err instanceof Error ? err.message : 'Failed to load taste profile.';
        setError(message);
        setProfile(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const lastGenerated = useMemo(() => {
    if (!profile?.generated_at) return 'Unknown';
    return new Date(profile.generated_at).toLocaleString();
  }, [profile?.generated_at]);

  async function handleRefresh() {
    if (refreshing) return;
    setRefreshing(true);
    setError(null);
    try {
      const data = await refreshTasteProfile();
      setProfile(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to refresh profile.';
      setError(message);
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 p-6 shadow-lg shadow-emerald-500/10 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-emerald-300">Taste profile</p>
          <h1 className="text-3xl font-semibold text-white">Your media balance at a glance.</h1>
          <p className="text-sm text-slate-300">Last generated: {lastGenerated}</p>
        </div>
        <button
          onClick={handleRefresh}
          className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400"
          disabled={refreshing}
        >
          {refreshing ? 'Refreshing...' : 'Refresh profile'}
        </button>
      </header>

      {loading && <p className="text-sm text-slate-300">Loading taste profile...</p>}
      {error && <p className="text-sm text-red-300">{error}</p>}

      {!loading && !error && profile && (
        <div className="grid gap-6 lg:grid-cols-[1.2fr,0.8fr]">
          <div className="space-y-6">
            <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
              <p className="text-xs uppercase tracking-wide text-emerald-200">Signals</p>
              <div className="mt-3 grid gap-4 sm:grid-cols-2">
                <Metric label="Menus" value={summary?.menus ?? 0} />
                <Metric label="Courses" value={summary?.courses ?? 0} />
                <Metric label="Items" value={summary?.items ?? 0} />
                <Metric label="Favorites" value={summary?.favorites ?? 0} />
                <Metric label="Minutes logged" value={summary?.minutes_spent ?? 0} />
                <Metric label="Logs" value={profile.profile.signals?.logs ?? 0} />
              </div>
            </section>

            <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
              <p className="text-xs uppercase tracking-wide text-emerald-200">Media mix</p>
              <MetricList items={mediaTypeCounts} emptyCopy="No media entries yet." />
              <p className="mt-4 text-xs uppercase tracking-wide text-emerald-200">Menu mix</p>
              <MetricList items={menuMediaTypeCounts} emptyCopy="No menu entries yet." />
            </section>
          </div>

          <div className="space-y-6">
            <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
              <p className="text-xs uppercase tracking-wide text-emerald-200">Top tags</p>
              {topTags.length === 0 ? (
                <p className="mt-3 text-sm text-slate-300">No tags collected yet.</p>
              ) : (
                <ul className="mt-3 space-y-2 text-sm text-slate-200">
                  {topTags.map((tag) => (
                    <li key={tag.name} className="flex items-center justify-between">
                      <span>{tag.name}</span>
                      <span className="text-xs text-slate-400">{tag.count}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
              <p className="text-xs uppercase tracking-wide text-emerald-200">Log activity</p>
              <MetricList items={logCounts} emptyCopy="No logs yet." />
            </section>
          </div>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="text-lg font-semibold text-white">{value}</p>
    </div>
  );
}

function MetricList({ items, emptyCopy }: { items: Record<string, number>; emptyCopy: string }) {
  const entries = Object.entries(items);
  if (!entries.length) {
    return <p className="mt-3 text-sm text-slate-300">{emptyCopy}</p>;
  }
  return (
    <ul className="mt-3 space-y-2 text-sm text-slate-200">
      {entries.map(([key, value]) => (
        <li key={key} className="flex items-center justify-between">
          <span className="capitalize">{key.replace(/_/g, ' ')}</span>
          <span className="text-xs text-slate-400">{value}</span>
        </li>
      ))}
    </ul>
  );
}
