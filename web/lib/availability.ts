// Availability API helpers for public and authenticated views.

import { apiFetch } from './api';

export type AvailabilitySummary = {
  providers: string[];
  regions: string[];
  formats: string[];
  status_counts: Record<string, number>;
  last_checked_at?: string | null;
};

export type AvailabilitySummaryItem = AvailabilitySummary & {
  media_item_id: string;
};

export async function getAvailabilitySummary(
  mediaItemIds: string[],
  options?: { isServer?: boolean }
) {
  return apiFetch<AvailabilitySummaryItem[]>(
    '/media/availability/summary',
    {
      method: 'POST',
      body: JSON.stringify({ media_item_ids: mediaItemIds }),
    },
    { isServer: options?.isServer ?? false, withCredentials: false }
  );
}
