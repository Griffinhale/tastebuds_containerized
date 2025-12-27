'use client';

// Library dashboard with status tracking, logs, and quick actions.

import { FormEvent, useEffect, useMemo, useState } from 'react';

import {
  CreateLogInput,
  LibraryOverview,
  MediaItemBase,
  UpdateStateInput,
  UserItemLog,
  UserItemLogType,
  UserItemStatus,
  createLog,
  deleteLog,
  getLibraryOverview,
  listLogs,
  upsertState,
} from '../lib/library';

const logTypeOptions: { value: UserItemLogType; label: string; description: string }[] = [
  { value: 'started', label: 'Started', description: 'Kick off a new session.' },
  { value: 'progress', label: 'Progress', description: 'Update progress or pacing.' },
  { value: 'finished', label: 'Finished', description: 'Mark completion.' },
  { value: 'note', label: 'Note', description: 'Drop quick thoughts.' },
  { value: 'goal', label: 'Goal', description: 'Set a target or deadline.' },
];

const statusOptions: { value: UserItemStatus; label: string }[] = [
  { value: 'want_to_consume', label: 'Want to consume' },
  { value: 'currently_consuming', label: 'Currently consuming' },
  { value: 'paused', label: 'Paused' },
  { value: 'consumed', label: 'Consumed' },
  { value: 'dropped', label: 'Dropped' },
];

type LogDraft = {
  media_item_id: string;
  log_type: UserItemLogType;
  notes: string;
  minutes_spent: string;
  progress_percent: string;
  goal_target: string;
  goal_due_on: string;
};

type StateDraft = {
  media_item_id: string;
  status: UserItemStatus;
  rating: string;
  favorite: boolean;
  notes: string;
};

export function LibraryDashboard() {
  const [library, setLibrary] = useState<LibraryOverview | null>(null);
  const [logs, setLogs] = useState<UserItemLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [logFilter, setLogFilter] = useState<UserItemLogType | 'all'>('all');

  const [logDraft, setLogDraft] = useState<LogDraft>({
    media_item_id: '',
    log_type: 'note',
    notes: '',
    minutes_spent: '',
    progress_percent: '',
    goal_target: '',
    goal_due_on: '',
  });

  const [stateDraft, setStateDraft] = useState<StateDraft>({
    media_item_id: '',
    status: 'want_to_consume',
    rating: '',
    favorite: false,
    notes: '',
  });

  const libraryItems = library?.items ?? [];

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [libraryPayload, logPayload] = await Promise.all([
        getLibraryOverview(),
        listLogs({ limit: 50 }),
      ]);
      setLibrary(libraryPayload);
      setLogs(logPayload);
      setLastUpdated(new Date());
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load library.';
      const normalized = message.toLowerCase();
      if (normalized.includes('unauthorized') || normalized.includes('token')) {
        setError('Log in to view your library and logs.');
      } else {
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (!libraryItems.length) return;
    setLogDraft((draft) => (draft.media_item_id ? draft : { ...draft, media_item_id: libraryItems[0].media_item.id }));
    setStateDraft((draft) =>
      draft.media_item_id ? draft : { ...draft, media_item_id: libraryItems[0].media_item.id }
    );
  }, [libraryItems]);

  useEffect(() => {
    if (!stateDraft.media_item_id) return;
    const selected = libraryItems.find((item) => item.media_item.id === stateDraft.media_item_id);
    if (!selected) return;
    setStateDraft((draft) => ({
      ...draft,
      status: selected.state?.status ?? 'want_to_consume',
      rating: selected.state?.rating?.toString() ?? '',
      favorite: selected.state?.favorite ?? false,
      notes: selected.state?.notes ?? '',
    }));
  }, [libraryItems, stateDraft.media_item_id]);

  const statusText = useMemo(() => {
    if (loading) return 'Loading library...';
    if (error) return error;
    if (!libraryItems.length) return 'No library entries yet. Start by logging an item.';
    return `Tracking ${libraryItems.length} item${libraryItems.length === 1 ? '' : 's'}.`;
  }, [libraryItems.length, loading, error]);

  const filteredLogs = useMemo(() => {
    if (logFilter === 'all') return logs;
    return logs.filter((log) => log.log_type === logFilter);
  }, [logs, logFilter]);

  const goalLogs = useMemo(() => logs.filter((log) => log.log_type === 'goal'), [logs]);

  const selectedLogType = logTypeOptions.find((option) => option.value === logDraft.log_type);

  async function handleCreateLog(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!logDraft.media_item_id) {
      setError('Select a library item to log.');
      return;
    }

    const payload: CreateLogInput = {
      media_item_id: logDraft.media_item_id,
      log_type: logDraft.log_type,
    };
    if (logDraft.notes.trim()) payload.notes = logDraft.notes.trim();
    if (logDraft.minutes_spent !== '') payload.minutes_spent = Number(logDraft.minutes_spent);
    if (logDraft.progress_percent !== '') payload.progress_percent = Number(logDraft.progress_percent);
    if (logDraft.goal_target.trim()) payload.goal_target = logDraft.goal_target.trim();
    if (logDraft.goal_due_on) payload.goal_due_on = logDraft.goal_due_on;

    try {
      await createLog(payload);
      setLogDraft((draft) => ({
        ...draft,
        notes: '',
        minutes_spent: '',
        progress_percent: '',
        goal_target: '',
        goal_due_on: '',
      }));
      await loadData();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create log entry.';
      setError(message);
    }
  }

  async function handleUpdateState(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!stateDraft.media_item_id) {
      setError('Select a library item to update.');
      return;
    }

    const payload: UpdateStateInput = {
      status: stateDraft.status,
      favorite: stateDraft.favorite,
    };
    payload.rating = stateDraft.rating ? Number(stateDraft.rating) : null;
    payload.notes = stateDraft.notes.trim() || null;

    try {
      await upsertState(stateDraft.media_item_id, payload);
      await loadData();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update status.';
      setError(message);
    }
  }

  async function handleDeleteLog(logId: string) {
    try {
      await deleteLog(logId);
      await loadData();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete log entry.';
      setError(message);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-emerald-300">Library snapshot</p>
            <p className="text-sm text-slate-200">{statusText}</p>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="text-sm text-emerald-300 underline decoration-emerald-300/60 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Refresh
          </button>
        </div>
        {lastUpdated && !loading && !error && (
          <p className="mt-2 text-xs text-slate-400">Last updated {lastUpdated.toLocaleTimeString()}</p>
        )}

        {library && (
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <SummaryCard label="Total" value={library.summary.total} />
            <SummaryCard label="Consuming" value={library.summary.currently_consuming} />
            <SummaryCard label="Want" value={library.summary.want_to_consume} />
            <SummaryCard label="Consumed" value={library.summary.consumed} />
            <SummaryCard label="Paused" value={library.summary.paused} />
            <SummaryCard label="Dropped" value={library.summary.dropped} />
          </div>
        )}
      </section>

      <div className="grid gap-4 lg:grid-cols-[1.1fr,0.9fr]">
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-emerald-300">Next up queue</p>
              <p className="text-xs text-slate-300">Auto-built from your want/active items.</p>
            </div>
          </div>
          {!library?.next_up.length && (
            <p className="mt-3 text-sm text-slate-400">No next-up items yet.</p>
          )}
          {library?.next_up.length ? (
            <ul className="mt-3 space-y-3">
              {library.next_up.map((entry) => (
                <li key={entry.media_item.id} className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                  <MediaHeading media={entry.media_item} />
                  <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-slate-300">
                    <span className="rounded-full border border-slate-800 px-2 py-1">
                      Status: {formatStatus(entry.state?.status)}
                    </span>
                    {entry.last_log && (
                      <span className="rounded-full border border-slate-800 px-2 py-1">
                        Last log: {formatLogType(entry.last_log.log_type)}
                      </span>
                    )}
                    {entry.last_activity_at && (
                      <span className="rounded-full border border-slate-800 px-2 py-1">
                        Active {formatDate(entry.last_activity_at)}
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div>
            <p className="text-sm font-semibold text-emerald-300">Goals</p>
            <p className="text-xs text-slate-300">Targets pulled from your goal logs.</p>
          </div>
          {!goalLogs.length && (
            <p className="mt-3 text-sm text-slate-400">No goals logged yet.</p>
          )}
          {goalLogs.length ? (
            <ul className="mt-3 space-y-3">
              {goalLogs.slice(0, 4).map((goal) => (
                <li key={goal.id} className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                  <p className="text-xs uppercase tracking-wide text-emerald-200">Goal</p>
                  <p className="text-sm font-semibold text-white">
                    {goal.media_item?.title ?? 'Untitled item'}
                  </p>
                  {goal.goal_target && <p className="text-xs text-slate-300">{goal.goal_target}</p>}
                  <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-slate-400">
                    {goal.goal_due_on && <span>Due {formatDate(goal.goal_due_on)}</span>}
                    <span>Logged {formatDate(goal.logged_at)}</span>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.05fr,0.95fr]">
        <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
          <header className="space-y-1">
            <p className="text-sm font-semibold text-emerald-300">Quick log</p>
            <p className="text-xs text-slate-300">Capture progress, notes, or goals in seconds.</p>
          </header>
          <form onSubmit={handleCreateLog} className="mt-4 space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-slate-300">
                Library item
                <select
                  value={logDraft.media_item_id}
                  onChange={(event) =>
                    setLogDraft((draft) => ({ ...draft, media_item_id: event.target.value }))
                  }
                  className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"
                >
                  <option value="" disabled>
                    Select an item
                  </option>
                  {libraryItems.map((item) => (
                    <option key={item.media_item.id} value={item.media_item.id}>
                      {item.media_item.title}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-slate-300">
                Log type
                <select
                  value={logDraft.log_type}
                  onChange={(event) =>
                    setLogDraft((draft) => ({
                      ...draft,
                      log_type: event.target.value as UserItemLogType,
                    }))
                  }
                  className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"
                >
                  {logTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {selectedLogType && (
              <p className="rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-400">
                {selectedLogType.description}
              </p>
            )}

            {(logDraft.log_type === 'started' ||
              logDraft.log_type === 'progress' ||
              logDraft.log_type === 'finished') && (
              <label className="text-xs text-slate-300">
                Minutes spent
                <input
                  type="number"
                  min={0}
                  value={logDraft.minutes_spent}
                  onChange={(event) =>
                    setLogDraft((draft) => ({ ...draft, minutes_spent: event.target.value }))
                  }
                  className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"
                />
              </label>
            )}

            {logDraft.log_type === 'progress' && (
              <label className="text-xs text-slate-300">
                Progress percent
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={logDraft.progress_percent}
                  onChange={(event) =>
                    setLogDraft((draft) => ({ ...draft, progress_percent: event.target.value }))
                  }
                  className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"
                />
              </label>
            )}

            {logDraft.log_type === 'goal' && (
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="text-xs text-slate-300">
                  Goal target
                  <input
                    type="text"
                    value={logDraft.goal_target}
                    onChange={(event) =>
                      setLogDraft((draft) => ({ ...draft, goal_target: event.target.value }))
                    }
                    className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"
                  />
                </label>
                <label className="text-xs text-slate-300">
                  Goal due date
                  <input
                    type="date"
                    value={logDraft.goal_due_on}
                    onChange={(event) =>
                      setLogDraft((draft) => ({ ...draft, goal_due_on: event.target.value }))
                    }
                    className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"
                  />
                </label>
              </div>
            )}

            <label className="text-xs text-slate-300">
              Notes
              <textarea
                value={logDraft.notes}
                onChange={(event) => setLogDraft((draft) => ({ ...draft, notes: event.target.value }))}
                rows={3}
                className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"
              />
            </label>

            <button
              type="submit"
              className="rounded-md bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400"
            >
              Save log
            </button>
          </form>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
          <header className="space-y-1">
            <p className="text-sm font-semibold text-emerald-300">Status update</p>
            <p className="text-xs text-slate-300">Adjust your library status, rating, and notes.</p>
          </header>
          <form onSubmit={handleUpdateState} className="mt-4 space-y-3">
            <label className="text-xs text-slate-300">
              Library item
              <select
                value={stateDraft.media_item_id}
                onChange={(event) =>
                  setStateDraft((draft) => ({ ...draft, media_item_id: event.target.value }))
                }
                className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"
              >
                <option value="" disabled>
                  Select an item
                </option>
                {libraryItems.map((item) => (
                  <option key={item.media_item.id} value={item.media_item.id}>
                    {item.media_item.title}
                  </option>
                ))}
              </select>
            </label>

            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-slate-300">
                Status
                <select
                  value={stateDraft.status}
                  onChange={(event) =>
                    setStateDraft((draft) => ({
                      ...draft,
                      status: event.target.value as UserItemStatus,
                    }))
                  }
                  className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"
                >
                  {statusOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="text-xs text-slate-300">
                Rating (0-10)
                <input
                  type="number"
                  min={0}
                  max={10}
                  value={stateDraft.rating}
                  onChange={(event) =>
                    setStateDraft((draft) => ({ ...draft, rating: event.target.value }))
                  }
                  className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"
                />
              </label>
            </div>

            <label className="flex items-center gap-2 text-xs text-slate-300">
              <input
                type="checkbox"
                checked={stateDraft.favorite}
                onChange={(event) =>
                  setStateDraft((draft) => ({ ...draft, favorite: event.target.checked }))
                }
                className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-emerald-400"
              />
              Mark as favorite
            </label>

            <label className="text-xs text-slate-300">
              Notes
              <textarea
                value={stateDraft.notes}
                onChange={(event) => setStateDraft((draft) => ({ ...draft, notes: event.target.value }))}
                rows={3}
                className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"
              />
            </label>

            <button
              type="submit"
              className="rounded-md bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400"
            >
              Update status
            </button>
          </form>
        </section>
      </div>

      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-emerald-300">Library items</p>
            <p className="text-xs text-slate-300">Snapshot of each tracked title.</p>
          </div>
        </div>

        {!libraryItems.length && !loading && (
          <p className="mt-4 text-sm text-slate-400">No entries yet.</p>
        )}

        {libraryItems.length ? (
          <ul className="mt-4 grid gap-3 md:grid-cols-2">
            {libraryItems.map((entry) => (
              <li key={entry.media_item.id} className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                <div className="flex items-start gap-3">
                  <CoverArt media={entry.media_item} />
                  <div className="flex-1">
                    <MediaHeading media={entry.media_item} />
                    <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-slate-300">
                      <span className="rounded-full border border-slate-800 px-2 py-1">
                        Status: {formatStatus(entry.state?.status)}
                      </span>
                      <span className="rounded-full border border-slate-800 px-2 py-1">
                        Logs: {entry.log_count}
                      </span>
                      {entry.last_activity_at && (
                        <span className="rounded-full border border-slate-800 px-2 py-1">
                          Active {formatDate(entry.last_activity_at)}
                        </span>
                      )}
                    </div>
                    {entry.last_log?.notes && (
                      <p className="mt-2 text-xs text-slate-400">“{entry.last_log.notes}”</p>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-emerald-300">Log timeline</p>
            <p className="text-xs text-slate-300">Latest activity across your library.</p>
          </div>
          <label className="text-xs text-slate-300">
            Filter
            <select
              value={logFilter}
              onChange={(event) => setLogFilter(event.target.value as UserItemLogType | 'all')}
              className="mt-1 w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white"
            >
              <option value="all">All</option>
              {logTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        {!filteredLogs.length && !loading && (
          <p className="mt-4 text-sm text-slate-400">No log entries yet.</p>
        )}

        {filteredLogs.length ? (
          <ul className="mt-4 space-y-3">
            {filteredLogs.map((log) => (
              <li key={log.id} className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-emerald-200">
                      {formatLogType(log.log_type)}
                    </p>
                    <p className="text-sm font-semibold text-white">
                      {log.media_item?.title ?? 'Untitled item'}
                    </p>
                    {log.notes && <p className="text-xs text-slate-300">{log.notes}</p>}
                    <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-slate-400">
                      <span>Logged {formatDate(log.logged_at)}</span>
                      {log.minutes_spent ? <span>{log.minutes_spent} mins</span> : null}
                      {log.progress_percent !== null && log.progress_percent !== undefined ? (
                        <span>{log.progress_percent}%</span>
                      ) : null}
                      {log.goal_due_on ? <span>Due {formatDate(log.goal_due_on)}</span> : null}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteLog(log.id)}
                    className="text-xs text-slate-400 underline decoration-slate-500/60"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-lg font-semibold text-white">{value}</p>
    </div>
  );
}

function CoverArt({ media }: { media: MediaItemBase }) {
  return (
    <div className="h-16 w-12 overflow-hidden rounded border border-slate-800 bg-slate-900">
      {media.cover_image_url ? (
        <img
          src={media.cover_image_url}
          alt={media.title}
          className="h-full w-full object-cover"
          referrerPolicy="no-referrer"
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center text-[10px] uppercase tracking-wide text-slate-500">
          No art
        </div>
      )}
    </div>
  );
}

function MediaHeading({ media }: { media: MediaItemBase }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-emerald-200">{media.media_type}</p>
      <p className="text-sm font-semibold text-white">{media.title}</p>
      {media.subtitle && <p className="text-xs text-slate-300">{media.subtitle}</p>}
    </div>
  );
}

function formatDate(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString();
}

function formatLogType(value: UserItemLogType) {
  return logTypeOptions.find((option) => option.value === value)?.label ?? value;
}

function formatStatus(status?: UserItemStatus | null) {
  if (!status) return 'Untracked';
  return statusOptions.find((option) => option.value === status)?.label ?? status;
}
