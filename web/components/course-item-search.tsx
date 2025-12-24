'use client';

import { FormEvent, useEffect, useMemo, useState, useId, useRef, ForwardedRef, forwardRef } from 'react';
import { Course, CourseItem, createCourseItem } from '../lib/menus';
import { MediaSearchItem, MediaType, searchMedia } from '../lib/search';

type CourseItemSearchProps = {
  menuId: string;
  course: Course;
  onAdded: (item: CourseItem) => void;
};

const mediaTypeOptions: { label: string; value: MediaType }[] = [
  { label: 'Books', value: 'book' },
  { label: 'Movies', value: 'movie' },
  { label: 'TV', value: 'tv' },
  { label: 'Games', value: 'game' },
  { label: 'Music', value: 'music' },
];

const promptSuggestions = [
  { label: 'Cozy sci-fi', value: 'cozy science fiction' },
  { label: 'Award winners', value: 'award winning novels 2023' },
  { label: 'Movie night', value: 'animated adventure family' },
  { label: 'New music', value: 'indie folk 2024' },
];

const RESULTS_PER_PAGE = 10;
const EXTERNAL_RESULTS_PER_SOURCE = 2;

export function CourseItemSearch({ menuId, course, onAdded }: CourseItemSearchProps) {
  const [query, setQuery] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<MediaType[]>([]);
  const [includeExternal, setIncludeExternal] = useState(true);
  const [results, setResults] = useState<MediaSearchItem[]>([]);
  const [metadata, setMetadata] = useState<Record<string, unknown> | null>(null);
  const [source, setSource] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMoreInternal, setHasMoreInternal] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [position, setPosition] = useState(course.items.length + 1);
  const [notes, setNotes] = useState('');
  const [addingId, setAddingId] = useState<string | null>(null);
  const queryHelpId = useId();
  const resultsHeadingId = useId();
  const statusRegionId = useId();
  const resultsListId = useId();
  const metadataRegionId = useId();
  const errorCardRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setPosition(course.items.length + 1);
  }, [course.items.length]);

  useEffect(() => {
    if (error && errorCardRef.current) {
      errorCardRef.current.focus();
    }
  }, [error]);

  const metadataEntries = useMemo(() => {
    if (!metadata) return [];
    return Object.entries(metadata).map(([key, value]) => {
      if (
        typeof value === 'string' ||
        typeof value === 'number' ||
        typeof value === 'boolean' ||
        value === null
      ) {
        return [key, String(value)] as [string, string];
      }
      return [key, JSON.stringify(value)] as [string, string];
    });
  }, [metadata]);

  const resultSummary = useMemo(() => {
    if (searching) {
      return 'Searching...';
    }
    if (!hasSearched) {
      return 'Use the search form to browse your catalog or ingest new matches.';
    }
    if (results.length === 0) {
      return 'No matches yet. Try another query or toggle external sources.';
    }
    const paging = metadata?.paging as { page?: number } | undefined;
    const pageNumber = paging?.page ?? currentPage;
    const pageSuffix = pageNumber && pageNumber > 1 ? ` (page ${pageNumber})` : '';
    return `Showing ${results.length} item${results.length === 1 ? '' : 's'}${pageSuffix} (${
      source ?? 'internal'
    })`;
  }, [currentPage, hasSearched, metadata, results.length, searching, source]);

  const toggleType = (value: MediaType) => {
    setSelectedTypes((prev) =>
      prev.includes(value) ? prev.filter((type) => type !== value) : [...prev, value]
    );
  };

  const applyPrompt = (value: string) => {
    setQuery(value);
    setHasSearched(false);
  };

  async function performSearch(pageToLoad: number, append = false) {
    if (!query.trim()) {
      setError('Enter a search query (at least 2 characters).');
      return;
    }
    if (append) {
      if (loadingMore || searching) {
        return;
      }
      setLoadingMore(true);
    } else {
      if (searching) {
        return;
      }
      setSearching(true);
    }
    if (!append) {
      setHasSearched(true);
    }
    setError(null);
    setStatusMessage(null);
    try {
      const response = await searchMedia({
        query,
        includeExternal,
        types: selectedTypes.length ? selectedTypes : undefined,
        page: pageToLoad,
        perPage: RESULTS_PER_PAGE,
        externalPerSource: EXTERNAL_RESULTS_PER_SOURCE,
      });
      setMetadata(response.metadata ?? null);
      setSource(response.source);
      setResults((prev) => {
        if (!append) {
          return response.results;
        }
        const seen = new Set(prev.map((item) => item.id));
        const additions = response.results.filter((item) => !seen.has(item.id));
        return [...prev, ...additions];
      });
      const paging = response.metadata?.paging as
        | {
            page?: number;
            per_page?: number;
            total_internal?: number;
          }
        | undefined;
      const pageNumber = paging?.page ?? pageToLoad;
      const perPageValue = paging?.per_page ?? RESULTS_PER_PAGE;
      const totalInternal = typeof paging?.total_internal === 'number' ? paging.total_internal : 0;
      setCurrentPage(pageNumber);
      setHasMoreInternal(pageNumber * perPageValue < totalInternal);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Search failed.';
      setError(message);
      if (!append) {
        setResults([]);
        setMetadata(null);
        setSource(null);
        setHasMoreInternal(false);
      }
    } finally {
      if (append) {
        setLoadingMore(false);
      } else {
        setSearching(false);
      }
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await performSearch(1);
  }

  async function handleLoadMore() {
    if (loadingMore || searching) {
      return;
    }
    await performSearch(currentPage + 1, true);
  }

  async function handleAdd(item: MediaSearchItem) {
    if (addingId) return;
    setAddingId(item.id);
    setError(null);
    setStatusMessage(null);
    try {
      const created = await createCourseItem(menuId, course.id, {
        media_item_id: item.id,
        position,
        notes: notes || undefined,
      });
      onAdded(created);
      setStatusMessage(`Added "${item.title}" to ${course.title}.`);
      setNotes('');
      setPosition((prev) => prev + 1);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to add item.';
      setError(message);
    } finally {
      setAddingId(null);
    }
  }

  return (
    <section className="space-y-4 rounded-lg border border-dashed border-slate-800 bg-slate-950/30 p-4">
      <header className="space-y-1">
        <p className="text-sm font-semibold text-slate-200">Search catalog & ingest</p>
        <p id={queryHelpId} className="text-xs text-slate-400">
          Look up existing media and optionally fan out to Google Books, TMDB, IGDB, and Last.fm.
          New external matches are ingested automatically.
        </p>
      </header>

      <form
        onSubmit={handleSearch}
        className="space-y-3 rounded-lg border border-slate-800 bg-slate-950/60 p-3"
      >
        <div className="flex flex-col gap-2 md:flex-row">
          <input
            type="text"
            minLength={2}
            required
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search title, artist, or keyword"
            aria-describedby={queryHelpId}
            className="flex-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
          />
          <button
            type="submit"
            disabled={searching}
            aria-controls={resultsListId}
            className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {searching ? 'Searching…' : 'Search'}
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          {mediaTypeOptions.map((option) => {
            const active = selectedTypes.includes(option.value);
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => toggleType(option.value)}
                className={`rounded-full border px-3 py-1 text-xs font-semibold transition ${
                  active
                    ? 'border-emerald-500/60 bg-emerald-500/10 text-emerald-200'
                    : 'border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700'
                }`}
              >
                {option.label}
              </button>
            );
          })}
          <label className="ml-auto flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-slate-300">
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
              className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1 text-[11px] font-semibold text-slate-200 transition hover:border-emerald-400/60 hover:text-emerald-100"
            >
              {prompt.label}
            </button>
          ))}
        </div>
      </form>

      <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1">
            <label className="text-xs uppercase tracking-wide text-slate-400">Next position</label>
            <input
              type="number"
              min={1}
              value={position}
              onChange={(event) => setPosition(Number(event.target.value))}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs uppercase tracking-wide text-slate-400">
              Notes (optional)
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Serving notes for this course item."
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
            />
          </div>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          When you add an item from the results below it will use this position and notes.
        </p>
      </div>

      <div
        className="space-y-2"
        role="region"
        aria-labelledby={`${resultsHeadingId} ${statusRegionId}`}
        aria-busy={searching || loadingMore}
      >
        <p id={resultsHeadingId} className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Results
        </p>
        <p id={statusRegionId} className="text-xs text-slate-400" role="status" aria-live="polite">
          {resultSummary}
        </p>
        {searching && !loadingMore && (
          <DrawerStateCard
            tone="info"
            title="Searching catalog & connectors…"
            description="Pulling internal matches, then fanning out to Google Books, TMDB, IGDB, and Last.fm."
            role="status"
            ariaLive="polite"
            showSpinner
          />
        )}
        {!hasSearched && !searching && (
          <DrawerStateCard
            role="status"
            ariaLive="polite"
            title="Nothing queued yet"
            description="Enter a query to browse your catalog. Toggle on external sources to fan out to Google Books, TMDB, IGDB, and Last.fm."
          />
        )}
        {hasSearched && !searching && results.length === 0 && !error && (
          <DrawerStateCard
            role="status"
            ariaLive="polite"
            title="No matches yet"
            description="Try expanding your filters, tweak the query, or include external sources to ingest new media."
          />
        )}
        {metadataEntries.length > 0 && (
          <dl
            id={metadataRegionId}
            className="grid gap-2 rounded-lg border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-300 sm:grid-cols-2"
            aria-live="polite"
            aria-label="Search metrics"
          >
            {metadataEntries.map(([key, value]) => (
              <div key={key}>
                <dt className="uppercase tracking-wide text-slate-500">{key}</dt>
                <dd className="font-semibold text-white">{value}</dd>
              </div>
            ))}
          </dl>
        )}
        {error && (
          <DrawerStateCard
            tone="error"
            title="Search failed"
            description={error}
            actionLabel="Try again"
            onAction={() => {
              setError(null);
              setResults([]);
              setHasSearched(false);
              setMetadata(null);
              setSource(null);
              setHasMoreInternal(false);
            }}
            role="alert"
            ariaLive="assertive"
            ref={errorCardRef}
          />
        )}
        {statusMessage && (
          <p className="text-xs text-emerald-300" role="status" aria-live="polite">
            {statusMessage}
          </p>
        )}
      </div>

      {results.length > 0 && (
        <ul className="space-y-3" id={resultsListId} aria-live="polite" aria-label="Search results">
          {results.map((item) => (
            <li key={item.id} className="rounded-lg border border-slate-800 bg-slate-950/80 p-4">
              <div className="flex flex-col gap-3 sm:flex-row">
                <div className="flex items-start gap-3">
                  <div className="h-20 w-14 overflow-hidden rounded border border-slate-800 bg-slate-900/50">
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
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-400">
                      {item.media_type}
                    </p>
                    <p className="text-sm font-semibold text-white">{item.title}</p>
                    {item.subtitle && <p className="text-xs text-slate-300">{item.subtitle}</p>}
                    {item.release_date && (
                      <p className="text-xs text-slate-400">Released {item.release_date}</p>
                    )}
                    {item.description && (
                      <p className="mt-2 text-xs leading-relaxed text-slate-300">
                        {item.description}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex flex-col gap-2 sm:items-end sm:text-right">
                  <button
                    onClick={() => handleAdd(item)}
                    disabled={Boolean(addingId)}
                    className="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {addingId === item.id ? 'Adding…' : 'Add to course'}
                  </button>
                  {item.canonical_url && (
                    <a
                      href={item.canonical_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-emerald-300 underline decoration-emerald-300/60"
                    >
                      View source
                    </a>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
      {hasMoreInternal && (
        <div className="flex justify-center">
          <button
            type="button"
            onClick={handleLoadMore}
            disabled={loadingMore || searching}
            aria-controls={resultsListId}
            className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-2 text-xs font-semibold text-white transition hover:border-slate-600 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loadingMore ? 'Loading…' : 'Load more results'}
          </button>
        </div>
      )}
    </section>
  );
}

type DrawerStateCardProps = {
  title: string;
  description: string;
  tone?: 'default' | 'error' | 'info';
  actionLabel?: string;
  onAction?: () => void;
  role?: 'status' | 'alert';
  ariaLive?: 'polite' | 'assertive';
  showSpinner?: boolean;
};

const DrawerStateCard = forwardRef<HTMLDivElement, DrawerStateCardProps>(function DrawerStateCard(
  { title, description, tone = 'default', actionLabel, onAction, role, ariaLive, showSpinner },
  ref: ForwardedRef<HTMLDivElement>
) {
  const toneClasses: Record<string, string> = {
    default: 'border-slate-800 bg-slate-950/60 text-slate-200',
    error: 'border-red-500/40 bg-red-500/5 text-red-200',
    info: 'border-emerald-500/60 bg-emerald-500/10 text-emerald-100',
  };
  const resolvedClass = toneClasses[tone] ?? toneClasses.default;
  return (
    <div
      ref={ref}
      className={`rounded-lg border p-4 text-xs ${resolvedClass}`}
      role={role}
      aria-live={ariaLive}
      tabIndex={role === 'alert' ? -1 : undefined}
    >
      <p className="flex items-center gap-2 font-semibold">
        {showSpinner && (
          <span
            aria-hidden="true"
            className="inline-flex h-3 w-3 animate-spin rounded-full border border-white/40 border-t-transparent"
          />
        )}
        {title}
      </p>
      <p className="mt-1 text-[11px] text-white/70">{description}</p>
      {actionLabel && (
        <button
          type="button"
          onClick={onAction}
          className="mt-2 rounded-full border border-white/20 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-white/80"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
});
