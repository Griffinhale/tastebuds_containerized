'use client';

import { FormEvent, useMemo, useState } from 'react';

import { MediaSearchItem, MediaType, searchMedia } from '../lib/search';
import { ConnectorHealth, fetchHealth, normalizeConnectorHealth } from '../lib/health';

const typeOptions: { label: string; value: MediaType }[] = [
  { label: 'Books', value: 'book' },
  { label: 'Movies', value: 'movie' },
  { label: 'TV', value: 'tv' },
  { label: 'Games', value: 'game' },
  { label: 'Music', value: 'music' },
];

const promptSuggestions = [
  { label: 'Cozy sci-fi dinner', value: 'space opera comfort watch' },
  { label: 'Award winners', value: '2023 award winning novels' },
  { label: 'Road trip playlist', value: 'indie folk summer' },
  { label: 'Family movie night', value: 'animated adventure' },
  { label: 'New to play', value: 'co-op puzzle games' },
];

export function MediaSearchExplorer() {
  const [query, setQuery] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<MediaType[]>([]);
  const [includeExternal, setIncludeExternal] = useState(true);
  const [results, setResults] = useState<MediaSearchItem[]>([]);
  const [metadata, setMetadata] = useState<Record<string, unknown> | null>(null);
  const [source, setSource] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectorHealth, setConnectorHealth] = useState<ConnectorHealth[]>([]);
  const [connectorMessage, setConnectorMessage] = useState<string | null>(null);

  const resultSummary = useMemo(() => {
    if (searching) return 'Searching...';
    if (!hasSearched) return 'Use the query box to explore your catalog or external feeds.';
    if (results.length === 0) return 'No matches yet. Try a different phrase or toggle sources.';
    const paging = metadata?.paging as { page?: number } | undefined;
    const pageNumber = paging?.page ?? 1;
    const suffix = pageNumber > 1 ? ` (page ${pageNumber})` : '';
    return `Showing ${results.length} item${results.length === 1 ? '' : 's'}${suffix} (${source ?? 'internal'})`;
  }, [metadata, results.length, searching, hasSearched, source]);

  const selectedTypeLabels = selectedTypes
    .map((value) => typeOptions.find((option) => option.value === value)?.label)
    .filter(Boolean) as string[];

  const metadataEntries = useMemo(() => {
    if (!metadata) return [] as [string, string][];
    return Object.entries(metadata).map(([key, value]) => [key, String(value)]);
  }, [metadata]);

  const connectorBadgeClass = (state: ConnectorHealth['state']) => {
    if (state === 'ok') return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200';
    if (state === 'circuit_open') return 'border-amber-400/40 bg-amber-500/10 text-amber-100';
    return 'border-red-500/50 bg-red-500/10 text-red-100';
  };

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then((payload) => {
        if (cancelled) return;
        const connectors = normalizeConnectorHealth(payload);
        setConnectorHealth(connectors);
        if (connectors.some((item) => item.state !== 'ok')) {
          setConnectorMessage('Connector issues detected—expect slower external fan-out.');
        } else if (connectors.length === 0) {
          setConnectorMessage('Sign in to view connector telemetry.');
        } else {
          setConnectorMessage(null);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setConnectorHealth([]);
        setConnectorMessage(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function toggleType(value: MediaType) {
    setSelectedTypes((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value]
    );
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (query.trim().length < 2) {
      setError('Enter a couple of characters to search.');
      return;
    }
    setSearching(true);
    setError(null);
    setHasSearched(true);
    try {
      const response = await searchMedia({
        query,
        includeExternal,
        types: selectedTypes.length ? selectedTypes : undefined,
        perPage: 9,
        externalPerSource: 2,
      });
      setResults(response.results);
      setMetadata(response.metadata ?? null);
      setSource(response.source);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Search failed.';
      setError(message);
      setResults([]);
      setMetadata(null);
      setSource(null);
    } finally {
      setSearching(false);
    }
  }

  function applyPrompt(value: string) {
    setQuery(value);
    setHasSearched(false);
  }

  return (
    <section className="space-y-6 rounded-2xl border border-emerald-500/20 bg-gradient-to-br from-slate-950/80 via-slate-900/60 to-emerald-900/30 p-6 shadow-xl shadow-emerald-500/10">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-wide text-emerald-200">Search workspace</p>
        <h2 className="text-2xl font-semibold text-white">Find media without leaving home.</h2>
        <p className="text-sm text-emerald-100/80">
          Use natural language to search by title, creator, or vibe. Toggle sources to pull from
          your catalog first and then fan out to external providers.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1.1fr,0.9fr]">
        <form
          onSubmit={handleSearch}
          className="space-y-4 rounded-xl border border-white/10 bg-slate-950/50 p-4"
        >
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-wide text-slate-400">Query</label>
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
              <input
                type="text"
                minLength={2}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search title, artist, or concept"
                className="flex-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
              />
              <button
                type="submit"
                disabled={searching}
                className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {searching ? 'Searching…' : 'Run search'}
              </button>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {typeOptions.map((option) => {
              const active = selectedTypes.includes(option.value);
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => toggleType(option.value)}
                  className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${
                    active
                      ? 'border-emerald-400/70 bg-emerald-500/10 text-emerald-200'
                      : 'border-white/10 bg-white/5 text-white/80 hover:border-white/30'
                  }`}
                >
                  {option.label}
                </button>
              );
            })}
            <label className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold text-white/80">
              <input
                type="checkbox"
                checked={includeExternal}
                onChange={(event) => setIncludeExternal(event.target.checked)}
                className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-emerald-400"
              />
              Include external
            </label>
          </div>

          <div className="flex flex-wrap gap-2">
            {promptSuggestions.map((prompt) => (
              <button
                key={prompt.value}
                type="button"
                onClick={() => applyPrompt(prompt.value)}
                className="rounded-lg border border-white/10 bg-white/5 px-3 py-1 text-[11px] font-semibold text-white/80 transition hover:border-emerald-300/60 hover:text-emerald-100"
              >
                {prompt.label}
              </button>
            ))}
          </div>
        </form>

        <div className="space-y-3 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-white/80">
          <p className="text-xs uppercase tracking-wide text-emerald-200">Search context</p>
          {connectorHealth.length > 0 && (
            <div className="flex flex-wrap gap-2 text-[11px]">
              {connectorHealth.map((connector) => (
                <span
                  key={connector.source}
                  className={`rounded-full border px-3 py-1 ${connectorBadgeClass(connector.state)}`}
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
          {connectorMessage && (
            <p className="text-[11px] text-amber-200" role="status" aria-live="polite">
              {connectorMessage}
            </p>
          )}
          <ContextLine label="Source" value={source ? source : 'Internal first'} />
          <ContextLine
            label="Types"
            value={selectedTypeLabels.length ? selectedTypeLabels.join(', ') : 'Any media type'}
          />
          <ContextLine
            label="External fanout"
            value={includeExternal ? 'Enabled' : 'Internal only'}
            tone={includeExternal ? 'accent' : 'muted'}
          />
          <div className="rounded-lg border border-white/10 bg-slate-950/60 p-3 text-xs text-slate-300">
            <p className="font-semibold text-white">Tip</p>
            <p className="mt-1 leading-relaxed">
              You can paste natural language prompts. The backend will still match against metadata
              and title fields so you get sensible results without crafting boolean queries.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-white">Results</p>
            <p className="text-xs text-slate-300">{resultSummary}</p>
          </div>
          {metadataEntries.length > 0 && (
            <div className="flex flex-wrap gap-2 text-[11px] text-slate-300">
              {metadataEntries.slice(0, 3).map(([key, value]) => (
                <span
                  key={key}
                  className="rounded-full border border-white/10 bg-white/5 px-3 py-1"
                >
                  {key}: {value}
                </span>
              ))}
            </div>
          )}
        </div>

        {error && <StateCard tone="error" title="Search failed" description={error} />}
        {!error && !hasSearched && (
          <StateCard
            title="No query yet"
            description="Start typing above to preview matches from your catalog and external sources."
          />
        )}
        {!error && hasSearched && results.length === 0 && (
          <StateCard
            title="No matches"
            description="Try a shorter phrase or widen filters. External sources help fill gaps."
          />
        )}

        {results.length > 0 && (
          <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {results.map((item) => (
              <MediaResultCard key={item.id} item={item} />
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function MediaResultCard({ item }: { item: MediaSearchItem }) {
  return (
    <li className="rounded-xl border border-white/10 bg-slate-950/60 p-3">
      <div className="flex items-start gap-3">
        <div className="h-20 w-16 overflow-hidden rounded border border-white/10 bg-slate-900">
          {item.cover_image_url ? (
            <img
              src={item.cover_image_url}
              alt={item.title}
              className="h-full w-full object-cover"
              referrerPolicy="no-referrer"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-[10px] uppercase tracking-wide text-slate-500">
              No art
            </div>
          )}
        </div>
        <div className="space-y-1">
          <p className="text-[11px] uppercase tracking-wide text-emerald-200">{item.media_type}</p>
          <p className="text-sm font-semibold text-white">{item.title}</p>
          {item.subtitle && <p className="text-xs text-slate-300">{item.subtitle}</p>}
          {item.release_date && (
            <p className="text-[11px] text-slate-400">Released {item.release_date}</p>
          )}
        </div>
      </div>
      {item.description && (
        <p className="mt-2 max-h-24 overflow-hidden text-xs leading-relaxed text-slate-300">
          {item.description}
        </p>
      )}
      {item.canonical_url && (
        <a
          href={item.canonical_url}
          target="_blank"
          rel="noreferrer"
          className="mt-2 inline-flex text-[11px] font-semibold text-emerald-200 underline decoration-emerald-200/60"
        >
          View source
        </a>
      )}
    </li>
  );
}

function ContextLine({
  label,
  value,
  tone = 'default',
}: {
  label: string;
  value: string;
  tone?: 'default' | 'accent' | 'muted';
}) {
  const toneClass =
    tone === 'accent' ? 'text-emerald-200' : tone === 'muted' ? 'text-slate-400' : 'text-white';
  return (
    <div className="flex items-center justify-between rounded-lg border border-white/10 bg-slate-950/40 px-3 py-2 text-xs">
      <span className="uppercase tracking-wide text-slate-400">{label}</span>
      <span className={`font-semibold ${toneClass}`}>{value}</span>
    </div>
  );
}

function StateCard({
  title,
  description,
  tone = 'default',
}: {
  title: string;
  description: string;
  tone?: 'default' | 'error';
}) {
  const toneClasses =
    tone === 'error'
      ? 'border-red-500/40 bg-red-500/10 text-red-100'
      : 'border-white/10 bg-white/5 text-white/80';
  return (
    <div className={`rounded-xl border p-4 ${toneClasses}`}>
      <p className="text-sm font-semibold">{title}</p>
      <p className="mt-1 text-xs leading-relaxed">{description}</p>
    </div>
  );
}
