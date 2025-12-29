'use client';

// Menu dashboard with local optimistic updates and drag-and-drop ordering.

import { DragEvent, FormEvent, ReactNode, useCallback, useEffect, useMemo, useState } from 'react';

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
  getMenuItemCount,
  listMenus,
  reorderCourseItems,
  updateCourse,
  updateCourseItem,
} from '../lib/menus';
import { ApiError } from '../lib/api';
import { CourseItemSearch } from './course-item-search';

export function MenuDashboard() {
  const [menus, setMenus] = useState<Menu[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [viewMode, setViewMode] = useState<'stacked' | 'sidebar'>('stacked');
  const [expandedMenus, setExpandedMenus] = useState<string[]>([]);
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);

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
    if (menus.length && !activeMenuId) {
      setActiveMenuId(menus[0].id);
    } else if (activeMenuId && !menus.find((menu) => menu.id === activeMenuId)) {
      setActiveMenuId(menus[0]?.id ?? null);
    }
  }, [activeMenuId, menus]);

  useEffect(() => {
    fetchMenus();
  }, [fetchMenus]);

  const statusText = useMemo(() => {
    if (loading) return 'Loading menus...';
    if (error) return error;
    if (!menus.length) return 'No menus yet. Create one to start adding courses.';
    return `Showing ${menus.length} menu${menus.length === 1 ? '' : 's'}.`;
  }, [menus, loading, error]);

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-emerald-300">Menus</p>
            <p className="text-sm text-slate-200">{statusText}</p>
            {lastUpdated && !loading && !error && (
              <p className="mt-1 text-xs text-slate-400">
                Last updated {lastUpdated.toLocaleTimeString()}
              </p>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {menus.length > 0 && (
              <ViewToggle
                value={viewMode}
                onChange={(mode) => {
                  setViewMode(mode);
                  if (mode === 'stacked') {
                    setExpandedMenus([]);
                  } else if (mode === 'sidebar' && menus.length) {
                    setActiveMenuId((current) => current ?? menus[0].id);
                  }
                }}
              />
            )}
            <button
              onClick={fetchMenus}
              disabled={loading}
              className="rounded-md border border-emerald-400/50 px-3 py-1 text-xs font-semibold text-emerald-200 transition hover:bg-emerald-500/10 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Refresh
            </button>
          </div>
        </div>

        {error && <p className="mt-4 text-sm text-red-300">{error}</p>}

        {!loading && !error && menus.length > 0 && (
          <>
            {viewMode === 'sidebar' ? (
              <SidebarMenuBrowser
                menus={menus}
                activeMenuId={activeMenuId}
                onSelect={(menuId) => setActiveMenuId(menuId)}
                onRefresh={(menuId) => refreshMenu(menuId)}
                onMenuMutate={(menuId, updater) => mutateMenu(menuId, updater)}
              />
            ) : (
              <StackedMenuList
                menus={menus}
                expandedMenus={expandedMenus}
                onToggle={(menuId) =>
                  setExpandedMenus((current) =>
                    current.includes(menuId)
                      ? current.filter((id) => id !== menuId)
                      : [...current, menuId]
                  )
                }
                onRefresh={(menuId) => refreshMenu(menuId)}
                onMenuMutate={(menuId, updater) => mutateMenu(menuId, updater)}
              />
            )}
          </>
        )}
      </section>

      <CreateMenuForm
        onCreated={(menu) => {
          setMenus((prev) => [menu, ...prev]);
          setActiveMenuId(menu.id);
          setError(null);
          setLastUpdated(new Date());
        }}
      />
    </div>
  );
}

function ViewToggle({
  value,
  onChange,
}: {
  value: 'stacked' | 'sidebar';
  onChange: (mode: 'stacked' | 'sidebar') => void;
}) {
  return (
    <div className="flex items-center gap-2 rounded-full border border-slate-800 bg-slate-950/60 p-1 text-xs">
      <button
        type="button"
        onClick={() => onChange('stacked')}
        className={`rounded-full px-3 py-1 font-semibold transition ${
          value === 'stacked'
            ? 'bg-emerald-500/20 text-emerald-100'
            : 'text-slate-300 hover:text-emerald-100'
        }`}
      >
        Stacked
      </button>
      <button
        type="button"
        onClick={() => onChange('sidebar')}
        className={`rounded-full px-3 py-1 font-semibold transition ${
          value === 'sidebar'
            ? 'bg-emerald-500/20 text-emerald-100'
            : 'text-slate-300 hover:text-emerald-100'
        }`}
      >
        Sidebar
      </button>
    </div>
  );
}

function StackedMenuList({
  menus,
  expandedMenus,
  onToggle,
  onRefresh,
  onMenuMutate,
}: {
  menus: Menu[];
  expandedMenus: string[];
  onToggle: (menuId: string) => void;
  onRefresh: (menuId: string) => Promise<void>;
  onMenuMutate: (menuId: string, updater: (menu: Menu) => Menu) => void;
}) {
  return (
    <ul className="mt-4 space-y-3">
      {menus.map((menu) => (
        <MenuAccordionCard
          key={menu.id}
          menu={menu}
          expanded={expandedMenus.includes(menu.id)}
          onToggle={() => onToggle(menu.id)}
          onRefresh={() => onRefresh(menu.id)}
          onMenuMutate={(updater) => onMenuMutate(menu.id, updater)}
        />
      ))}
    </ul>
  );
}

function MenuAccordionCard({
  menu,
  expanded,
  onToggle,
  onRefresh,
  onMenuMutate,
}: {
  menu: Menu;
  expanded: boolean;
  onToggle: () => void;
  onRefresh: () => Promise<void>;
  onMenuMutate: (updater: (menu: Menu) => Menu) => void;
}) {
  const courseCount = menu.courses.length || 0;
  const itemCount = getMenuItemCount(menu);

  return (
    <li className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 shadow-sm shadow-emerald-500/5">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-start justify-between gap-3 text-left"
        aria-expanded={expanded}
      >
        <div className="flex items-start gap-3">
          <ChevronIcon expanded={expanded} />
          <div className="space-y-1">
            <p className="text-[11px] uppercase tracking-wide text-slate-400">Menu</p>
            <h3 className="text-lg font-semibold text-white">{menu.title}</h3>
            {menu.description && (
              <p className="text-sm text-slate-300 line-clamp-2">{menu.description}</p>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end text-xs text-slate-400">
          <span>
            {courseCount} course{courseCount === 1 ? '' : 's'}
          </span>
          <span>{itemCount} items</span>
        </div>
      </button>

      {expanded && (
        <div className="mt-4 border-t border-slate-800 pt-4">
          <MenuCoursesSection menu={menu} onRefresh={onRefresh} onMenuMutate={onMenuMutate} />
        </div>
      )}
    </li>
  );
}

function SidebarMenuBrowser({
  menus,
  activeMenuId,
  onSelect,
  onRefresh,
  onMenuMutate,
}: {
  menus: Menu[];
  activeMenuId: string | null;
  onSelect: (menuId: string) => void;
  onRefresh: (menuId: string) => Promise<void>;
  onMenuMutate: (menuId: string, updater: (menu: Menu) => Menu) => void;
}) {
  const activeMenu = menus.find((menu) => menu.id === activeMenuId);

  return (
    <div className="mt-4 grid gap-4 lg:grid-cols-[260px,1fr]">
      <aside className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
        <p className="text-xs uppercase tracking-wide text-slate-400">Menus</p>
        <div className="mt-3 space-y-2">
          {menus.map((menu) => {
            const isActive = menu.id === activeMenuId;
            return (
              <button
                key={menu.id}
                type="button"
                onClick={() => onSelect(menu.id)}
                className={`flex w-full flex-col items-start rounded-lg border px-3 py-2 text-left transition ${
                  isActive
                    ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-100'
                    : 'border-slate-800 bg-slate-950/60 text-slate-200 hover:border-slate-700'
                }`}
              >
                <span className="text-sm font-semibold">{menu.title}</span>
                <span className="text-[11px] text-slate-400">
                  {menu.courses.length} course{menu.courses.length === 1 ? '' : 's'} ·{' '}
                  {getMenuItemCount(menu)} items
                </span>
              </button>
            );
          })}
        </div>
      </aside>
      <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
        {activeMenu ? (
          <>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <p className="text-[11px] uppercase tracking-wide text-slate-400">Menu</p>
                <h3 className="text-xl font-semibold text-white">{activeMenu.title}</h3>
                {activeMenu.description && (
                  <p className="text-sm text-slate-300">{activeMenu.description}</p>
                )}
              </div>
              <div className="text-xs text-slate-400">
                {activeMenu.courses.length} course{activeMenu.courses.length === 1 ? '' : 's'} ·{' '}
                {getMenuItemCount(activeMenu)} items
              </div>
            </div>
            <div className="mt-4 border-t border-slate-800 pt-4">
              <MenuCoursesSection
                menu={activeMenu}
                onRefresh={() => onRefresh(activeMenu.id)}
                onMenuMutate={(updater) => onMenuMutate(activeMenu.id, updater)}
              />
            </div>
          </>
        ) : (
          <p className="text-sm text-slate-300">Select a menu to view its courses.</p>
        )}
      </div>
    </div>
  );
}

function MenuCoursesSection({
  menu,
  onRefresh,
  onMenuMutate,
}: {
  menu: Menu;
  onRefresh: () => Promise<void>;
  onMenuMutate: (updater: (menu: Menu) => Menu) => void;
}) {
  const [showAddCourse, setShowAddCourse] = useState(false);

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
      setShowAddCourse(false);
    },
    [onMenuMutate]
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-emerald-300">Courses</p>
          <p className="text-sm text-slate-300">
            Focus on ordering and annotations without leaving this view.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setShowAddCourse((prev) => !prev)}
            className="rounded-md border border-emerald-500/50 px-3 py-1 text-xs font-semibold text-emerald-100 transition hover:bg-emerald-500/10"
          >
            {showAddCourse ? 'Close add course' : 'Add course'}
          </button>
          <button
            type="button"
            onClick={onRefresh}
            className="rounded-md border border-slate-700 px-3 py-1 text-xs font-semibold text-slate-200 transition hover:border-emerald-400/70 hover:text-emerald-100"
          >
            Refresh menu
          </button>
        </div>
      </div>

      {menu.courses.length === 0 && (
        <p className="text-sm text-slate-300">
          No courses yet. Select &quot;Add course&quot; to start building this menu.
        </p>
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

      {showAddCourse && (
        <AddCourseForm
          menuId={menu.id}
          nextPosition={menu.courses.length + 1}
          onCourseAdded={handleCourseAdded}
        />
      )}
    </div>
  );
}

function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <span
      className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-full border border-slate-800 bg-slate-900 text-emerald-200"
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 20 20"
        className={`h-3 w-3 transition ${expanded ? 'rotate-180' : ''}`}
        fill="currentColor"
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          clipRule="evenodd"
          d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
        />
      </svg>
    </span>
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
  const [addMode, setAddMode] = useState<'search' | 'id'>('search');
  const [addPanelOpen, setAddPanelOpen] = useState(false);
  const [lastSaved, setLastSaved] = useState({
    title: course.title,
    description: course.description ?? '',
    intent: course.intent ?? '',
    updatedAt: course.updated_at,
  });
  const openAddPanel = (mode: 'search' | 'id') => {
    setAddMode(mode);
    setAddPanelOpen(true);
  };
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
          {editing && <AutoSaveBadge state={autoSaveState} message={autoSaveMessage} />}
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
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs uppercase tracking-wide text-slate-400">Items</p>
        </div>
        {course.items.length === 0 ? (
          <p className="text-sm text-slate-300">No items yet.</p>
        ) : (
          <p className="text-[11px] text-slate-500">Drag to reorder; changes save automatically.</p>
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
        {!addPanelOpen ? (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-950/70 p-4">
            <div>
              <p className="text-sm font-semibold text-emerald-300">Add items</p>
              <p className="text-xs text-slate-300">
                Search or paste an ID when you&apos;re ready.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => openAddPanel('search')}
                className="rounded-full bg-emerald-500 px-3 py-1 text-[11px] font-semibold text-slate-950 transition hover:bg-emerald-400"
              >
                Add item
              </button>
              <button
                type="button"
                onClick={() => openAddPanel('id')}
                className="rounded-full border border-slate-800 px-3 py-1 text-[11px] font-semibold text-slate-300 transition hover:border-slate-700"
              >
                Quick add ID
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-950/70 p-3">
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setAddMode('search')}
                  className={`rounded-full border px-3 py-1 text-[11px] font-semibold ${
                    addMode === 'search'
                      ? 'border-emerald-500/60 bg-emerald-500/10 text-emerald-200'
                      : 'border-slate-800 text-slate-300'
                  }`}
                >
                  Search & ingest
                </button>
                <button
                  type="button"
                  onClick={() => setAddMode('id')}
                  className={`rounded-full border px-3 py-1 text-[11px] font-semibold ${
                    addMode === 'id'
                      ? 'border-emerald-500/60 bg-emerald-500/10 text-emerald-200'
                      : 'border-slate-800 text-slate-300'
                  }`}
                >
                  Quick add ID
                </button>
              </div>
              <button
                type="button"
                onClick={() => setAddPanelOpen(false)}
                className="text-xs font-semibold text-slate-400 underline decoration-slate-600 decoration-dotted"
              >
                Done adding
              </button>
            </div>
            {addMode === 'id' ? (
              <AddCourseItemForm course={course} menuId={menuId} onItemAdded={handleItemAdded} />
            ) : (
              <CourseItemSearch menuId={menuId} course={course} onAdded={handleItemAdded} />
            )}
          </>
        )}
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
          {editing && <AutoSaveBadge state={autoSaveState} message={autoSaveMessage} />}
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

function AutoSaveBadge({
  state,
  message,
}: {
  state: 'idle' | 'saving' | 'saved' | 'error' | 'conflict';
  message?: string | null;
}) {
  const label =
    state === 'saving'
      ? 'Autosaving...'
      : state === 'saved'
        ? 'Saved'
        : state === 'conflict'
          ? 'Conflict'
          : state === 'error'
            ? 'Save failed'
            : 'Autosave';
  const toneClass =
    state === 'conflict' || state === 'error'
      ? 'border-amber-400/40 bg-amber-500/10 text-amber-100'
      : state === 'saved'
        ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-100'
        : 'border-slate-800 bg-slate-900 text-slate-300';
  return (
    <span
      className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-wide ${toneClass}`}
      title={message || label}
    >
      {label}
    </span>
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
