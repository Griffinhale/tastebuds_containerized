'use client';

// Course item search with external fan-out and inline add-to-course actions.

import {
  FormEvent,
  useEffect,
  useMemo,
  useState,
  useId,
  useRef,
  ForwardedRef,
  forwardRef,
} from 'react';
import { ApiError } from '../lib/api';
import { ingestMedia } from '../lib/media';
import { Course, CourseItem, createCourseItem } from '../lib/menus';
import { MediaSearchItem, MediaType, formatSearchSource, searchMedia } from '../lib/search';

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

const RESULTS_PER_PAGE = 10;
const EXTERNAL_RESULTS_PER_SOURCE = 4;

type SortOption = 'title-asc' | 'title-desc' | 'release-desc' | 'release-asc' | 'search';

const sortOptions: { label: string; value: SortOption }[] = [
  { label: 'Title (A-Z)', value: 'title-asc' },
  { label: 'Title (Z-A)', value: 'title-desc' },
  { label: 'Release date (newest)', value: 'release-desc' },
  { label: 'Release date (oldest)', value: 'release-asc' },
  { label: 'Search order', value: 'search' },
];

export function CourseItemSearch({ menuId, course, onAdded }: CourseItemSearchProps) {
  const [query, setQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedTypes, setSelectedTypes] = useState<MediaType[]>([]);
  const [includeExternal, setIncludeExternal] = useState(false);
  const [sortOrder, setSortOrder] = useState<SortOption>('title-asc');
  const [results, setResults] = useState<MediaSearchItem[]>([]);
  const [metadata, setMetadata] = useState<Record<string, unknown> | null>(null);
  const [source, setSource] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMoreInternal, setHasMoreInternal] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<'external' | 'default' | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [position, setPosition] = useState(course.items.length + 1);
  const [notes, setNotes] = useState('');
  const [addingId, setAddingId] = useState<string | null>(null);
  const queryHelpId = useId();
  const resultsHeadingId = useId();
  const statusRegionId = useId();
  const resultsListId = useId();
  const errorCardRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setPosition(course.items.length + 1);
  }, [course.items.length]);

  useEffect(() => {
    if (error && errorCardRef.current) {
      errorCardRef.current.focus();
    }
  }, [error]);

  const sourceCounts = useMemo(() => {
    const counts = (metadata as { source_counts?: Record<string, number> } | null)?.source_counts;
    if (!counts) return [];
    return Object.entries(counts).map(([key, value]) => [key, value] as [string, number]);
  }, [metadata]);

  const dedupeEntries = useMemo<[string, number][]>(() => {
    const reasons = (metadata as { dedupe_reasons?: Record<string, number> } | null)
      ?.dedupe_reasons;
    if (!reasons) return [];
    return Object.entries(reasons).map(([key, value]) => [String(key), Number(value)]);
  }, [metadata]);

  const insightBadges = useMemo(() => {
    const badges: { key: string; label: string }[] = [];
    sourceCounts.slice(0, 2).forEach(([key, value]) => {
      badges.push({ key: `source-${key}`, label: `${formatSearchSource(key)}: ${value}` });
    });
    dedupeEntries.slice(0, 1).forEach(([key, value]) => {
      badges.push({ key: `dedupe-${key}`, label: `Dedupe ${key.replace(/_/g, ' ')}: ${value}` });
    });
    return badges;
  }, [dedupeEntries, sourceCounts]);

  const sortedResults = useMemo(() => {
    if (sortOrder === 'search') {
      return results;
    }
    const items = [...results];
    const titleCompare = (left: MediaSearchItem, right: MediaSearchItem) =>
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

  const resultSummary = useMemo(() => {
    if (searching) {
      return 'Searching...';
    }
    if (!hasSearched) {
      return 'Search to drop matches into this course.';
    }
    if (results.length === 0) {
      return 'No matches yet. Try another query or include external.';
    }
    const paging = metadata?.paging as { page?: number } | undefined;
    const pageNumber = paging?.page ?? currentPage;
    const pageSuffix = pageNumber && pageNumber > 1 ? ` (page ${pageNumber})` : '';
    const sourceLabel = formatSearchSource(source ?? 'internal');
    return `Showing ${results.length} item${results.length === 1 ? '' : 's'}${pageSuffix} (${sourceLabel})`;
  }, [currentPage, hasSearched, metadata, results.length, searching, source]);

  const toggleType = (value: MediaType) => {
    setSelectedTypes((prev) =>
      prev.includes(value) ? prev.filter((type) => type !== value) : [...prev, value]
    );
  };

  async function performSearch(
    pageToLoad: number,
    options: { append?: boolean; includeExternalOverride?: boolean } = {}
  ) {
    const append = options.append ?? false;
    const includeExternalValue = options.includeExternalOverride ?? includeExternal;
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
    if (options.includeExternalOverride !== undefined) {
      setIncludeExternal(includeExternalValue);
    }
    setError(null);
    setErrorKind(null);
    setStatusMessage(null);
    try {
      const response = await searchMedia({
        query,
        includeExternal: includeExternalValue,
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
        // Deduplicate by ID when appending additional pages.
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
      const apiError = err instanceof ApiError ? err : null;
      const isExternalBlocked =
        includeExternalValue && apiError ? [401, 403, 429].includes(apiError.status) : false;
      setErrorKind(isExternalBlocked ? 'external' : 'default');
      if (!append && !isExternalBlocked) {
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
    await performSearch(currentPage + 1, { append: true });
  }

  async function handleAdd(item: MediaSearchItem) {
    if (addingId) return;
    setAddingId(item.id);
    setError(null);
    setErrorKind(null);
    setStatusMessage(null);
    try {
      let mediaItemId = item.id;
      if (item.preview_id) {
        if (!item.source_name || !item.source_id) {
          throw new Error('Missing source details for ingestion.');
        }
        const ingested = await ingestMedia(item.source_name, { external_id: item.source_id });
        mediaItemId = ingested.media_item.id;
      }
      const created = await createCourseItem(menuId, course.id, {
        media_item_id: mediaItemId,
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
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-slate-200">Search catalog</p>
          <p id={queryHelpId} className="text-xs text-slate-400">
            Drop matches straight into {course.title}.
          </p>
        </div>
      </header>

      <form
        onSubmit={handleSearch}
        className="space-y-3 rounded-lg border border-slate-800 bg-slate-950/60 p-3"
      >
        <div className="space-y-2">
          <label className="text-xs uppercase tracking-wide text-slate-400">Query</label>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
            <input
              type="text"
              minLength={2}
              required
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search title, artist, or concept"
              aria-describedby={queryHelpId}
              className="flex-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
            />
            <div className="flex flex-wrap gap-2">
              <button
                type="submit"
                disabled={searching}
                aria-controls={resultsListId}
                className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {searching ? 'Searching…' : 'Search'}
              </button>
              <button
                type="button"
                onClick={() => setShowFilters((current) => !current)}
                aria-pressed={showFilters}
                className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-emerald-400/60 hover:text-emerald-100"
              >
                {showFilters ? 'Hide filters' : 'Filters'}
              </button>
            </div>
          </div>
        </div>

        {showFilters && (
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
        )}
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
              placeholder="Notes for this course item."
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
            />
          </div>
        </div>
        <p className="mt-2 text-xs text-slate-500">Applies to the next add.</p>
      </div>

      <div
        className="space-y-2"
        role="region"
        aria-labelledby={`${resultsHeadingId} ${statusRegionId}`}
        aria-busy={searching || loadingMore}
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p
            id={resultsHeadingId}
            className="text-xs font-semibold uppercase tracking-wide text-slate-400"
          >
            Results
          </p>
          <label className="flex items-center gap-2 text-[11px] text-slate-300">
            <span className="uppercase tracking-wide text-slate-500">Sort</span>
            <select
              value={sortOrder}
              onChange={(event) => setSortOrder(event.target.value as SortOption)}
              className="rounded-md border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-white"
            >
              {sortOptions.map((option) => (
                <option key={option.value} value={option.value} className="bg-slate-950">
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p id={statusRegionId} className="text-xs text-slate-400" role="status" aria-live="polite">
          {resultSummary}
        </p>
        {insightBadges.length > 0 && (
          <div className="flex flex-wrap gap-2 text-[11px] text-slate-300">
            {insightBadges.map((badge) => (
              <span key={badge.key} className="rounded-full border border-slate-800 px-3 py-1">
                {badge.label}
              </span>
            ))}
          </div>
        )}
        {searching && !loadingMore && (
          <DrawerStateCard
            tone="info"
            title={includeExternal ? 'Searching catalog + external' : 'Searching catalog'}
            description="Fetching matches..."
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
            description="Run a search to pull from your catalog. Toggle external if you want connectors."
          />
        )}
        {hasSearched && !searching && results.length === 0 && !error && (
          <DrawerStateCard
            role="status"
            ariaLive="polite"
            title="No matches yet"
            description="Try another phrase or include external sources."
          />
        )}
        {error && (
          <DrawerStateCard
            tone="error"
            title={errorKind === 'external' ? 'External search unavailable' : 'Search failed'}
            description={
              errorKind === 'external'
                ? `${error} You can retry without external sources.`
                : error
            }
            actionLabel={errorKind === 'external' ? 'Search internal only' : 'Try again'}
            onAction={() => {
              if (errorKind === 'external') {
                setError(null);
                setErrorKind(null);
                performSearch(1, { includeExternalOverride: false });
                return;
              }
              setError(null);
              setErrorKind(null);
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
          {sortedResults.map((item) => (
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
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-xs uppercase tracking-wide text-slate-400">
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
                      <p className="text-xs text-slate-400">Released {item.release_date}</p>
                    )}
                    {item.source_name && (
                      <p className="text-[11px] text-slate-400">
                        Source: {formatSearchSource(item.source_name)}
                      </p>
                    )}
                    {item.preview_expires_at && (
                      <p className="text-[11px] text-amber-200">
                        Preview expires {formatTimestamp(item.preview_expires_at)}
                      </p>
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

function formatTimestamp(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}
