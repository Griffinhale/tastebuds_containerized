'use client';

import { apiFetch } from './api';

export type MediaType = 'book' | 'movie' | 'tv' | 'game' | 'music';

export type SearchSource = 'internal' | 'external' | 'google_books' | 'tmdb' | 'igdb' | 'lastfm';

export type MediaSearchItem = {
  id: string;
  media_type: MediaType;
  title: string;
  subtitle?: string | null;
  description?: string | null;
  release_date?: string | null;
  cover_image_url?: string | null;
  canonical_url?: string | null;
  metadata?: Record<string, unknown> | null;
};

export type MediaSearchResponse = {
  results: MediaSearchItem[];
  source: string;
  metadata?: Record<string, unknown> | null;
};

type SearchParams = {
  query: string;
  types?: MediaType[];
  includeExternal?: boolean;
  page?: number;
  perPage?: number;
  sourceFilters?: SearchSource[];
  externalPerSource?: number;
};

export async function searchMedia(params: SearchParams): Promise<MediaSearchResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set('q', params.query);
  if (params.includeExternal) {
    searchParams.set('include_external', 'true');
  }
  params.types?.forEach((type) => {
    searchParams.append('types', type);
  });
  if (params.page) {
    searchParams.set('page', String(params.page));
  }
  if (params.perPage) {
    searchParams.set('per_page', String(params.perPage));
  }
  if (params.sourceFilters) {
    params.sourceFilters.forEach((source) => {
      searchParams.append('sources', source);
    });
  }
  if (params.externalPerSource) {
    searchParams.set('external_per_source', String(params.externalPerSource));
  }

  const queryString = searchParams.toString();
  return apiFetch<MediaSearchResponse>(`/search?${queryString}`, undefined, { isServer: false });
}
