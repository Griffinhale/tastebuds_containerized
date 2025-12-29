export const SEARCH_SOURCE_LABELS: Record<string, string> = {
  internal: 'Internal',
  external: 'External',
  google_books: 'Google Books',
  tmdb: 'TMDB',
  igdb: 'IGDB',
  lastfm: 'Last.fm',
};

export function formatSearchSource(source?: string | null) {
  if (!source) return 'Internal';
  return SEARCH_SOURCE_LABELS[source] ?? source;
}
