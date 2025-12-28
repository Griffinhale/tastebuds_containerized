// Taste profile API helpers.

import { apiFetch } from './api';

export type TasteProfileSummary = {
  menus: number;
  courses: number;
  items: number;
  favorites: number;
  minutes_spent: number;
};

export type TasteProfilePayload = {
  summary: TasteProfileSummary;
  media_type_counts: Record<string, number>;
  menu_media_type_counts: Record<string, number>;
  top_tags: { name: string; count: number }[];
  log_counts: Record<string, number>;
  signals: { media_items: number; logs: number };
};

export type TasteProfile = {
  id: string;
  user_id: string;
  generated_at: string;
  profile: TasteProfilePayload;
};

export async function getTasteProfile(refresh?: boolean) {
  const query = refresh ? '?refresh=true' : '';
  return apiFetch<TasteProfile>(`/me/taste-profile${query}`, undefined, { isServer: false });
}

export async function refreshTasteProfile() {
  return apiFetch<TasteProfile>(
    '/me/taste-profile/refresh',
    {
      method: 'POST',
      body: JSON.stringify({ force: true }),
    },
    { isServer: false }
  );
}
