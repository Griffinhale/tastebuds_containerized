'use client';

// Search explorer for the search workspace.

import Link from 'next/link';
import { FormEvent, useMemo, useState } from 'react';

import { ingestMedia } from '../lib/media';
import { upsertState } from '../lib/library';
import { MediaSearchItem, MediaType, formatSearchSource, searchMedia } from '../lib/search';

const typeOptions: { label: string; value: MediaType }[] = [
  { label: 'Books', value: 'book' },
  { label: 'Movies', value: 'movie' },
  { label: 'TV', value: 'tv' },
  { label: 'Games', value: 'game' },
  { label: 'Music', value: 'music' },
];

const EXTERNAL_RESULTS_PER_SOURCE = 4;

// Keyword/prompt chips are intentionally omitted until the search API supports reliable keyword filters
// (e.g., add a `keywords` array to the search payload and map chip selections to that field).

type SearchResultItem = MediaSearchItem & {
  resolved_media_id?: string;
};

type SortOption = 'title-asc' | 'title-desc' | 'release-desc' | 'release-asc' | 'search';

const sortOptions: { label: string; value: SortOption }[] = [
  { label: 'Title (A-Z)', value: 'title-asc' },
  { label: 'Title (Z-A)', value: 'title-desc' },
  { label: 'Release date (newest)', value: 'release-desc' },
  { label: 'Release date (oldest)', value: 'release-asc' },
  { label: 'Search order', value: 'search' },
];

export function MediaSearchExplorer() {
  const [query, setQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedTypes, setSelectedTypes] = useState<MediaType[]>([]);
  const [includeExternal, setIncludeExternal] = useState(false);
  const [sortOrder, setSortOrder] = useState<SortOption>('title-asc');
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [metadata, setMetadata] = useState<Record<string, unknown> | null>(null);
  const [source, setSource] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [addingToLibraryId, setAddingToLibraryId] = useState<string | null>(null);
  const [libraryMessage, setLibraryMessage] = useState<string | null>(null);
  const [libraryError, setLibraryError] = useState<string | null>(null);

  const resultSummary = useMemo(() => {
    if (searching) return 'Searching...';
    if (!hasSearched)
      return 'Use the query box to explore your catalog. Toggle external sources as needed.';
    if (results.length === 0) return 'No matches yet. Try a different phrase or toggle sources.';
    const paging = metadata?.paging as { page?: number } | undefined;
    const pageNumber = paging?.page ?? 1;
    const suffix = pageNumber > 1 ? ` (page ${pageNumber})` : '';
    const sourceLabel = formatSearchSource(source ?? 'internal');
    return `Showing ${results.length} item${results.length === 1 ? '' : 's'}${suffix} (${sourceLabel})`;
  }, [metadata, results.length, searching, hasSearched, source]);

  const metadataEntries = useMemo(() => {
    if (!metadata?.counts) return [] as [string, string][];
    return Object.entries(metadata.counts).map(([key, value]) => [key, String(value)]);
  }, [metadata]);

  const sortedResults = useMemo(() => {
    if (sortOrder === 'search') {
      return results;
    }
    const items = [...results];
    const titleCompare = (left: SearchResultItem, right: SearchResultItem) =>
      left.title.localeCompare(right.title, undefined, { sensitivity: 'base' });
    const releaseTimestamp = (value?: string | null) => {
      if (!value) return null;
      const parsed = new Date(value);
      return Number.isNaN(parsed.getTime()) ? null : parsed.getTime();
    };
    if (sortOrder === 'title-asc') {
      items.sort(titleCompare);
      return items;
    }
    if (sortOrder === 'title-desc') {
      items.sort((left, right) => titleCompare(right, left));
      return items;
    }
    const descending = sortOrder === 'release-desc';
    items.sort((left, right) => {
      const leftTime = releaseTimestamp(left.release_date);
      const rightTime = releaseTimestamp(right.release_date);
      if (leftTime === null && rightTime === null) {
        return titleCompare(left, right);
      }
      if (leftTime === null) return 1;
      if (rightTime === null) return -1;
      if (leftTime === rightTime) {
        return titleCompare(left, right);
      }
      return descending ? rightTime - leftTime : leftTime - rightTime;
    });
    return items;
  }, [results, sortOrder]);

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
    setLibraryError(null);
    setLibraryMessage(null);
    setHasSearched(true);
    try {
      const response = await searchMedia({
        query,
        includeExternal,
        types: selectedTypes.length ? selectedTypes : undefined,
        perPage: 9,
        externalPerSource: EXTERNAL_RESULTS_PER_SOURCE,
      });
      const normalized = response.results.map((item) => ({
        ...item,
        resolved_media_id: item.preview_id ? undefined : item.id,
      }));
      setResults(normalized);
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

  async function handleAddToLibrary(item: SearchResultItem) {
    if (addingToLibraryId || item.in_collection) return;
    setAddingToLibraryId(item.id);
    setLibraryError(null);
    setLibraryMessage(null);
    try {
      let resolvedMediaId = item.resolved_media_id ?? (item.preview_id ? undefined : item.id);
      if (!resolvedMediaId) {
        if (!item.source_name || !item.source_id) {
          throw new Error('Missing source details for ingestion.');
        }
        const ingestResponse = await ingestMedia(item.source_name, {
          external_id: item.source_id,
        });
        resolvedMediaId = ingestResponse.media_item.id;
      }
      await upsertState(resolvedMediaId, { status: 'want_to_consume', favorite: false });
      setResults((prev) =>
        prev.map((entry) =>
          entry.id === item.id
            ? { ...entry, in_collection: true, resolved_media_id: resolvedMediaId }
            : entry
        )
      );
      setLibraryMessage(`Added "${item.title}" to your library.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to add to library.';
      setLibraryError(message);
    } finally {
      setAddingToLibraryId(null);
    }
  }

  return (
    <section className="space-y-6 rounded-2xl border border-emerald-500/20 bg-gradient-to-br from-slate-950/80 via-slate-900/60 to-emerald-900/30 p-6 shadow-xl shadow-emerald-500/10">
      <header>
        <h1 className="text-2xl font-semibold text-white">Search workspace</h1>
      </header>

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
              className="flex-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2.5 text-base text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
            />
            <div className="flex flex-wrap gap-2">
              <button
                type="submit"
                disabled={searching}
                className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {searching ? 'Searching…' : 'Run search'}
              </button>
              <button
                type="button"
                onClick={() => setShowFilters((current) => !current)}
                aria-pressed={showFilters}
                className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-white/80 transition hover:border-white/30 hover:text-white"
              >
                {showFilters ? 'Hide filters' : 'Show filters'}
              </button>
            </div>
          </div>
        </div>

        {showFilters && (
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
        )}
      </form>

      <div className="space-y-3">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-white">Results</p>
            <p className="text-xs text-slate-300">{resultSummary}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
            <label className="flex items-center gap-2">
              <span className="uppercase tracking-wide text-slate-400">Sort</span>
              <select
                value={sortOrder}
                onChange={(event) => setSortOrder(event.target.value as SortOption)}
                className="rounded-md border border-white/10 bg-slate-950 px-2 py-1 text-xs text-white"
              >
                {sortOptions.map((option) => (
                  <option key={option.value} value={option.value} className="bg-slate-950">
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            {metadataEntries.length > 0 &&
              metadataEntries.slice(0, 3).map(([key, value]) => (
                <span
                  key={key}
                  className="rounded-full border border-white/10 bg-white/5 px-3 py-1"
                >
                  {key}: {value}
                </span>
              ))}
          </div>
        </div>

        {error && <StateCard tone="error" title="Search failed" description={error} />}
        {libraryError && (
          <StateCard tone="error" title="Unable to add to library" description={libraryError} />
        )}
        {libraryMessage && (
          <StateCard tone="success" title="Added to library" description={libraryMessage} />
        )}
        {!error && !hasSearched && (
          <StateCard
            title="No query yet"
            description="Start typing above to preview matches from your catalog. Toggle external sources to expand."
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
            {sortedResults.map((item) => (
              <MediaResultCard
                key={item.id}
                item={item}
                adding={addingToLibraryId === item.id}
                onAdd={handleAddToLibrary}
                detailsHref={
                  item.resolved_media_id
                    ? `/media/${item.resolved_media_id}`
                    : item.preview_id
                      ? `/previews/${item.preview_id}`
                      : null
                }
              />
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function MediaResultCard({
  item,
  onAdd,
  adding,
  detailsHref,
}: {
  item: SearchResultItem;
  onAdd: (item: SearchResultItem) => void;
  adding: boolean;
  detailsHref: string | null;
}) {
  const addLabel = item.in_collection ? 'In library' : adding ? 'Adding...' : 'Add to library';
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
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[11px] uppercase tracking-wide text-emerald-200">
              {item.media_type}
            </p>
            {item.in_collection && (
              <span className="rounded-full border border-emerald-400/50 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-100">
                In library
              </span>
            )}
          </div>
          <p className="text-sm font-semibold text-white">{item.title}</p>
          {item.subtitle && <p className="text-xs text-slate-300">{item.subtitle}</p>}
          {item.release_date && (
            <p className="text-[11px] text-slate-400">Released {item.release_date}</p>
          )}
          {item.availability_summary && <AvailabilityBadge summary={item.availability_summary} />}
        </div>
      </div>
      {item.description && (
        <p className="mt-2 max-h-24 overflow-hidden text-xs leading-relaxed text-slate-300">
          {item.description}
        </p>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px]">
        <button
          type="button"
          onClick={() => onAdd(item)}
          disabled={item.in_collection || adding}
          className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 font-semibold text-emerald-100 transition hover:border-emerald-400 disabled:cursor-not-allowed disabled:opacity-70"
        >
          {addLabel}
        </button>
        {detailsHref && (
          <Link
            href={detailsHref}
            className="font-semibold text-emerald-200 underline decoration-emerald-200/60"
          >
            View details
          </Link>
        )}
        {item.canonical_url && (
          <a
            href={item.canonical_url}
            target="_blank"
            rel="noreferrer"
            className="font-semibold text-slate-300 underline decoration-slate-500/60"
          >
            View source
          </a>
        )}
      </div>
    </li>
  );
}

function AvailabilityBadge({
  summary,
}: {
  summary: NonNullable<MediaSearchItem['availability_summary']>;
}) {
  const providers = summary.providers ?? [];
  const availableCount = summary.status_counts?.available ?? 0;
  const providerLabel = providers.length
    ? providers.slice(0, 2).join(', ') + (providers.length > 2 ? ` +${providers.length - 2}` : '')
    : 'Unknown providers';
  const statusLabel = availableCount > 0 ? `${availableCount} available` : 'Availability unknown';
  return (
    <div className="flex flex-wrap items-center gap-2 text-[11px] text-emerald-100">
      <span className="rounded-full border border-emerald-400/40 bg-emerald-500/10 px-2 py-0.5">
        {statusLabel}
      </span>
      <span className="text-slate-400">{providerLabel}</span>
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
  tone?: 'default' | 'error' | 'success';
}) {
  const toneClasses =
    tone === 'error'
      ? 'border-red-500/40 bg-red-500/10 text-red-100'
      : tone === 'success'
        ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-100'
        : 'border-white/10 bg-white/5 text-white/80';
  return (
    <div className={`rounded-xl border p-4 ${toneClasses}`}>
      <p className="text-sm font-semibold">{title}</p>
      <p className="mt-1 text-xs leading-relaxed">{description}</p>
    </div>
  );
}
