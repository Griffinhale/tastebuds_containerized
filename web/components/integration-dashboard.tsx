// Integration management dashboard with provider status and actions.
'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import { apiFetch, ApiError } from '../lib/api';
import { fetchQueueHealth, filterQueues, QueueSnapshot } from '../lib/ops';

type IntegrationCapabilities = {
  supports_webhooks: boolean;
  supports_export: boolean;
  supports_sync: boolean;
};

type IntegrationStatus = {
  provider: string;
  display_name: string;
  auth_type: string;
  connected: boolean;
  status: string;
  expires_at?: string | null;
  rotated_at?: string | null;
  last_error?: string | null;
  webhook_token_prefix?: string | null;
  capabilities?: IntegrationCapabilities;
};

type WebhookTokenResponse = {
  provider: string;
  webhook_url: string;
  token_prefix: string;
};

type IntegrationEvent = {
  id: string;
  provider: string;
  event_type?: string | null;
  title?: string | null;
  source_name?: string | null;
  status: string;
  created_at: string;
};

type SyncStatus = {
  status: 'idle' | 'working' | 'success' | 'error';
  lastTriggeredAt?: string;
  message?: string;
};

const providerFields: Record<
  string,
  { label: string; fields: { name: string; label: string; type: string; placeholder?: string }[] }
> = {
  arr: {
    label: 'Arr Suite',
    fields: [
      {
        name: 'base_url',
        label: 'Server URL',
        type: 'text',
        placeholder: 'https://radarr.local:7878',
      },
      { name: 'api_key', label: 'API Key', type: 'password' },
    ],
  },
  jellyfin: {
    label: 'Jellyfin',
    fields: [
      {
        name: 'base_url',
        label: 'Server URL',
        type: 'text',
        placeholder: 'https://jellyfin.local:8096',
      },
      { name: 'api_key', label: 'API Key', type: 'password' },
    ],
  },
  plex: {
    label: 'Plex',
    fields: [
      {
        name: 'base_url',
        label: 'Server URL',
        type: 'text',
        placeholder: 'https://plex.local:32400',
      },
      { name: 'api_key', label: 'Token', type: 'password' },
    ],
  },
};

export function IntegrationDashboard() {
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [arrQueue, setArrQueue] = useState<IntegrationEvent[]>([]);
  const [queueSnapshot, setQueueSnapshot] = useState<QueueSnapshot | null>(null);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [queueLoading, setQueueLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [webhookUrl, setWebhookUrl] = useState<string | null>(null);
  const [webhookPrefix, setWebhookPrefix] = useState<string | null>(null);
  const [formState, setFormState] = useState<Record<string, Record<string, string>>>({});
  const [syncState, setSyncState] = useState<Record<string, SyncStatus>>({});

  const refreshIntegrations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<IntegrationStatus[]>('/integrations');
      setIntegrations(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Unable to load integrations.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshArrQueue = useCallback(async () => {
    try {
      const data = await apiFetch<IntegrationEvent[]>(
        '/integrations/arr/queue?status_filter=pending'
      );
      setArrQueue(data);
    } catch {
      setArrQueue([]);
    }
  }, []);

  const refreshQueueHealth = useCallback(async () => {
    setQueueLoading(true);
    try {
      const data = await fetchQueueHealth();
      setQueueSnapshot(data);
      setQueueError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to load queue health.';
      setQueueError(message);
      setQueueSnapshot(null);
    } finally {
      setQueueLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshIntegrations();
    void refreshArrQueue();
    void refreshQueueHealth();
  }, [refreshIntegrations, refreshArrQueue, refreshQueueHealth]);

  const handleOAuthConnect = async () => {
    try {
      const data = await apiFetch<{ authorization_url: string }>('/integrations/spotify/authorize');
      window.location.href = data.authorization_url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to start Spotify authorization.');
    }
  };

  const handleDisconnect = async (provider: string) => {
    try {
      await apiFetch<void>(`/integrations/${provider}`, { method: 'DELETE' });
      await refreshIntegrations();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Unable to disconnect ${provider}.`);
    }
  };

  const handleRotate = async (provider: string) => {
    try {
      await apiFetch(`/integrations/${provider}/rotate`, { method: 'POST' });
      await refreshIntegrations();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Unable to rotate ${provider}.`);
    }
  };

  const handleCredentialsSave = async (provider: string) => {
    const rawPayload = formState[provider] || {};
    const payload = Object.fromEntries(
      Object.entries(rawPayload).filter(([, value]) => value.trim().length > 0)
    );
    if (!Object.keys(payload).length) {
      setError('Provide at least one credential value before saving.');
      return;
    }
    try {
      await apiFetch(`/integrations/${provider}/credentials`, {
        method: 'POST',
        body: JSON.stringify({ payload }),
      });
      await refreshIntegrations();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Unable to save ${provider} credentials.`);
    }
  };

  const handleWebhookToken = async () => {
    try {
      const data = await apiFetch<WebhookTokenResponse>('/integrations/arr/webhook-token', {
        method: 'POST',
      });
      setWebhookUrl(data.webhook_url);
      setWebhookPrefix(data.token_prefix);
      await refreshIntegrations();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to generate webhook token.');
    }
  };

  const handleArrIngest = async (eventId: string) => {
    try {
      await apiFetch(`/integrations/arr/queue/${eventId}/ingest`, { method: 'POST' });
      await refreshArrQueue();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to ingest Arr event.');
    }
  };

  const handleSync = async (provider: string) => {
    setSyncState((prev) => ({
      ...prev,
      [provider]: {
        status: 'working',
        lastTriggeredAt: new Date().toISOString(),
      },
    }));
    try {
      await apiFetch(`/integrations/${provider}/sync`, {
        method: 'POST',
        body: JSON.stringify({ external_id: 'library', action: 'sync', force_refresh: false }),
      });
      setSyncState((prev) => ({
        ...prev,
        [provider]: {
          status: 'success',
          lastTriggeredAt: prev[provider]?.lastTriggeredAt,
          message: 'Sync queued.',
        },
      }));
      await refreshQueueHealth();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : `Unable to sync ${provider}.`;
      setSyncState((prev) => ({
        ...prev,
        [provider]: {
          status: 'error',
          lastTriggeredAt: prev[provider]?.lastTriggeredAt,
          message,
        },
      }));
      setError(message);
    }
  };

  const queueStats = useMemo(
    () =>
      filterQueues(queueSnapshot, [
        'integrations',
        'webhooks',
        'sync',
        'ingestion',
        'maintenance',
        'default',
      ]),
    [queueSnapshot]
  );

  const flowSteps = [
    {
      title: 'Connect credentials',
      description: 'Link Spotify or paste API keys to unlock imports/exports.',
    },
    {
      title: 'Configure webhooks',
      description: 'Generate Arr webhooks to send new downloads into Tastebuds.',
    },
    {
      title: 'Trigger syncs',
      description: 'Kick off Jellyfin/Plex syncs or Spotify exports when ready.',
    },
    {
      title: 'Monitor queue health',
      description: 'Watch ingestion + sync queues to confirm background work.',
    },
  ];

  if (loading) {
    return (
      <section className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
        <p className="text-sm text-slate-300">Loading integrations…</p>
      </section>
    );
  }

  return (
    <section className="space-y-6 rounded-2xl border border-slate-800 bg-slate-950/60 p-6 shadow-lg shadow-emerald-500/5">
      <header className="space-y-2">
        <p className="text-sm uppercase tracking-wide text-emerald-300">Connect & flow</p>
        <h1 className="text-2xl font-semibold text-white">
          Connect Spotify, Arr, Jellyfin, and Plex.
        </h1>
        <p className="text-sm text-slate-300">
          Link accounts, set up webhooks, and watch the queues that power background syncs.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-[1.1fr,0.9fr]">
        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <p className="text-xs uppercase tracking-wide text-emerald-200">Connect & flow steps</p>
          <ol className="mt-3 space-y-3 text-xs text-slate-300">
            {flowSteps.map((step, index) => (
              <li key={step.title} className="flex gap-3">
                <span className="flex h-6 w-6 items-center justify-center rounded-full border border-emerald-400/40 bg-emerald-500/10 text-[11px] font-semibold text-emerald-100">
                  {index + 1}
                </span>
                <div>
                  <p className="text-sm font-semibold text-white">{step.title}</p>
                  <p className="text-xs text-slate-300">{step.description}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-emerald-200">Queue health</p>
              <p className="text-xs text-slate-300">
                {queueLoading
                  ? 'Checking background workers...'
                  : queueError
                    ? normalizeQueueError(queueError)
                    : `Status: ${queueSnapshot?.status ?? 'unknown'}`}
              </p>
            </div>
            <button
              type="button"
              onClick={refreshQueueHealth}
              className="rounded-lg border border-slate-700 px-3 py-1 text-[11px] font-semibold text-white transition hover:border-emerald-400/60"
            >
              Refresh
            </button>
          </div>
          {queueSnapshot?.checked_at && (
            <p className="mt-2 text-[11px] text-slate-400">
              Checked {formatTimestamp(queueSnapshot.checked_at)}
            </p>
          )}
          {queueStats.length > 0 ? (
            <div className="mt-3 grid gap-2 text-[11px] text-slate-300 sm:grid-cols-2">
              {queueStats.map((queue) => (
                <div
                  key={queue.name}
                  className="rounded-lg border border-slate-800 bg-slate-950/70 p-2"
                >
                  <p className="text-xs font-semibold text-white">{queue.name}</p>
                  <p className="text-[11px] text-slate-400">
                    {queue.size} queued · {queue.failed} failed · {queue.scheduled} scheduled
                  </p>
                </div>
              ))}
            </div>
          ) : null}
          {queueSnapshot?.warnings?.length ? (
            <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-amber-100">
              {queueSnapshot.warnings.map((warning) => (
                <span
                  key={warning}
                  className="rounded-full border border-amber-400/40 bg-amber-500/10 px-3 py-1"
                >
                  {warning.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          ) : null}
        </section>
      </div>

      {error ? (
        <p className="rounded-lg border border-rose-500/40 bg-rose-500/10 p-3 text-sm">{error}</p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {integrations.map((integration) => (
          <div
            key={integration.provider}
            className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/60 p-4"
          >
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-white">{integration.display_name}</h2>
                <p className="text-xs uppercase tracking-wide text-slate-400">
                  {integration.status} · {integration.auth_type}
                </p>
              </div>
              {integration.connected ? (
                <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-semibold text-emerald-200">
                  Connected
                </span>
              ) : (
                <span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold text-slate-300">
                  Not linked
                </span>
              )}
            </div>

            {integration.last_error ? (
              <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-2 text-xs text-amber-200">
                {integration.last_error}
              </p>
            ) : null}

            <div className="grid gap-2 text-xs text-slate-300 sm:grid-cols-2">
              <StatusLine
                label="Connection"
                value={integration.connected ? 'Linked' : 'Not linked'}
              />
              <StatusLine
                label="Token"
                value={
                  integration.expires_at
                    ? `Expires ${formatTimestamp(integration.expires_at)}`
                    : 'No expiry'
                }
              />
              <StatusLine
                label="Last rotation"
                value={
                  integration.rotated_at ? formatTimestamp(integration.rotated_at) : 'Not rotated'
                }
              />
              {(() => {
                const lastTriggeredAt = syncState[integration.provider]?.lastTriggeredAt;
                if (!lastTriggeredAt) return null;
                return (
                  <StatusLine
                    label="Last sync"
                    value={formatTimestamp(lastTriggeredAt)}
                    tone={syncState[integration.provider]?.status === 'error' ? 'error' : 'default'}
                  />
                );
              })()}
              {(() => {
                const message = syncState[integration.provider]?.message;
                if (!message) return null;
                return <StatusLine label="Sync status" value={message} />;
              })()}
            </div>

            {integration.provider === 'spotify' ? (
              <div className="flex flex-wrap gap-2">
                {!integration.connected ? (
                  <button
                    type="button"
                    onClick={handleOAuthConnect}
                    className="rounded-lg bg-emerald-500 px-3 py-2 text-xs font-semibold text-slate-950 transition hover:bg-emerald-400"
                  >
                    Connect Spotify
                  </button>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => handleRotate('spotify')}
                      className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-white transition hover:border-emerald-400/60"
                    >
                      Refresh token
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDisconnect('spotify')}
                      className="rounded-lg border border-rose-500/50 px-3 py-2 text-xs font-semibold text-rose-200 transition hover:border-rose-400"
                    >
                      Disconnect
                    </button>
                  </>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                <div className="grid gap-3 md:grid-cols-2">
                  {(providerFields[integration.provider]?.fields || []).map((field) => (
                    <label key={field.name} className="space-y-1 text-xs text-slate-300">
                      <span>{field.label}</span>
                      <input
                        type={field.type}
                        placeholder={field.placeholder}
                        value={formState[integration.provider]?.[field.name] || ''}
                        onChange={(event) =>
                          setFormState((prev) => ({
                            ...prev,
                            [integration.provider]: {
                              ...(prev[integration.provider] || {}),
                              [field.name]: event.target.value,
                            },
                          }))
                        }
                        className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white"
                      />
                    </label>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => handleCredentialsSave(integration.provider)}
                    className="rounded-lg bg-emerald-500 px-3 py-2 text-xs font-semibold text-slate-950 transition hover:bg-emerald-400"
                  >
                    Save credentials
                  </button>
                  {integration.connected ? (
                    <button
                      type="button"
                      onClick={() => handleDisconnect(integration.provider)}
                      className="rounded-lg border border-rose-500/50 px-3 py-2 text-xs font-semibold text-rose-200 transition hover:border-rose-400"
                    >
                      Disconnect
                    </button>
                  ) : null}
                  {integration.capabilities?.supports_sync ? (
                    <button
                      type="button"
                      onClick={() => handleSync(integration.provider)}
                      className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-white transition hover:border-emerald-400/60"
                    >
                      Trigger sync
                    </button>
                  ) : null}
                </div>
              </div>
            )}

            {integration.provider === 'arr' ? (
              <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-xs text-slate-300">
                <p className="text-xs uppercase tracking-wide text-slate-400">Webhook</p>
                <p className="mt-2">
                  Token prefix:{' '}
                  <span className="font-semibold text-emerald-200">
                    {webhookPrefix || integration.webhook_token_prefix || 'Not generated'}
                  </span>
                </p>
                {webhookUrl ? (
                  <p className="mt-2 break-all text-emerald-200">{webhookUrl}</p>
                ) : (
                  <button
                    type="button"
                    onClick={handleWebhookToken}
                    className="mt-2 rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-white transition hover:border-emerald-400/60"
                  >
                    Generate webhook URL
                  </button>
                )}
              </div>
            ) : null}
          </div>
        ))}
      </div>

      <section className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Arr ingest queue</h2>
            <p className="text-xs text-slate-400">Incoming webhook events ready to ingest.</p>
          </div>
          <button
            type="button"
            onClick={refreshArrQueue}
            className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-white transition hover:border-emerald-400/60"
          >
            Refresh
          </button>
        </div>
        {arrQueue.length === 0 ? (
          <p className="text-xs text-slate-400">No pending events.</p>
        ) : (
          <div className="space-y-2">
            {arrQueue.map((event) => (
              <div
                key={event.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-2"
              >
                <div>
                  <p className="text-xs font-semibold text-white">
                    {event.title || 'Untitled item'}
                  </p>
                  <p className="text-[11px] text-slate-400">
                    {event.event_type || 'event'} · {event.source_name || 'unknown source'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleArrIngest(event.id)}
                  className="rounded-lg bg-emerald-500 px-3 py-2 text-xs font-semibold text-slate-950 transition hover:bg-emerald-400"
                >
                  Ingest
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}

function StatusLine({
  label,
  value,
  tone = 'default',
}: {
  label: string;
  value: string;
  tone?: 'default' | 'error';
}) {
  const valueClass = tone === 'error' ? 'text-amber-200' : 'text-white';
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-2">
      <p className="text-[10px] uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`text-xs font-semibold ${valueClass}`}>{value}</p>
    </div>
  );
}

function formatTimestamp(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function normalizeQueueError(message: string) {
  const normalized = message.toLowerCase();
  if (normalized.includes('unauthorized') || normalized.includes('token')) {
    return 'Sign in to view queue health.';
  }
  return message;
}
