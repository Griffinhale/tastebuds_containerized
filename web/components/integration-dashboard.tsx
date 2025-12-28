// Integration management dashboard with provider status and actions.
'use client';

import { useCallback, useEffect, useState } from 'react';

import { apiFetch, ApiError } from '../lib/api';

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [webhookUrl, setWebhookUrl] = useState<string | null>(null);
  const [webhookPrefix, setWebhookPrefix] = useState<string | null>(null);
  const [formState, setFormState] = useState<Record<string, Record<string, string>>>({});

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

  useEffect(() => {
    void refreshIntegrations();
    void refreshArrQueue();
  }, [refreshIntegrations, refreshArrQueue]);

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
    try {
      await apiFetch(`/integrations/${provider}/sync`, {
        method: 'POST',
        body: JSON.stringify({ external_id: 'library', action: 'sync', force_refresh: false }),
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Unable to sync ${provider}.`);
    }
  };

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
        <p className="text-sm uppercase tracking-wide text-emerald-300">Integrations</p>
        <h1 className="text-2xl font-semibold text-white">
          Connect Spotify, Arr, Jellyfin, and Plex.
        </h1>
        <p className="text-sm text-slate-300">
          Manage OAuth linking, headless API keys, webhook endpoints, and sync triggers from one
          place.
        </p>
      </header>

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
