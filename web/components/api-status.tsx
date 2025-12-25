'use client';

import { useEffect, useState } from 'react';
import { fetchHealth, normalizeConnectorHealth, ConnectorHealth } from '../lib/health';

export function ApiStatus() {
  const [status, setStatus] = useState<'idle' | 'ok' | 'error'>('idle');
  const [message, setMessage] = useState<string>('Checking backend health...');
  const [connectors, setConnectors] = useState<ConnectorHealth[]>([]);
  const [connectorWarning, setConnectorWarning] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetchHealth()
      .then((res) => {
        if (cancelled) return;
        setStatus('ok');
        setMessage(
          `API reachable at ${process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000/api'}`
        );
        const normalized = normalizeConnectorHealth(res);
        setConnectors(normalized);
        if (normalized.some((item) => item.state !== 'ok')) {
          setConnectorWarning('One or more connectors are degraded—see details below.');
        }
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setStatus('error');
        setMessage(err.message);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const color =
    status === 'ok' ? 'text-emerald-300' : status === 'error' ? 'text-red-300' : 'text-slate-200';
  const indicator = status === 'ok' ? '●' : status === 'error' ? '○' : '…';

  const badgeClass = (state: ConnectorHealth['state']) => {
    if (state === 'ok') return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200';
    if (state === 'circuit_open') return 'border-amber-400/50 bg-amber-500/10 text-amber-100';
    return 'border-red-500/50 bg-red-500/10 text-red-100';
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
      <p className={`flex items-center gap-2 text-sm font-semibold ${color}`}>
        <span>{indicator}</span>
        API health
      </p>
      <p className="mt-2 text-sm text-slate-200">{message}</p>
      {connectorWarning && <p className="mt-1 text-xs text-amber-200">{connectorWarning}</p>}
      {connectors.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
          {connectors.map((connector) => (
            <span
              key={connector.source}
              className={`rounded-full border px-3 py-1 ${badgeClass(connector.state)}`}
              title={
                connector.last_error
                  ? `Last error: ${connector.last_error}`
                  : connector.remaining_cooldown
                    ? `Cooling down for ${connector.remaining_cooldown.toFixed(1)}s`
                    : 'Healthy'
              }
            >
              {connector.source}: {connector.state}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
