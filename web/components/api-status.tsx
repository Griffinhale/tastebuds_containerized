"use client";

import { useEffect, useState } from 'react';
import { apiFetch } from '../lib/api';

type HealthResponse = { status: string };

export function ApiStatus() {
  const [status, setStatus] = useState<'idle' | 'ok' | 'error'>('idle');
  const [message, setMessage] = useState<string>('Checking backend health...');

  useEffect(() => {
    let cancelled = false;

    apiFetch<HealthResponse>('/health', {}, { isServer: false })
      .then((res) => {
        if (cancelled) return;
        setStatus('ok');
        setMessage(`API reachable at ${process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000/api'}`);
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
  const indicator =
    status === 'ok' ? '●' : status === 'error' ? '○' : '…';

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
      <p className={`flex items-center gap-2 text-sm font-semibold ${color}`}>
        <span>{indicator}</span>
        API health
      </p>
      <p className="mt-2 text-sm text-slate-200">{message}</p>
    </div>
  );
}
