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
  media_item?: MediaItemPreview | null;
};

export type Course = {
  id: string;
  title: string;
  description?: string | null;
  intent?: string | null;
  position: number;
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
};

export type UpdateCourseItemInput = {
  notes?: string | null;
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
      body: JSON.stringify({ notes: input.notes }),
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
