"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import {
  CreateCourseInput,
  CreateCourseItemInput,
  CreateMenuInput,
  Course,
  CourseItem,
  Menu,
  createCourse,
  createCourseItem,
  createMenu,
  deleteCourse,
  deleteCourseItem,
  getMenu,
  listMenus
} from '../lib/menus';
import { CourseItemSearch } from './course-item-search';

export function MenuDashboard() {
  const [menus, setMenus] = useState<Menu[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const replaceMenu = useCallback((menu: Menu) => {
    setMenus((current) => current.map((existing) => (existing.id === menu.id ? menu : existing)));
    setLastUpdated(new Date());
  }, []);

  const fetchMenus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listMenus();
      setMenus(data);
      setLastUpdated(new Date());
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load menus.';
      const normalized = message.toLowerCase();
      if (normalized.includes('401') || normalized.includes('unauthorized')) {
        setError('Log in to view and manage your menus.');
      } else {
        setError(message);
      }
      setMenus([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshMenu = useCallback(
    async (menuId: string) => {
      try {
        const menu = await getMenu(menuId);
        replaceMenu(menu);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to refresh menu.';
        setError(message);
      }
    },
    [replaceMenu]
  );

  useEffect(() => {
    fetchMenus();
  }, [fetchMenus]);

  const statusText = useMemo(() => {
    if (loading) return 'Loading menus...';
    if (error) return error;
    if (!menus.length) return 'No menus yet. Use the form below to create your first one.';
    return `Showing ${menus.length} menu${menus.length === 1 ? '' : 's'}.`;
  }, [menus, loading, error]);

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-emerald-300">Your menus</p>
            <p className="text-sm text-slate-200">{statusText}</p>
          </div>
          <button
            onClick={fetchMenus}
            disabled={loading}
            className="text-sm text-emerald-300 underline decoration-emerald-300/60 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Refresh
          </button>
        </div>
        {lastUpdated && !loading && !error && (
          <p className="mt-2 text-xs text-slate-400">Last updated {lastUpdated.toLocaleTimeString()}</p>
        )}

        {!loading && !error && menus.length > 0 && (
          <ul className="mt-4 space-y-4">
            {menus.map((menu) => (
              <MenuCard key={menu.id} menu={menu} onRefresh={() => refreshMenu(menu.id)} />
            ))}
          </ul>
        )}

        {error && <p className="mt-4 text-sm text-red-300">{error}</p>}
      </section>

      <CreateMenuForm
        onCreated={(menu) => {
          setMenus((prev) => [menu, ...prev]);
          setError(null);
          setLastUpdated(new Date());
        }}
      />
    </div>
  );
}

function MenuCard({ menu, onRefresh }: { menu: Menu; onRefresh: () => Promise<void> }) {
  return (
    <li className="rounded-lg border border-slate-800 bg-slate-950/70 p-4 shadow-sm shadow-emerald-500/5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">Slug: {menu.slug}</p>
          <h3 className="text-lg font-semibold text-white">{menu.title}</h3>
          {menu.description && <p className="text-sm text-slate-200">{menu.description}</p>}
        </div>
        <VisibilityBadge isPublic={menu.is_public} />
      </div>
      <dl className="mt-4 grid gap-4 sm:grid-cols-3">
        <InfoItem label="Courses" value={menu.courses.length || 0} />
        <InfoItem label="Created" value={new Date(menu.created_at).toLocaleDateString()} />
        <InfoItem label="Updated" value={new Date(menu.updated_at).toLocaleDateString()} />
      </dl>

      <div className="mt-6 space-y-4">
        <p className="text-sm font-semibold text-emerald-300">Courses</p>
        {menu.courses.length === 0 && (
          <p className="text-sm text-slate-300">No courses yet. Add one to begin ordering items.</p>
        )}
        {menu.courses.map((course) => (
          <CourseEditor key={course.id} course={course} menuId={menu.id} onRefresh={onRefresh} />
        ))}
        <AddCourseForm menuId={menu.id} nextPosition={menu.courses.length + 1} onSuccess={onRefresh} />
      </div>
    </li>
  );
}

function CourseEditor({
  course,
  menuId,
  onRefresh
}: {
  course: Course;
  menuId: string;
  onRefresh: () => Promise<void>;
}) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await deleteCourse(menuId, course.id);
      await onRefresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete course.';
      setError(message);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">Position {course.position}</p>
          <h4 className="text-base font-semibold text-white">{course.title}</h4>
          {course.description && <p className="text-sm text-slate-200">{course.description}</p>}
        </div>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="text-xs font-semibold text-slate-400 underline decoration-slate-500/60 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {deleting ? 'Removing…' : 'Delete course'}
        </button>
      </div>

      <div className="mt-4 space-y-3">
        <p className="text-xs uppercase tracking-wide text-slate-400">Items</p>
        {course.items.length === 0 && (
          <p className="text-sm text-slate-300">
            Add an item via search/ingest or paste a known media ID to populate this course.
          </p>
        )}
        {course.items.map((item) => (
          <CourseItemRow key={item.id} item={item} menuId={menuId} onRefresh={onRefresh} />
        ))}
      </div>

      <div className="mt-4 space-y-4 border-t border-slate-800 pt-4">
        <AddCourseItemForm course={course} menuId={menuId} onSuccess={onRefresh} />
        <CourseItemSearch menuId={menuId} course={course} onAdded={onRefresh} />
      </div>

      {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
    </div>
  );
}

function CourseItemRow({
  item,
  menuId,
  onRefresh
}: {
  item: CourseItem;
  menuId: string;
  onRefresh: () => Promise<void>;
}) {
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRemove() {
    setRemoving(true);
    setError(null);
    try {
      await deleteCourseItem(menuId, item.id);
      await onRefresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete item.';
      setError(message);
    } finally {
      setRemoving(false);
    }
  }

  return (
    <div className="rounded-md border border-slate-800 bg-slate-900/70 p-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Position {item.position}</p>
          <p className="text-sm font-semibold text-white">
            {item.media_item?.title || 'Untitled media'}{' '}
            <span className="text-xs text-slate-400">({item.media_item_id})</span>
          </p>
          {item.notes && <p className="text-xs text-slate-300">{item.notes}</p>}
        </div>
        <button
          onClick={handleRemove}
          disabled={removing}
          className="text-xs font-semibold text-slate-400 underline decoration-slate-500/60 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {removing ? 'Removing…' : 'Remove'}
        </button>
      </div>
      {error && <p className="mt-2 text-xs text-red-300">{error}</p>}
    </div>
  );
}

function VisibilityBadge({ isPublic }: { isPublic: boolean }) {
  const copy = isPublic ? 'Public' : 'Private';
  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${
        isPublic
          ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-200'
          : 'border-slate-800 bg-slate-900 text-slate-200'
      }`}
    >
      {copy}
    </span>
  );
}

function InfoItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-400">{label}</dt>
      <dd className="text-sm font-semibold text-white">{value}</dd>
    </div>
  );
}

function CreateMenuForm({ onCreated }: { onCreated: (menu: Menu) => void }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isPublic, setIsPublic] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setTitle('');
    setDescription('');
    setIsPublic(false);
  };

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    const payload: CreateMenuInput = {
      title,
      description: description || undefined,
      is_public: isPublic
    };

    try {
      const menu = await createMenu(payload);
      onCreated(menu);
      reset();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create menu.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
      <p className="text-sm font-semibold text-emerald-300">Create a new menu</p>
      <p className="text-sm text-slate-200">Menus organize your recommended courses with ordered media.</p>

      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <div className="space-y-1">
          <label htmlFor="menu_title" className="text-sm text-slate-200">
            Title
          </label>
          <input
            id="menu_title"
            type="text"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="menu_description" className="text-sm text-slate-200">
            Description
          </label>
          <textarea
            id="menu_description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
            placeholder="Optional summary for your menu."
          />
        </div>

        <label className="flex items-center gap-2 text-sm text-slate-200">
          <input
            type="checkbox"
            checked={isPublic}
            onChange={(e) => setIsPublic(e.target.checked)}
            className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-emerald-400"
          />
          Make this menu public
        </label>

        {error && <p className="text-sm text-red-300">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-70"
        >
          {loading ? 'Creating...' : 'Create menu'}
        </button>
      </form>
    </section>
  );
}

function AddCourseForm({
  menuId,
  nextPosition,
  onSuccess
}: {
  menuId: string;
  nextPosition: number;
  onSuccess: () => Promise<void>;
}) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [position, setPosition] = useState(nextPosition);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPosition(nextPosition);
  }, [nextPosition]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    const payload: CreateCourseInput = {
      title,
      description: description || undefined,
      position
    };

    try {
      await createCourse(menuId, payload);
      await onSuccess();
      setTitle('');
      setDescription('');
      setPosition((prev) => prev + 1);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create course.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-dashed border-slate-800 p-4">
      <p className="text-sm font-semibold text-slate-200">Add course</p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div className="space-y-1">
          <label className="text-xs text-slate-400" htmlFor={`course_title_${menuId}`}>
            Title
          </label>
          <input
            id={`course_title_${menuId}`}
            type="text"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-slate-400" htmlFor={`course_position_${menuId}`}>
            Position
          </label>
          <input
            id={`course_position_${menuId}`}
            type="number"
            min={1}
            value={position}
            onChange={(e) => setPosition(Number(e.target.value))}
            className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
          />
        </div>
      </div>
      <div className="mt-3 space-y-1">
        <label className="text-xs text-slate-400" htmlFor={`course_desc_${menuId}`}>
          Description
        </label>
        <textarea
          id={`course_desc_${menuId}`}
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
          placeholder="Optional context for this course."
        />
      </div>
      {error && <p className="mt-2 text-xs text-red-300">{error}</p>}
      <button
        type="submit"
        disabled={loading}
        className="mt-3 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-70"
      >
        {loading ? 'Adding…' : 'Add course'}
      </button>
    </form>
  );
}

function AddCourseItemForm({
  course,
  menuId,
  onSuccess
}: {
  course: Course;
  menuId: string;
  onSuccess: () => Promise<void>;
}) {
  const [mediaItemId, setMediaItemId] = useState('');
  const [position, setPosition] = useState(course.items.length + 1);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPosition(course.items.length + 1);
  }, [course.items.length]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    const payload: CreateCourseItemInput = {
      media_item_id: mediaItemId,
      position,
      notes: notes || undefined
    };

    try {
      await createCourseItem(menuId, course.id, payload);
      await onSuccess();
      setMediaItemId('');
      setNotes('');
      setPosition((prev) => prev + 1);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to add item.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <p className="text-sm font-semibold text-slate-200">Add course item</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1">
          <label className="text-xs text-slate-400" htmlFor={`item_media_${course.id}`}>
            Media item ID
          </label>
          <input
            id={`item_media_${course.id}`}
            type="text"
            required
            value={mediaItemId}
            onChange={(e) => setMediaItemId(e.target.value)}
            className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
            placeholder="Paste an existing media_item_id"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-slate-400" htmlFor={`item_position_${course.id}`}>
            Position
          </label>
          <input
            id={`item_position_${course.id}`}
            type="number"
            min={1}
            value={position}
            onChange={(e) => setPosition(Number(e.target.value))}
            className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
          />
        </div>
      </div>
      <div className="space-y-1">
        <label className="text-xs text-slate-400" htmlFor={`item_notes_${course.id}`}>
          Notes
        </label>
        <textarea
          id={`item_notes_${course.id}`}
          rows={2}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
          placeholder="Optional serving notes."
        />
      </div>
      {error && <p className="text-xs text-red-300">{error}</p>}
      <button
        type="submit"
        disabled={loading}
        className="rounded-lg bg-emerald-500 px-4 py-2 text-xs font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-70"
      >
        {loading ? 'Adding…' : 'Add item'}
      </button>
    </form>
  );
}
