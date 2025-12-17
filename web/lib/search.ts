"use client";

import { apiFetch } from './api';

export type MediaType = 'book' | 'movie' | 'tv' | 'game' | 'music';

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

  const queryString = searchParams.toString();
  return apiFetch<MediaSearchResponse>(`/search?${queryString}`, undefined, { isServer: false });
}
