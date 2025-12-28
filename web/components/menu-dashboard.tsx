'use client';

// Menu dashboard with local optimistic updates and drag-and-drop ordering.

import Link from 'next/link';
import { DragEvent, FormEvent, ReactNode, useCallback, useEffect, useMemo, useState } from 'react';
import {
  CreateCourseInput,
  CreateCourseItemInput,
  CreateMenuInput,
  Course,
  CourseItem,
  Menu,
  MenuItemPairing,
  MenuLineage,
  MenuPairingInput,
  MenuShareToken,
  createCourse,
  createCourseItem,
  createMenu,
  createMenuPairing,
  createMenuShareToken,
  deleteCourse,
  deleteCourseItem,
  deleteMenuPairing,
  getMenuLineage,
  getMenu,
  listMenus,
  reorderCourseItems,
  updateCourse,
  updateCourseItem,
} from '../lib/menus';
import { CourseItemSearch } from './course-item-search';
import { ApiError } from '../lib/api';

export function MenuDashboard() {
  const [menus, setMenus] = useState<Menu[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const replaceMenu = useCallback((menu: Menu) => {
    setMenus((current) => current.map((existing) => (existing.id === menu.id ? menu : existing)));
    setLastUpdated(new Date());
  }, []);

  const mutateMenu = useCallback((menuId: string, updater: (menu: Menu) => Menu) => {
    setMenus((current) =>
      current.map((existing) => (existing.id === menuId ? updater(existing) : existing))
    );
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
          <p className="mt-2 text-xs text-slate-400">
            Last updated {lastUpdated.toLocaleTimeString()}
          </p>
        )}

        {!loading && !error && menus.length > 0 && (
          <ul className="mt-4 space-y-4">
            {menus.map((menu) => (
              <MenuCard
                key={menu.id}
                menu={menu}
                onRefresh={() => refreshMenu(menu.id)}
                onMenuMutate={(updater) => mutateMenu(menu.id, updater)}
              />
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

function MenuCard({
  menu,
  onRefresh,
  onMenuMutate,
}: {
  menu: Menu;
  onRefresh: () => Promise<void>;
  onMenuMutate: (updater: (menu: Menu) => Menu) => void;
}) {
  const handleCourseUpdated = useCallback(
    (updatedCourse: Course) => {
      onMenuMutate((current) => ({
        ...current,
        courses: current.courses.map((course) =>
          course.id === updatedCourse.id ? updatedCourse : course
        ),
      }));
    },
    [onMenuMutate]
  );

  const handleCourseRemoved = useCallback(
    (courseId: string) => {
      onMenuMutate((current) => ({
        ...current,
        courses: current.courses.filter((course) => course.id !== courseId),
      }));
    },
    [onMenuMutate]
  );

  const handleCourseAdded = useCallback(
    (newCourse: Course) => {
      onMenuMutate((current) => ({
        ...current,
        courses: [...current.courses, newCourse].sort((a, b) => a.position - b.position),
      }));
    },
    [onMenuMutate]
  );

  return (
    <li className="rounded-lg border border-slate-800 bg-slate-950/70 p-4 shadow-sm shadow-emerald-500/5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">Slug: {menu.slug}</p>
          <h3 className="text-lg font-semibold text-white">{menu.title}</h3>
          {menu.description && <p className="text-sm text-slate-200">{menu.description}</p>}
        </div>
        <div className="flex flex-col items-start gap-2 sm:items-end">
          <VisibilityBadge isPublic={menu.is_public} />
          {menu.is_public && (
            <Link
              href={`/menus/${menu.slug}`}
              className="text-xs font-semibold text-emerald-300 underline decoration-emerald-300/60"
            >
              View public page
            </Link>
          )}
        </div>
      </div>
      <dl className="mt-4 grid gap-4 sm:grid-cols-3">
        <InfoItem label="Courses" value={menu.courses.length || 0} />
        <InfoItem label="Created" value={new Date(menu.created_at).toLocaleDateString()} />
        <InfoItem label="Updated" value={new Date(menu.updated_at).toLocaleDateString()} />
      </dl>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <DraftSharePanel menuId={menu.id} menuSlug={menu.slug} isPublic={menu.is_public} />
        <LineageSummary menuId={menu.id} />
      </div>

      <div className="mt-6 space-y-4">
        <p className="text-sm font-semibold text-emerald-300">Courses</p>
        {menu.courses.length === 0 && (
          <p className="text-sm text-slate-300">No courses yet. Add one to begin ordering items.</p>
        )}
        {menu.courses.map((course) => (
          <CourseEditor
            key={course.id}
            course={course}
            menuId={menu.id}
            onRefresh={onRefresh}
            onCourseUpdated={handleCourseUpdated}
            onCourseRemoved={() => handleCourseRemoved(course.id)}
          />
        ))}
        <AddCourseForm
          menuId={menu.id}
          nextPosition={menu.courses.length + 1}
          onCourseAdded={handleCourseAdded}
        />
        <PairingsPanel menu={menu} onMenuMutate={onMenuMutate} />
      </div>
    </li>
  );
}

function DraftSharePanel({
  menuId,
  menuSlug,
  isPublic,
}: {
  menuId: string;
  menuSlug: string;
  isPublic: boolean;
}) {
  const [token, setToken] = useState<MenuShareToken | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const shareBase =
    typeof window !== 'undefined'
      ? window.location.origin
      : process.env.NEXT_PUBLIC_APP_BASE_URL || 'http://localhost:3000';

  const shareUrl = token ? `${shareBase.replace(/\/$/, '')}/menus/draft/${token.token}` : '';

  async function handleCreateToken() {
    if (creating) return;
    setCreating(true);
    setError(null);
    try {
      const created = await createMenuShareToken(menuId);
      setToken(created);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create share link.';
      setError(message);
    } finally {
      setCreating(false);
    }
  }

  async function handleCopy() {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Copy failed.';
      setError(message);
    }
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-emerald-300">Draft share link</p>
          <p className="text-xs text-slate-300">
            Generate a private preview link before publishing.
          </p>
        </div>
        <button
          onClick={handleCreateToken}
          className="rounded-md bg-emerald-500 px-3 py-1 text-xs font-semibold text-slate-950 transition hover:bg-emerald-400"
          disabled={creating}
        >
          {creating ? 'Creating...' : 'Create link'}
        </button>
      </div>
      {token && (
        <div className="mt-3 space-y-2 text-xs text-slate-200">
          <p className="break-all">{shareUrl}</p>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={handleCopy}
              className="rounded-md border border-slate-700 px-3 py-1 text-xs font-semibold text-slate-100"
            >
              {copied ? 'Copied!' : 'Copy link'}
            </button>
            {isPublic && menuSlug && (
              <Link
                href={`/menus/${menuSlug}`}
                className="rounded-md border border-slate-700 px-3 py-1 text-xs font-semibold text-slate-100"
              >
                View public page
              </Link>
            )}
          </div>
          {token.expires_at && (
            <p className="text-[11px] text-slate-400">
              Expires {new Date(token.expires_at).toLocaleString()}
            </p>
          )}
        </div>
      )}
      {error && <p className="mt-2 text-xs text-red-300">{error}</p>}
    </div>
  );
}

function LineageSummary({ menuId }: { menuId: string }) {
  const [lineage, setLineage] = useState<MenuLineage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    getMenuLineage(menuId)
      .then((data) => {
        if (!mounted) return;
        setLineage(data);
        setError(null);
      })
      .catch((err) => {
        if (!mounted) return;
        const message = err instanceof Error ? err.message : 'Failed to load lineage.';
        setError(message);
      });
    return () => {
      mounted = false;
    };
  }, [menuId]);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-xs text-slate-200">
      <p className="text-sm font-semibold text-emerald-300">Lineage</p>
      {error && <p className="mt-2 text-red-300">{error}</p>}
      {!error && lineage?.source_menu?.menu && (
        <p className="mt-2">
          Forked from{' '}
          <span className="font-semibold text-emerald-200">{lineage.source_menu.menu.title}</span>
        </p>
      )}
      {!error && (
        <p className="mt-2 text-[11px] text-slate-400">Forks: {lineage?.fork_count ?? 0}</p>
      )}
    </div>
  );
}

function PairingsPanel({
  menu,
  onMenuMutate,
}: {
  menu: Menu;
  onMenuMutate: (updater: (menu: Menu) => Menu) => void;
}) {
  const items = useMemo(
    () =>
      menu.courses.flatMap((course) =>
        course.items.map((item) => ({
          id: item.id,
          label: `Course ${course.position}: ${item.media_item?.title || 'Untitled'}`,
        }))
      ),
    [menu.courses]
  );

  const [draft, setDraft] = useState<MenuPairingInput>({
    primary_course_item_id: items[0]?.id ?? '',
    paired_course_item_id: items[1]?.id ?? '',
    relationship: '',
    note: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!items.length) return;
    setDraft((current) => ({
      ...current,
      primary_course_item_id: current.primary_course_item_id || items[0]?.id || '',
      paired_course_item_id: current.paired_course_item_id || items[1]?.id || '',
    }));
  }, [items]);

  async function handleCreatePairing(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.primary_course_item_id || !draft.paired_course_item_id) {
      setError('Select two items to pair.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const pairing = await createMenuPairing(menu.id, draft);
      onMenuMutate((current) => ({
        ...current,
        pairings: [...(current.pairings ?? []), pairing],
      }));
      setDraft((current) => ({ ...current, relationship: '', note: '' }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create pairing.';
      setError(message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDeletePairing(pairing: MenuItemPairing) {
    setError(null);
    try {
      await deleteMenuPairing(menu.id, pairing.id);
      onMenuMutate((current) => ({
        ...current,
        pairings: (current.pairings ?? []).filter((item) => item.id !== pairing.id),
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete pairing.';
      setError(message);
    }
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-emerald-300">Narrative pairings</p>
          <p className="text-xs text-slate-300">Link items to reinforce a story arc.</p>
        </div>
      </div>
      {menu.pairings && menu.pairings.length > 0 && (
        <ul className="mt-3 space-y-2 text-xs text-slate-200">
          {menu.pairings.map((pairing) => (
            <li key={pairing.id} className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-white">
                  {pairing.primary_item?.media_item?.title || 'Untitled'} {' <-> '}
                  {pairing.paired_item?.media_item?.title || 'Untitled'}
                </p>
                {pairing.relationship && (
                  <p className="text-[11px] uppercase tracking-wide text-emerald-200">
                    {pairing.relationship}
                  </p>
                )}
                {pairing.note && <p className="text-[11px] text-slate-300">{pairing.note}</p>}
              </div>
              <button
                onClick={() => handleDeletePairing(pairing)}
                className="text-[11px] font-semibold text-red-300 hover:text-red-200"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleCreatePairing} className="mt-4 grid gap-3 text-xs text-slate-200">
        <div className="grid gap-2 sm:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-wide text-slate-400">Primary item</span>
            <select
              value={draft.primary_course_item_id}
              onChange={(event) =>
                setDraft((current) => ({ ...current, primary_course_item_id: event.target.value }))
              }
              className="rounded-md border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-white"
            >
              {items.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-wide text-slate-400">Paired item</span>
            <select
              value={draft.paired_course_item_id}
              onChange={(event) =>
                setDraft((current) => ({ ...current, paired_course_item_id: event.target.value }))
              }
              className="rounded-md border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-white"
            >
              {items.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-wide text-slate-400">Relationship</span>
            <input
              value={draft.relationship ?? ''}
              onChange={(event) =>
                setDraft((current) => ({ ...current, relationship: event.target.value }))
              }
              className="rounded-md border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-white"
              placeholder="Contrast, echo, bridge..."
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] uppercase tracking-wide text-slate-400">Note</span>
            <input
              value={draft.note ?? ''}
              onChange={(event) =>
                setDraft((current) => ({ ...current, note: event.target.value }))
              }
              className="rounded-md border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-white"
              placeholder="Why they pair"
            />
          </label>
        </div>
        <div className="flex items-center justify-between">
          <button
            type="submit"
            disabled={saving || items.length < 2}
            className="rounded-md bg-emerald-500 px-3 py-1 text-xs font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {saving ? 'Saving...' : 'Add pairing'}
          </button>
          {error && <p className="text-xs text-red-300">{error}</p>}
        </div>
      </form>
    </div>
  );
}

function CourseEditor({
  course,
  menuId,
  onRefresh,
  onCourseUpdated,
  onCourseRemoved,
}: {
  course: Course;
  menuId: string;
  onRefresh: () => Promise<void>;
  onCourseUpdated: (course: Course) => void;
  onCourseRemoved: () => void;
}) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reordering, setReordering] = useState(false);
  const [orderError, setOrderError] = useState<string | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [savingEdits, setSavingEdits] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState(course.title);
  const [draftDescription, setDraftDescription] = useState(course.description ?? '');
  const [draftIntent, setDraftIntent] = useState(course.intent ?? '');
  const [autoSaveState, setAutoSaveState] = useState<
    'idle' | 'saving' | 'saved' | 'error' | 'conflict'
  >('idle');
  const [autoSaveMessage, setAutoSaveMessage] = useState<string | null>(null);
  const [lastSaved, setLastSaved] = useState({
    title: course.title,
    description: course.description ?? '',
    intent: course.intent ?? '',
    updatedAt: course.updated_at,
  });
  const normalizedDraft = useMemo(
    () => ({
      title: draftTitle.trim(),
      description: draftDescription.trim(),
      intent: draftIntent.trim(),
    }),
    [draftDescription, draftIntent, draftTitle]
  );
  const normalizedLastSaved = useMemo(
    () => ({
      title: lastSaved.title.trim(),
      description: lastSaved.description.trim(),
      intent: lastSaved.intent.trim(),
    }),
    [lastSaved.description, lastSaved.intent, lastSaved.title]
  );
  const isDraftDirty =
    normalizedDraft.title !== normalizedLastSaved.title ||
    normalizedDraft.description !== normalizedLastSaved.description ||
    normalizedDraft.intent !== normalizedLastSaved.intent;

  useEffect(() => {
    const shouldSyncDrafts = !editing || !isDraftDirty;
    setLastSaved({
      title: course.title,
      description: course.description ?? '',
      intent: course.intent ?? '',
      updatedAt: course.updated_at,
    });
    if (shouldSyncDrafts) {
      setDraftTitle(course.title);
      setDraftDescription(course.description ?? '');
      setDraftIntent(course.intent ?? '');
    }
    setAutoSaveState('idle');
    setAutoSaveMessage(null);
  }, [course.description, course.intent, course.title, course.updated_at, editing, isDraftDirty]);

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await deleteCourse(menuId, course.id);
      onCourseRemoved();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete course.';
      setError(message);
    } finally {
      setDeleting(false);
    }
  }

  function handleItemRemoved(itemId: string) {
    const remaining = rebuildPositions(course.items.filter((item) => item.id !== itemId));
    onCourseUpdated({ ...course, items: remaining });
  }

  function handleItemAdded(newItem: CourseItem) {
    const nextItems = sortItemsByPosition([...course.items, newItem]);
    onCourseUpdated({ ...course, items: nextItems });
  }

  const handleItemUpdated = useCallback(
    (updatedItem: CourseItem) => {
      onCourseUpdated({
        ...course,
        items: course.items.map((item) => (item.id === updatedItem.id ? updatedItem : item)),
      });
    },
    [course, onCourseUpdated]
  );

  function handleDragStart(itemId: string) {
    setDraggingId(itemId);
    setDragOverId(itemId);
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>, itemId: string) {
    event.preventDefault();
    if (!draggingId || draggingId === itemId) return;
    setDragOverId(itemId);
  }

  function resetDragState() {
    setDraggingId(null);
    setDragOverId(null);
  }

  async function persistCourseUpdate({
    mode,
    allowStale,
  }: {
    mode: 'auto' | 'manual';
    allowStale?: boolean;
  }) {
    if (!normalizedDraft.title) {
      return;
    }
    setSavingEdits(true);
    setEditError(null);
    if (mode === 'auto') {
      setAutoSaveState('saving');
      setAutoSaveMessage('Saving…');
    }
    try {
      const updated = await updateCourse(menuId, course.id, {
        title: normalizedDraft.title,
        description: normalizedDraft.description ? normalizedDraft.description : null,
        intent: normalizedDraft.intent ? normalizedDraft.intent : null,
        expectedUpdatedAt: allowStale ? undefined : lastSaved.updatedAt,
      });
      onCourseUpdated(updated);
      setLastSaved({
        title: updated.title,
        description: updated.description ?? '',
        intent: updated.intent ?? '',
        updatedAt: updated.updated_at,
      });
      setAutoSaveState('saved');
      setAutoSaveMessage(mode === 'auto' ? 'Autosaved just now.' : 'Changes saved.');
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setAutoSaveState('conflict');
        setAutoSaveMessage(err.message);
      } else {
        const message = err instanceof Error ? err.message : 'Failed to update course.';
        setEditError(message);
        setAutoSaveState('error');
        setAutoSaveMessage(message);
      }
    } finally {
      setSavingEdits(false);
    }
  }

  function handleCourseCancel() {
    setDraftTitle(lastSaved.title);
    setDraftDescription(lastSaved.description);
    setDraftIntent(lastSaved.intent);
    setEditError(null);
    setAutoSaveState('idle');
    setAutoSaveMessage(null);
    setEditing(false);
  }

  async function handleConflictReload() {
    setAutoSaveState('idle');
    setAutoSaveMessage(null);
    setEditError(null);
    setEditing(false);
    await onRefresh();
    setEditing(true);
  }

  async function handleDrop(targetId: string) {
    if (!draggingId || draggingId === targetId) {
      resetDragState();
      return;
    }
    const reordered = reorderItemsLocally(course.items, draggingId, targetId);
    if (!reordered) {
      resetDragState();
      return;
    }
    resetDragState();
    await persistReorder(reordered);
  }

  async function persistReorder(nextItems: CourseItem[]) {
    setOrderError(null);
    // Optimistically update order while persisting to the backend.
    onCourseUpdated({ ...course, items: nextItems });
    setReordering(true);
    try {
      const refreshed = await reorderCourseItems(
        menuId,
        course.id,
        nextItems.map((item) => item.id)
      );
      onCourseUpdated(refreshed);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update order.';
      setOrderError(message);
      await onRefresh();
    } finally {
      setReordering(false);
    }
  }

  async function moveItem(itemId: string, direction: 'up' | 'down') {
    if (reordering) return;
    const currentIndex = course.items.findIndex((item) => item.id === itemId);
    if (currentIndex === -1) return;
    const targetIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
    if (targetIndex < 0 || targetIndex >= course.items.length) return;
    const updated = [...course.items];
    const [moved] = updated.splice(currentIndex, 1);
    updated.splice(targetIndex, 0, moved);
    await persistReorder(rebuildPositions(updated));
  }

  useEffect(() => {
    if (!editing || !isDraftDirty || savingEdits || autoSaveState === 'conflict') {
      return;
    }
    if (!normalizedDraft.title) {
      return;
    }
    const timer = setTimeout(() => {
      persistCourseUpdate({ mode: 'auto' });
    }, 1200);
    return () => clearTimeout(timer);
  }, [
    autoSaveState,
    editing,
    isDraftDirty,
    normalizedDraft.title,
    normalizedDraft.description,
    normalizedDraft.intent,
    savingEdits,
  ]);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">
            Position {course.position}
          </p>
          <h4 className="text-base font-semibold text-white">{course.title}</h4>
          {course.description && <p className="text-sm text-slate-200">{course.description}</p>}
          {course.intent && <p className="text-sm text-emerald-200">{course.intent}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setEditing((prev) => !prev)}
            className="text-xs font-semibold text-emerald-300 underline decoration-emerald-300/60"
          >
            {editing ? 'Close editor' : 'Edit course'}
          </button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="text-xs font-semibold text-slate-400 underline decoration-slate-500/60 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {deleting ? 'Removing…' : 'Delete course'}
          </button>
        </div>
      </div>

      {editing && (
        <div className="mt-4 space-y-3 rounded-lg border border-slate-800 bg-slate-950/70 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-400">Narrative details</p>
          <div className="space-y-2">
            <label className="text-xs text-slate-400" htmlFor={`course_edit_title_${course.id}`}>
              Title
            </label>
            <input
              id={`course_edit_title_${course.id}`}
              type="text"
              value={draftTitle}
              onChange={(e) => setDraftTitle(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-slate-400" htmlFor={`course_edit_desc_${course.id}`}>
              Description
            </label>
            <textarea
              id={`course_edit_desc_${course.id}`}
              rows={2}
              value={draftDescription}
              onChange={(e) => setDraftDescription(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
              placeholder="Optional context for this course."
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-slate-400" htmlFor={`course_edit_intent_${course.id}`}>
              Intent
            </label>
            <textarea
              id={`course_edit_intent_${course.id}`}
              rows={2}
              value={draftIntent}
              onChange={(e) => setDraftIntent(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
              placeholder="Why this course matters in the overall story."
            />
          </div>
          {editError && <p className="text-xs text-red-300">{editError}</p>}
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => persistCourseUpdate({ mode: 'manual' })}
              disabled={savingEdits || !normalizedDraft.title}
              className="rounded-lg bg-emerald-500 px-4 py-2 text-xs font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {savingEdits ? 'Saving…' : 'Save now'}
            </button>
            <button
              type="button"
              onClick={handleCourseCancel}
              className="text-xs font-semibold text-slate-400 underline decoration-slate-500/60"
            >
              Cancel
            </button>
          </div>
          {autoSaveMessage && (
            <p
              className={`text-xs ${
                autoSaveState === 'conflict' || autoSaveState === 'error'
                  ? 'text-amber-200'
                  : 'text-emerald-200'
              }`}
              role="status"
              aria-live="polite"
            >
              {autoSaveMessage}
            </p>
          )}
          {autoSaveState === 'conflict' && (
            <div className="flex flex-wrap gap-3 text-xs">
              <button
                type="button"
                onClick={handleConflictReload}
                className="rounded-lg border border-amber-300/40 px-3 py-1 text-amber-100"
              >
                Reload latest
              </button>
              <button
                type="button"
                onClick={() => persistCourseUpdate({ mode: 'manual', allowStale: true })}
                className="text-xs font-semibold text-amber-200 underline decoration-amber-200/60"
              >
                Save anyway
              </button>
            </div>
          )}
        </div>
      )}

      <div className="mt-4 space-y-3">
        <p className="text-xs uppercase tracking-wide text-slate-400">Items</p>
        {course.items.length === 0 ? (
          <p className="text-sm text-slate-300">
            Add an item via search/ingest or paste a known media ID to populate this course.
          </p>
        ) : (
          <p className="text-[11px] text-slate-500">
            Drag the handle or use the up/down buttons to reorder; changes save automatically.
          </p>
        )}
        {course.items.map((item, index) => (
          <CourseItemRow
            key={item.id}
            item={item}
            menuId={menuId}
            onRefresh={onRefresh}
            onItemRemoved={() => handleItemRemoved(item.id)}
            onItemUpdated={handleItemUpdated}
            onMove={moveItem}
            canMoveUp={index > 0}
            canMoveDown={index < course.items.length - 1}
            dragState={
              course.items.length > 1
                ? {
                    draggable: true,
                    isDragging: draggingId === item.id,
                    isDragOver: dragOverId === item.id && draggingId !== item.id,
                    onDragStart: () => handleDragStart(item.id),
                    onDragOver: (event) => handleDragOver(event, item.id),
                    onDrop: () => handleDrop(item.id),
                    onDragEnd: () => resetDragState(),
                  }
                : undefined
            }
          />
        ))}
      </div>

      <div className="mt-4 space-y-4 border-t border-slate-800 pt-4">
        <AddCourseItemForm course={course} menuId={menuId} onItemAdded={handleItemAdded} />
        <CourseItemSearch menuId={menuId} course={course} onAdded={handleItemAdded} />
      </div>

      {reordering && <p className="mt-3 text-xs text-emerald-300">Saving new order…</p>}
      {orderError && <p className="mt-3 text-xs text-red-300">{orderError}</p>}
      {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
    </div>
  );
}

type DragState = {
  draggable: boolean;
  isDragging: boolean;
  isDragOver: boolean;
  onDragStart: () => void;
  onDragOver: (event: DragEvent<HTMLDivElement>) => void;
  onDrop: () => void;
  onDragEnd: () => void;
};

function CourseItemRow({
  item,
  menuId,
  onRefresh,
  onItemRemoved,
  onItemUpdated,
  onMove,
  canMoveUp,
  canMoveDown,
  dragState,
}: {
  item: CourseItem;
  menuId: string;
  onRefresh: () => Promise<void>;
  onItemRemoved: () => void;
  onItemUpdated: (item: CourseItem) => void;
  onMove: (itemId: string, direction: 'up' | 'down') => void;
  canMoveUp: boolean;
  canMoveDown: boolean;
  dragState?: DragState;
}) {
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [notes, setNotes] = useState(item.notes ?? '');
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [autoSaveState, setAutoSaveState] = useState<
    'idle' | 'saving' | 'saved' | 'error' | 'conflict'
  >('idle');
  const [autoSaveMessage, setAutoSaveMessage] = useState<string | null>(null);
  const [lastSaved, setLastSaved] = useState({
    notes: item.notes ?? '',
    updatedAt: item.updated_at,
  });
  const normalizedNotes = useMemo(() => notes.trim(), [notes]);
  const normalizedLastSaved = useMemo(() => lastSaved.notes.trim(), [lastSaved.notes]);
  const isDirty = normalizedNotes !== normalizedLastSaved;

  useEffect(() => {
    const shouldSyncNotes = !editing || !isDirty;
    setLastSaved({ notes: item.notes ?? '', updatedAt: item.updated_at });
    if (shouldSyncNotes) {
      setNotes(item.notes ?? '');
    }
    setAutoSaveState('idle');
    setAutoSaveMessage(null);
  }, [editing, isDirty, item.notes, item.updated_at]);

  async function handleRemove() {
    setRemoving(true);
    setError(null);
    try {
      await deleteCourseItem(menuId, item.id);
      onItemRemoved();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete item.';
      setError(message);
    } finally {
      setRemoving(false);
    }
  }

  async function persistNotesUpdate({
    mode,
    allowStale,
  }: {
    mode: 'auto' | 'manual';
    allowStale?: boolean;
  }) {
    setSaving(true);
    setEditError(null);
    if (mode === 'auto') {
      setAutoSaveState('saving');
      setAutoSaveMessage('Saving…');
    }
    try {
      const updated = await updateCourseItem(menuId, item.id, {
        notes: normalizedNotes ? normalizedNotes : null,
        expectedUpdatedAt: allowStale ? undefined : lastSaved.updatedAt,
      });
      onItemUpdated(updated);
      setLastSaved({ notes: updated.notes ?? '', updatedAt: updated.updated_at });
      setAutoSaveState('saved');
      setAutoSaveMessage(mode === 'auto' ? 'Autosaved just now.' : 'Notes saved.');
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setAutoSaveState('conflict');
        setAutoSaveMessage(err.message);
      } else {
        const message = err instanceof Error ? err.message : 'Failed to update notes.';
        setEditError(message);
        setAutoSaveState('error');
        setAutoSaveMessage(message);
      }
    } finally {
      setSaving(false);
    }
  }

  function handleNotesCancel() {
    setNotes(lastSaved.notes);
    setEditError(null);
    setAutoSaveState('idle');
    setAutoSaveMessage(null);
    setEditing(false);
  }

  async function handleNotesReload() {
    setAutoSaveState('idle');
    setAutoSaveMessage(null);
    setEditError(null);
    setEditing(false);
    await onRefresh();
    setEditing(true);
  }

  useEffect(() => {
    if (!editing || !isDirty || saving || autoSaveState === 'conflict') {
      return;
    }
    const timer = setTimeout(() => {
      persistNotesUpdate({ mode: 'auto' });
    }, 900);
    return () => clearTimeout(timer);
  }, [autoSaveState, editing, isDirty, saving, normalizedNotes]);

  const dragClasses = dragState
    ? dragState.isDragging
      ? 'opacity-60 ring-2 ring-emerald-400/40'
      : dragState.isDragOver
        ? 'border-emerald-400/70 bg-slate-900'
        : ''
    : '';
  const formattedNotes = useMemo(() => (item.notes ? formatNotes(item.notes) : null), [item.notes]);

  return (
    <div
      className={`rounded-md border border-slate-800 bg-slate-900/70 p-3 transition ${dragClasses}`}
      onDragOver={(event) => {
        if (!dragState) return;
        dragState.onDragOver(event);
      }}
      onDrop={(event) => {
        if (!dragState) return;
        event.preventDefault();
        dragState.onDrop();
      }}
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex flex-col items-center gap-2">
            <button
              type="button"
              draggable={Boolean(dragState?.draggable)}
              onDragStart={(event) => {
                if (!dragState) return;
                dragState.onDragStart();
                event.dataTransfer.effectAllowed = 'move';
              }}
              onDragEnd={() => dragState?.onDragEnd()}
              disabled={!dragState?.draggable}
              className="rounded-md border border-slate-800 bg-slate-950 px-2 py-1 text-[10px] uppercase tracking-wide text-slate-300 hover:text-emerald-200 disabled:cursor-not-allowed disabled:opacity-40"
              aria-label="Drag to reorder"
              title="Drag to reorder"
            >
              Drag
            </button>
            <div className="flex flex-col gap-1">
              <button
                type="button"
                onClick={() => onMove(item.id, 'up')}
                disabled={!canMoveUp}
                className="rounded-md border border-slate-800 px-2 py-1 text-[10px] text-slate-300 hover:text-emerald-200 disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="Move item up"
              >
                Up
              </button>
              <button
                type="button"
                onClick={() => onMove(item.id, 'down')}
                disabled={!canMoveDown}
                className="rounded-md border border-slate-800 px-2 py-1 text-[10px] text-slate-300 hover:text-emerald-200 disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="Move item down"
              >
                Down
              </button>
            </div>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">
              Position {item.position}
            </p>
            <p className="text-sm font-semibold text-white">
              {item.media_item?.title || 'Untitled media'}{' '}
              <span className="text-xs text-slate-400">({item.media_item_id})</span>
            </p>
            {formattedNotes && (
              <div className="mt-2 space-y-1 text-xs text-slate-300">{formattedNotes}</div>
            )}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setEditing((prev) => !prev)}
            className="text-xs font-semibold text-emerald-300 underline decoration-emerald-300/60"
          >
            {editing ? 'Close notes' : 'Edit notes'}
          </button>
          <button
            onClick={handleRemove}
            disabled={removing}
            className="text-xs font-semibold text-slate-400 underline decoration-slate-500/60 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {removing ? 'Removing…' : 'Remove'}
          </button>
        </div>
      </div>
      {editing && (
        <div className="mt-3 space-y-2 rounded-lg border border-slate-800 bg-slate-950/70 p-3">
          <label className="text-xs text-slate-400" htmlFor={`item_notes_${item.id}`}>
            Annotation
          </label>
          <textarea
            id={`item_notes_${item.id}`}
            rows={2}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
            placeholder="Add a narrative note or pairing suggestion."
          />
          <p className="text-[10px] text-slate-500">
            Supports line breaks and bullets (start a line with &quot;-&quot;).
          </p>
          {editError && <p className="text-xs text-red-300">{editError}</p>}
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => persistNotesUpdate({ mode: 'manual' })}
              disabled={saving}
              className="rounded-lg bg-emerald-500 px-3 py-1 text-xs font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {saving ? 'Saving…' : 'Save now'}
            </button>
            <button
              type="button"
              onClick={handleNotesCancel}
              className="text-xs font-semibold text-slate-400 underline decoration-slate-500/60"
            >
              Cancel
            </button>
          </div>
          {autoSaveMessage && (
            <p
              className={`text-xs ${
                autoSaveState === 'conflict' || autoSaveState === 'error'
                  ? 'text-amber-200'
                  : 'text-emerald-200'
              }`}
              role="status"
              aria-live="polite"
            >
              {autoSaveMessage}
            </p>
          )}
          {autoSaveState === 'conflict' && (
            <div className="flex flex-wrap gap-3 text-xs">
              <button
                type="button"
                onClick={handleNotesReload}
                className="rounded-lg border border-amber-300/40 px-3 py-1 text-amber-100"
              >
                Reload latest
              </button>
              <button
                type="button"
                onClick={() => persistNotesUpdate({ mode: 'manual', allowStale: true })}
                className="text-xs font-semibold text-amber-200 underline decoration-amber-200/60"
              >
                Save anyway
              </button>
            </div>
          )}
        </div>
      )}
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
      is_public: isPublic,
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
      <p className="text-sm text-slate-200">
        Menus organize your recommended courses with ordered media.
      </p>

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
  onCourseAdded,
}: {
  menuId: string;
  nextPosition: number;
  onCourseAdded: (course: Course) => void;
}) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [intent, setIntent] = useState('');
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
      intent: intent || undefined,
      position,
    };

    try {
      const created = await createCourse(menuId, payload);
      onCourseAdded(created);
      setTitle('');
      setDescription('');
      setIntent('');
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
      <div className="mt-3 space-y-1">
        <label className="text-xs text-slate-400" htmlFor={`course_intent_${menuId}`}>
          Intent
        </label>
        <textarea
          id={`course_intent_${menuId}`}
          rows={2}
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
          placeholder="What should this course convey?"
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
  onItemAdded,
}: {
  course: Course;
  menuId: string;
  onItemAdded: (item: CourseItem) => void;
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
      notes: notes || undefined,
    };

    try {
      const created = await createCourseItem(menuId, course.id, payload);
      onItemAdded(created);
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
          Annotation
        </label>
        <textarea
          id={`item_notes_${course.id}`}
          rows={2}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white outline-none ring-emerald-400/50 focus:border-emerald-400/70 focus:ring-2"
          placeholder="Optional pairing notes or context."
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

function sortItemsByPosition(items: CourseItem[]) {
  return [...items].sort((a, b) => a.position - b.position);
}

function rebuildPositions(items: CourseItem[]) {
  return items.map((item, index) => ({ ...item, position: index + 1 }));
}

function reorderItemsLocally(items: CourseItem[], sourceId: string, targetId: string) {
  const currentIndex = items.findIndex((item) => item.id === sourceId);
  const targetIndex = items.findIndex((item) => item.id === targetId);
  if (currentIndex === -1 || targetIndex === -1) {
    return null;
  }
  const updated = [...items];
  const [moved] = updated.splice(currentIndex, 1);
  updated.splice(targetIndex, 0, moved);
  return rebuildPositions(updated);
}

function formatNotes(notes: string): ReactNode[] {
  const lines = notes.split(/\r?\n/);
  const blocks: ReactNode[] = [];
  let paragraphLines: string[] = [];
  let listItems: string[] = [];
  let blockIndex = 0;

  const flushParagraph = () => {
    if (paragraphLines.length === 0) return;
    blocks.push(
      <p key={`p-${blockIndex++}`} className="whitespace-pre-wrap">
        {paragraphLines.join('\n')}
      </p>
    );
    paragraphLines = [];
  };

  const flushList = () => {
    if (listItems.length === 0) return;
    blocks.push(
      <ul key={`ul-${blockIndex++}`} className="list-disc space-y-1 pl-4">
        {listItems.map((item, index) => (
          <li key={`li-${blockIndex}-${index}`}>{item}</li>
        ))}
      </ul>
    );
    listItems = [];
  };

  for (const line of lines) {
    const trimmed = line.trim();
    const listMatch = /^[-*]\s+(.+)$/.exec(trimmed);
    if (listMatch) {
      flushParagraph();
      listItems.push(listMatch[1]);
      continue;
    }
    if (!trimmed) {
      flushParagraph();
      flushList();
      continue;
    }
    if (listItems.length) {
      flushList();
    }
    paragraphLines.push(line);
  }

  flushParagraph();
  flushList();

  if (blocks.length === 0) {
    return [notes];
  }
  return blocks;
}
