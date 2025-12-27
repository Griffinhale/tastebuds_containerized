// Library and log API helpers for the web app.
import { apiFetch } from './api';

export type MediaType = 'book' | 'movie' | 'tv' | 'game' | 'music';

export type UserItemStatus =
  | 'consumed'
  | 'currently_consuming'
  | 'want_to_consume'
  | 'paused'
  | 'dropped';

export type UserItemLogType = 'started' | 'progress' | 'finished' | 'note' | 'goal';

export type MediaItemBase = {
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

export type UserItemState = {
  id: string;
  user_id: string;
  media_item_id: string;
  status: UserItemStatus;
  rating?: number | null;
  favorite: boolean;
  notes?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
};

export type UserItemLog = {
  id: string;
  user_id: string;
  media_item_id: string;
  log_type: UserItemLogType;
  notes?: string | null;
  minutes_spent?: number | null;
  progress_percent?: number | null;
  goal_target?: string | null;
  goal_due_on?: string | null;
  logged_at: string;
  created_at: string;
  updated_at: string;
  media_item?: MediaItemBase | null;
};

export type LibraryItem = {
  media_item: MediaItemBase;
  state?: UserItemState | null;
  last_log?: UserItemLog | null;
  log_count: number;
  last_activity_at?: string | null;
};

export type LibrarySummary = {
  total: number;
  consumed: number;
  currently_consuming: number;
  want_to_consume: number;
  paused: number;
  dropped: number;
};

export type LibraryOverview = {
  summary: LibrarySummary;
  items: LibraryItem[];
  next_up: LibraryItem[];
};

export type CreateLogInput = {
  media_item_id: string;
  log_type: UserItemLogType;
  notes?: string | null;
  minutes_spent?: number | null;
  progress_percent?: number | null;
  goal_target?: string | null;
  goal_due_on?: string | null;
  logged_at?: string | null;
};

export type UpdateLogInput = {
  log_type?: UserItemLogType;
  notes?: string | null;
  minutes_spent?: number | null;
  progress_percent?: number | null;
  goal_target?: string | null;
  goal_due_on?: string | null;
  logged_at?: string | null;
};

export type UpdateStateInput = {
  status: UserItemStatus;
  rating?: number | null;
  favorite?: boolean;
  notes?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
};

export async function getLibraryOverview() {
  return apiFetch<LibraryOverview>('/me/library', undefined, { isServer: false });
}

export async function listLogs(params?: {
  media_item_id?: string;
  log_type?: UserItemLogType;
  limit?: number;
  offset?: number;
}) {
  const search = new URLSearchParams();
  if (params?.media_item_id) search.set('media_item_id', params.media_item_id);
  if (params?.log_type) search.set('log_type', params.log_type);
  if (params?.limit) search.set('limit', String(params.limit));
  if (params?.offset) search.set('offset', String(params.offset));
  const suffix = search.toString();
  return apiFetch<UserItemLog[]>(`/me/logs${suffix ? `?${suffix}` : ''}`, undefined, {
    isServer: false,
  });
}

export async function createLog(input: CreateLogInput) {
  return apiFetch<UserItemLog>(
    '/me/logs',
    {
      method: 'POST',
      body: JSON.stringify(input),
    },
    { isServer: false }
  );
}

export async function updateLog(logId: string, input: UpdateLogInput) {
  return apiFetch<UserItemLog>(
    `/me/logs/${logId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(input),
    },
    { isServer: false }
  );
}

export async function deleteLog(logId: string) {
  await apiFetch(`/me/logs/${logId}`, { method: 'DELETE' }, { isServer: false });
}

export async function upsertState(mediaItemId: string, input: UpdateStateInput) {
  return apiFetch<UserItemState>(
    `/me/states/${mediaItemId}`,
    {
      method: 'PUT',
      body: JSON.stringify(input),
    },
    { isServer: false }
  );
}
