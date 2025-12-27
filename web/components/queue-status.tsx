'use client';

// Ops queue status card for authenticated users.

import { useEffect, useState } from 'react';

import { QueueSnapshot, fetchQueueHealth } from '../lib/ops';

export function QueueStatus() {
  const [snapshot, setSnapshot] = useState<QueueSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Avoid state updates after unmount.
    let cancelled = false;
    setLoading(true);
    fetchQueueHealth()
      .then((res) => {
        if (cancelled) return;
        setSnapshot(res);
        setError(null);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message);
        setSnapshot(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const status = snapshot?.status ?? 'offline';
  const warnings = snapshot?.warnings ?? [];
  const statusColor =
    status === 'online'
      ? 'text-emerald-300'
      : status === 'degraded'
        ? 'text-amber-300'
        : 'text-red-300';

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className={`flex items-center gap-2 text-sm font-semibold ${statusColor}`}>
            <span>{status === 'online' ? '●' : status === 'degraded' ? '◐' : '○'}</span>
            Queue health
          </p>
          <p className="mt-1 text-xs text-slate-300">
            {loading
              ? 'Checking worker + scheduler status...'
              : error
                ? normalizeError(error)
                : `Workers: ${snapshot?.workers.length ?? 0}, Scheduler jobs: ${
                    snapshot?.scheduler?.scheduled_jobs ?? 'n/a'
                  }`}
          </p>
        </div>
        {snapshot?.checked_at && (
          <span className="rounded-full bg-slate-800 px-2 py-1 text-[10px] text-slate-400">
            {new Date(snapshot.checked_at).toLocaleTimeString()}
          </span>
        )}
      </div>

      {warnings.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
          {warnings.map((warning) => (
            <span
              key={warning}
              className="rounded-full border border-amber-400/40 bg-amber-500/10 px-3 py-1 text-amber-100"
            >
              {warning.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      )}

      {snapshot?.queues && snapshot.queues.length > 0 && (
        <div className="mt-3 grid gap-2 text-[11px] text-slate-200 sm:grid-cols-2">
          {snapshot.queues.map((queue) => (
            <div
              key={queue.name}
              className="rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-2"
            >
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-white">{queue.name}</p>
                <p className="text-[10px] text-slate-400">{queue.size} queued</p>
              </div>
              <p className="mt-1 text-[10px] text-slate-400">
                Started: {queue.started} · Scheduled: {queue.scheduled} · Failed: {queue.failed}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function normalizeError(message: string) {
  // Hide auth errors behind a friendly message.
  const normalized = message.toLowerCase();
  if (normalized.includes('unauthorized') || normalized.includes('token')) {
    return 'Sign in to view queue health.';
  }
  return message;
}
