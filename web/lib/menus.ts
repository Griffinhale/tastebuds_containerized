// Menu CRUD API helpers for the web app.
import { apiFetch } from './api';

export type MediaItemPreview = {
  id: string;
  title: string;
  subtitle?: string | null;
  description?: string | null;
  release_date?: string | null;
  cover_image_url?: string | null;
  canonical_url?: string | null;
  metadata?: Record<string, unknown> | null;
};

export type CourseItem = {
  id: string;
  media_item_id: string;
  notes?: string | null;
  position: number;
  updated_at: string;
  media_item?: MediaItemPreview | null;
};

export type Course = {
  id: string;
  title: string;
  description?: string | null;
  intent?: string | null;
  position: number;
  updated_at: string;
  items: CourseItem[];
};

export type Menu = {
  id: string;
  title: string;
  description?: string | null;
  slug: string;
  is_public: boolean;
  owner_id: string;
  created_at: string;
  updated_at: string;
  courses: Course[];
  pairings?: MenuItemPairing[];
};

export type MenuItemPairing = {
  id: string;
  menu_id: string;
  primary_course_item_id: string;
  paired_course_item_id: string;
  relationship?: string | null;
  note?: string | null;
  created_at: string;
  updated_at: string;
  primary_item?: CourseItem | null;
  paired_item?: CourseItem | null;
};

export type MenuPairingInput = {
  primary_course_item_id: string;
  paired_course_item_id: string;
  relationship?: string | null;
  note?: string | null;
};

export type MenuShareToken = {
  id: string;
  menu_id: string;
  token: string;
  expires_at?: string | null;
  revoked_at?: string | null;
  last_accessed_at?: string | null;
  access_count: number;
  created_at: string;
};

export type MenuLineageMenu = {
  id: string;
  title: string;
  slug: string;
  is_public: boolean;
  created_at: string;
};

export type MenuLineageSource = {
  menu: MenuLineageMenu;
  note?: string | null;
};

export type MenuLineage = {
  source_menu?: MenuLineageSource | null;
  forked_menus: MenuLineageMenu[];
  fork_count: number;
};

export type CreateMenuInput = {
  title: string;
  description?: string;
  is_public?: boolean;
};

export type CreateCourseInput = {
  title: string;
  description?: string;
  intent?: string;
  position: number;
};

export type CreateCourseItemInput = {
  media_item_id: string;
  position: number;
  notes?: string;
};

export type UpdateCourseInput = {
  title?: string;
  description?: string | null;
  intent?: string | null;
  expectedUpdatedAt?: string;
};

export type UpdateCourseItemInput = {
  notes?: string | null;
  expectedUpdatedAt?: string;
};

export type MenuForkInput = {
  title?: string | null;
  description?: string | null;
  is_public?: boolean | null;
  note?: string | null;
};

export async function listMenus() {
  // Authenticated menu list for the current user.
  return apiFetch<Menu[]>('/menus', undefined, { isServer: false });
}

export async function getMenu(menuId: string) {
  return apiFetch<Menu>(`/menus/${menuId}`, undefined, { isServer: false });
}

export async function createMenu(input: CreateMenuInput) {
  return apiFetch<Menu>(
    '/menus',
    {
      method: 'POST',
      body: JSON.stringify({
        title: input.title,
        description: input.description,
        is_public: input.is_public ?? false,
      }),
    },
    { isServer: false }
  );
}

export async function createCourse(menuId: string, input: CreateCourseInput) {
  return apiFetch<Course>(
    `/menus/${menuId}/courses`,
    {
      method: 'POST',
      body: JSON.stringify({
        title: input.title,
        description: input.description,
        intent: input.intent,
        position: input.position,
      }),
    },
    { isServer: false }
  );
}

export async function updateCourse(menuId: string, courseId: string, input: UpdateCourseInput) {
  return apiFetch<Course>(
    `/menus/${menuId}/courses/${courseId}`,
    {
      method: 'PATCH',
      body: JSON.stringify({
        title: input.title,
        description: input.description,
        intent: input.intent,
        expected_updated_at: input.expectedUpdatedAt,
      }),
    },
    { isServer: false }
  );
}

export async function deleteCourse(menuId: string, courseId: string) {
  await apiFetch(`/menus/${menuId}/courses/${courseId}`, { method: 'DELETE' }, { isServer: false });
}

export async function createCourseItem(
  menuId: string,
  courseId: string,
  input: CreateCourseItemInput
) {
  return apiFetch<CourseItem>(
    `/menus/${menuId}/courses/${courseId}/items`,
    {
      method: 'POST',
      body: JSON.stringify({
        media_item_id: input.media_item_id,
        position: input.position,
        notes: input.notes,
      }),
    },
    { isServer: false }
  );
}

export async function deleteCourseItem(menuId: string, itemId: string) {
  await apiFetch(
    `/menus/${menuId}/course-items/${itemId}`,
    { method: 'DELETE' },
    { isServer: false }
  );
}

export async function updateCourseItem(
  menuId: string,
  itemId: string,
  input: UpdateCourseItemInput
) {
  return apiFetch<CourseItem>(
    `/menus/${menuId}/course-items/${itemId}`,
    {
      method: 'PATCH',
      body: JSON.stringify({
        notes: input.notes,
        expected_updated_at: input.expectedUpdatedAt,
      }),
    },
    { isServer: false }
  );
}

export async function reorderCourseItems(menuId: string, courseId: string, itemIds: string[]) {
  return apiFetch<Course>(
    `/menus/${menuId}/courses/${courseId}/reorder-items`,
    {
      method: 'POST',
      body: JSON.stringify({ item_ids: itemIds }),
    },
    { isServer: false }
  );
}

export async function getPublicMenuBySlug(slug: string) {
  // Server-side fetch avoids leaking cookies to public endpoints.
  const encoded = encodeURIComponent(slug.trim());
  return apiFetch<Menu>(`/public/menus/${encoded}`, undefined, {
    isServer: true,
    withCredentials: false,
  });
}

export async function getDraftMenuByToken(token: string) {
  const encoded = encodeURIComponent(token.trim());
  return apiFetch<{ menu: Menu; share_token_id: string; share_token_expires_at?: string | null }>(
    `/public/menus/draft/${encoded}`,
    undefined,
    {
      isServer: true,
      withCredentials: false,
    }
  );
}

export async function forkMenu(menuId: string, input: MenuForkInput) {
  return apiFetch<Menu>(
    `/menus/${menuId}/fork`,
    {
      method: 'POST',
      body: JSON.stringify({
        title: input.title ?? undefined,
        description: input.description ?? undefined,
        is_public: input.is_public ?? undefined,
        note: input.note ?? undefined,
      }),
    },
    { isServer: false }
  );
}

export async function listMenuPairings(menuId: string) {
  return apiFetch<MenuItemPairing[]>(`/menus/${menuId}/pairings`, undefined, { isServer: false });
}

export async function createMenuPairing(menuId: string, payload: MenuPairingInput) {
  return apiFetch<MenuItemPairing>(
    `/menus/${menuId}/pairings`,
    {
      method: 'POST',
      body: JSON.stringify({
        primary_course_item_id: payload.primary_course_item_id,
        paired_course_item_id: payload.paired_course_item_id,
        relationship: payload.relationship,
        note: payload.note,
      }),
    },
    { isServer: false }
  );
}

export async function deleteMenuPairing(menuId: string, pairingId: string) {
  await apiFetch(
    `/menus/${menuId}/pairings/${pairingId}`,
    { method: 'DELETE' },
    { isServer: false }
  );
}

export async function listMenuShareTokens(menuId: string) {
  return apiFetch<MenuShareToken[]>(`/menus/${menuId}/share-tokens`, undefined, {
    isServer: false,
  });
}

export async function createMenuShareToken(menuId: string, expiresAt?: string | null) {
  return apiFetch<MenuShareToken>(
    `/menus/${menuId}/share-tokens`,
    {
      method: 'POST',
      body: JSON.stringify({ expires_at: expiresAt ?? null }),
    },
    { isServer: false }
  );
}

export async function revokeMenuShareToken(menuId: string, tokenId: string) {
  await apiFetch(
    `/menus/${menuId}/share-tokens/${tokenId}`,
    { method: 'DELETE' },
    { isServer: false }
  );
}

export async function getMenuLineage(menuId: string) {
  return apiFetch<MenuLineage>(`/menus/${menuId}/lineage`, undefined, { isServer: false });
}

export async function getPublicMenuLineage(slug: string) {
  const encoded = encodeURIComponent(slug.trim());
  return apiFetch<MenuLineage>(`/public/menus/${encoded}/lineage`, undefined, {
    isServer: true,
    withCredentials: false,
  });
}

export function getMenuItemCount(menu: Menu) {
  return menu.courses.reduce((total, course) => total + course.items.length, 0);
}
