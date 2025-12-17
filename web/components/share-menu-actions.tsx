"use client";

import { useCallback, useState } from 'react';

type ShareMenuActionsProps = {
  title: string;
  shareUrl: string;
};

export function ShareMenuActions({ title, shareUrl }: ShareMenuActionsProps) {
  const [copied, setCopied] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const copyLink = useCallback(async () => {
    setError(null);
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(shareUrl);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = shareUrl;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to copy link.';
      setError(message);
    }
  }, [shareUrl]);

  const shareNative = useCallback(async () => {
    if (sharing) return;
    const canShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function';
    if (!canShare) {
      await copyLink();
      return;
    }
    setSharing(true);
    setError(null);
    try {
      await navigator.share({
        title: `${title} · Tastebuds`,
        url: shareUrl,
        text: `Browse the "${title}" menu on Tastebuds.`,
      });
    } catch (err) {
      // Users may cancel; only surface real errors
      if (err instanceof Error && err.name !== 'AbortError') {
        setError(err.message);
      }
    } finally {
      setSharing(false);
    }
  }, [sharing, shareUrl, title, copyLink]);

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-sm font-semibold text-white">Share this menu</p>
        <p className="text-xs text-slate-400">Copy or natively share the public link.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={shareNative}
          className="rounded-lg bg-white/90 px-4 py-2 text-xs font-semibold text-slate-900 transition hover:bg-white"
          disabled={sharing}
        >
          {sharing ? 'Sharing…' : 'Share menu'}
        </button>
        <button
          type="button"
          onClick={copyLink}
          className="rounded-lg border border-white/30 px-4 py-2 text-xs font-semibold text-white transition hover:border-white hover:text-emerald-200"
        >
          {copied ? 'Copied!' : 'Copy link'}
        </button>
      </div>
      {error && <p className="text-xs text-red-300">{error}</p>}
    </div>
  );
}
