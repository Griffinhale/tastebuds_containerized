// Media detail and ingestion helpers for future detail views.
import { apiFetch } from './api';
import { MediaType } from './search';

export type MediaSourceDetail = {
  id: string;
  source_name: string;
  external_id: string;
  canonical_url?: string | null;
  fetched_at: string;
};

export type BookDetail = {
  authors?: string[] | null;
  page_count?: number | null;
  publisher?: string | null;
  language?: string | null;
  isbn_10?: string | null;
  isbn_13?: string | null;
};

export type MovieDetail = {
  runtime_minutes?: number | null;
  directors?: string[] | null;
  producers?: string[] | null;
  tmdb_type?: string | null;
};

export type GameDetail = {
  platforms?: string[] | null;
  developers?: string[] | null;
  publishers?: string[] | null;
  genres?: string[] | null;
};

export type MusicDetail = {
  artist_name?: string | null;
  album_name?: string | null;
  track_number?: number | null;
  duration_ms?: number | null;
};

export type MediaDetailBase = {
  media_type: MediaType;
  title: string;
  subtitle?: string | null;
  description?: string | null;
  release_date?: string | null;
  cover_image_url?: string | null;
  canonical_url?: string | null;
  metadata?: Record<string, unknown> | null;
  book?: BookDetail | null;
  movie?: MovieDetail | null;
  game?: GameDetail | null;
  music?: MusicDetail | null;
};

export type MediaItemDetail = MediaDetailBase & {
  id: string;
  sources: MediaSourceDetail[];
};

export type MediaPreviewDetail = MediaDetailBase & {
  preview_id: string;
  source_name: string;
  source_id: string;
  source_url?: string | null;
  preview_expires_at?: string | null;
};

export type IngestResponse = {
  media_item: MediaItemDetail;
  source_name: string;
};

export async function ingestMedia(
  source: string,
  payload: { external_id?: string; url?: string; force_refresh?: boolean }
) {
  return apiFetch<IngestResponse>(
    `/ingest/${source}`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    { isServer: false }
  );
}

export async function getMediaDetail(mediaItemId: string, options?: { isServer?: boolean }) {
  return apiFetch<MediaItemDetail>(`/media/${mediaItemId}`, undefined, {
    isServer: options?.isServer ?? false,
  });
}

export async function getPreviewDetail(
  previewId: string,
  options?: { isServer?: boolean; token?: string }
) {
  return apiFetch<MediaPreviewDetail>(`/previews/${previewId}`, undefined, {
    isServer: options?.isServer ?? false,
    token: options?.token,
  });
}
