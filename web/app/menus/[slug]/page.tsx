// Public menu page with share metadata and preview tiles.
import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { cache } from 'react';

import type { Course, CourseItem, Menu } from '../../../lib/menus';
import { getPublicMenuBySlug, getPublicMenuLineage } from '../../../lib/menus';
import type { AvailabilitySummaryItem } from '../../../lib/availability';
import { getAvailabilitySummary } from '../../../lib/availability';
import { ForkMenuActions } from '@/components/fork-menu-actions';
import { ShareMenuActions } from '@/components/share-menu-actions';

type PageProps = {
  params: { slug: string };
};

const notFoundCopy = 'menu not found';
const appBaseUrl = process.env.NEXT_PUBLIC_APP_BASE_URL || 'http://localhost:3000';

// Cache the fetch to reuse in metadata + page rendering.
const getMenuBySlug = cache(async (slug: string) => getPublicMenuBySlug(slug));

async function loadMenu(slug: string): Promise<Menu> {
  // Translate 404-style errors into Next.js notFound responses.
  try {
    return await getMenuBySlug(slug);
  } catch (err) {
    const message = err instanceof Error ? err.message.toLowerCase() : '';
    if (message.includes(notFoundCopy) || message.includes('404')) {
      notFound();
    }
    throw err;
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  try {
    const menu = await getMenuBySlug(params.slug);
    const totalItems = menu.courses.reduce((count, course) => count + course.items.length, 0);
    const shareUrl = buildShareUrl(menu.slug);
    const description =
      menu.description ||
      `A ${menu.courses.length}-course menu with ${totalItems} featured picks on Tastebuds.`;
    const imageCandidates = collectPreviewImages(menu);

    return {
      title: `${menu.title} · Tastebuds`,
      description,
      alternates: {
        canonical: shareUrl,
      },
      openGraph: {
        type: 'article',
        url: shareUrl,
        title: `${menu.title} · Tastebuds`,
        description,
        images: imageCandidates.length
          ? imageCandidates.map((url) => ({
              url,
              alt: menu.title,
            }))
          : undefined,
      },
      twitter: {
        card: imageCandidates.length ? 'summary_large_image' : 'summary',
        title: `${menu.title} · Tastebuds`,
        description,
        images: imageCandidates.length ? imageCandidates : undefined,
      },
    };
  } catch {
    return {
      title: 'Menu not found · Tastebuds',
      description: 'This menu is not published or no longer exists.',
      alternates: {
        canonical: buildShareUrl(params.slug),
      },
    };
  }
}

export default async function PublicMenuPage({ params }: PageProps) {
  const menu = await loadMenu(params.slug);
  const totalItems = menu.courses.reduce((count, course) => count + course.items.length, 0);
  const shareUrl = buildShareUrl(menu.slug);
  const availability = await loadAvailability(menu);
  const lineage = await loadLineage(menu.slug);

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-12">
      <Link href="/" className="text-sm text-emerald-300 underline decoration-emerald-300/60">
        {'<- Back home'}
      </Link>

      <header className="space-y-3 rounded-2xl border border-slate-800 bg-slate-950/60 p-6 shadow-lg shadow-emerald-500/10">
        <p className="text-xs uppercase tracking-wide text-emerald-300">Public menu</p>
        <h1 className="text-3xl font-semibold text-white">{menu.title}</h1>
        {menu.description && (
          <p className="text-base leading-relaxed text-slate-200">{menu.description}</p>
        )}
        <dl className="grid gap-4 border-t border-slate-800 pt-4 text-sm sm:grid-cols-3">
          <InfoItem label="Slug" value={menu.slug} />
          <InfoItem label="Courses" value={`${menu.courses.length}`} />
          <InfoItem label="Items" value={`${totalItems}`} />
        </dl>
        {lineage && <LineagePanel lineage={lineage} />}
      </header>

      <section className="grid gap-4 lg:grid-cols-[1.1fr,0.9fr]">
        <div className="rounded-2xl border border-emerald-500/30 bg-slate-950/60 p-6">
          <p className="text-xs uppercase tracking-wide text-emerald-200">Share & export</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">
            Share the menu or make it yours.
          </h2>
          <p className="mt-2 text-sm text-slate-200">
            Copy the public link, open it in Tastebuds, or connect integrations to export.
          </p>
          <div className="mt-4">
            <ShareMenuActions
              title={menu.title}
              shareUrl={shareUrl}
              ctaLabel="Open in Tastebuds"
              ctaHref="/menus"
            />
          </div>
          <p className="mt-3 text-xs text-slate-400">
            Want Spotify export or Jellyfin sync?{' '}
            <Link
              href="/account#integrations"
              className="text-emerald-300 underline decoration-emerald-300/60"
            >
              Connect integrations
            </Link>
            .
          </p>
        </div>
        <ForkMenuActions menuId={menu.id} menuTitle={menu.title} />
      </section>

      <section className="space-y-4">
        {menu.courses.length === 0 ? (
          <p className="rounded-xl border border-slate-800 bg-slate-950/40 p-6 text-sm text-slate-300">
            This menu is published but has no courses yet. Add courses via the dashboard to fill it
            out.
          </p>
        ) : (
          menu.courses.map((course) => (
            <CourseSection key={course.id} course={course} availability={availability} />
          ))
        )}
      </section>

      {menu.pairings && menu.pairings.length > 0 && <PairingsSection pairings={menu.pairings} />}

      <ShareablePreview menu={menu} />
    </main>
  );
}

type PreviewItem = CourseItem & { coursePosition: number };

function ShareablePreview({ menu }: { menu: Menu }) {
  const previewItems = getPreviewItems(menu);
  return (
    <section className="space-y-4 rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-slate-950/80 via-slate-900/50 to-emerald-900/30 p-6 shadow-lg shadow-emerald-500/10">
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-wide text-emerald-200">Share-ready preview</p>
        <h2 className="text-2xl font-semibold text-white">Invite someone to browse this menu.</h2>
        <p className="text-sm text-emerald-100/80">
          We surface a preview of recent additions below and include metadata for social networks,
          so shared links look polished everywhere.
        </p>
      </div>

      {previewItems.length > 0 ? (
        <ul className="grid gap-3 sm:grid-cols-3">
          {previewItems.map((item) => (
            <li key={item.id} className="rounded-xl border border-white/10 bg-white/5 p-3">
              {item.media_item?.cover_image_url ? (
                <img
                  src={item.media_item.cover_image_url}
                  alt={item.media_item.title || 'Menu item'}
                  className="h-32 w-full rounded-lg object-cover"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <div className="flex h-32 w-full items-center justify-center rounded-lg border border-dashed border-white/20 text-xs uppercase tracking-wide text-white/50">
                  No artwork yet
                </div>
              )}
              <div className="mt-3 space-y-1">
                <p className="text-[10px] uppercase tracking-wide text-white/70">
                  Course {item.coursePosition}
                </p>
                <p className="text-sm font-semibold text-white">
                  {item.media_item?.title || 'Untitled media'}
                </p>
                {item.media_item?.subtitle && (
                  <p className="text-xs text-white/70">{item.media_item.subtitle}</p>
                )}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="rounded-lg border border-dashed border-white/20 bg-slate-950/40 p-4 text-sm text-white/80">
          Items appear here once you add content to any course.
        </p>
      )}
    </section>
  );
}

function CourseSection({
  course,
  availability,
}: {
  course: Course;
  availability: Record<string, AvailabilitySummaryItem>;
}) {
  return (
    <article className="space-y-4 rounded-2xl border border-slate-800 bg-slate-950/40 p-6">
      <header className="space-y-1">
        <p className="text-xs uppercase tracking-wide text-slate-400">Course {course.position}</p>
        <h2 className="text-2xl font-semibold text-white">{course.title}</h2>
        {course.description && <p className="text-sm text-slate-300">{course.description}</p>}
        {course.intent && <p className="text-sm text-emerald-200">{course.intent}</p>}
      </header>

      {course.items.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-800 p-4 text-sm text-slate-400">
          No items yet. Once items are added they appear here automatically.
        </p>
      ) : (
        <ul className="space-y-3">
          {course.items.map((item) => (
            <CourseItemCard
              key={item.id}
              item={item}
              availability={availability[item.media_item_id]}
            />
          ))}
        </ul>
      )}
    </article>
  );
}

function CourseItemCard({
  item,
  availability,
}: {
  item: CourseItem;
  availability?: AvailabilitySummaryItem;
}) {
  const media = item.media_item;

  return (
    <li className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-4">
          <div className="h-20 w-14 overflow-hidden rounded border border-slate-800 bg-slate-900">
            {media?.cover_image_url ? (
              <img
                src={media.cover_image_url}
                alt={media.title}
                className="h-full w-full object-cover"
                referrerPolicy="no-referrer"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-[10px] uppercase tracking-wide text-slate-500">
                No art
              </div>
            )}
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">
              Position {item.position}
            </p>
            <p className="text-sm font-semibold text-white">{media?.title || 'Untitled media'}</p>
            {media?.subtitle && <p className="text-xs text-slate-400">{media.subtitle}</p>}
            {media?.release_date && (
              <p className="text-xs text-slate-500">
                Released{' '}
                {new Date(media.release_date).toLocaleDateString(undefined, {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                })}
              </p>
            )}
            <AvailabilityChips availability={availability} />
            {item.notes && (
              <p className="mt-2 text-xs text-emerald-200 whitespace-pre-wrap">{item.notes}</p>
            )}
            {media?.description && (
              <p className="mt-2 text-xs leading-relaxed text-slate-300">{media.description}</p>
            )}
          </div>
        </div>
        {media?.canonical_url && (
          <a
            href={media.canonical_url}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-emerald-300 underline decoration-emerald-300/60"
          >
            View source
          </a>
        )}
      </div>
    </li>
  );
}

function InfoItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-400">{label}</dt>
      <dd className="text-lg font-semibold text-white">{value}</dd>
    </div>
  );
}

function PairingsSection({ pairings }: { pairings: Menu['pairings'] }) {
  if (!pairings || pairings.length === 0) return null;
  return (
    <section className="space-y-4 rounded-2xl border border-emerald-500/30 bg-slate-950/60 p-6">
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-wide text-emerald-200">Story pairings</p>
        <h2 className="text-2xl font-semibold text-white">Narrative links across courses.</h2>
        <p className="text-sm text-emerald-100/80">
          These pairings highlight why two items belong together.
        </p>
      </div>
      <ul className="space-y-3">
        {pairings.map((pairing) => (
          <li key={pairing.id} className="rounded-xl border border-white/10 bg-white/5 p-3">
            <p className="text-sm font-semibold text-white">
              {pairing.primary_item?.media_item?.title || 'Untitled'} {' <-> '}
              {pairing.paired_item?.media_item?.title || 'Untitled'}
            </p>
            {pairing.relationship && (
              <p className="text-xs uppercase tracking-wide text-emerald-200">
                {pairing.relationship}
              </p>
            )}
            {pairing.note && <p className="text-xs text-slate-200">{pairing.note}</p>}
          </li>
        ))}
      </ul>
    </section>
  );
}

function LineagePanel({ lineage }: { lineage: Awaited<ReturnType<typeof loadLineage>> }) {
  if (!lineage) return null;
  return (
    <div className="mt-4 rounded-xl border border-emerald-500/20 bg-slate-950/50 p-4 text-sm text-slate-200">
      <p className="text-xs uppercase tracking-wide text-emerald-200">Lineage</p>
      {lineage.source_menu?.menu && (
        <p className="mt-2">
          Forked from{' '}
          {lineage.source_menu.menu.is_public ? (
            <Link
              href={`/menus/${lineage.source_menu.menu.slug}`}
              className="font-semibold text-emerald-200 underline decoration-emerald-300/60"
            >
              {lineage.source_menu.menu.title}
            </Link>
          ) : (
            <span className="font-semibold text-emerald-200">{lineage.source_menu.menu.title}</span>
          )}
          {lineage.source_menu.note ? ` - ${lineage.source_menu.note}` : ''}
        </p>
      )}
      <p className="mt-2 text-xs text-slate-300">Forks: {lineage.fork_count}</p>
      {lineage.forked_menus?.length ? (
        <div className="mt-3 space-y-1 text-xs text-slate-300">
          <p className="uppercase tracking-wide text-slate-400">Recent forks</p>
          <div className="flex flex-wrap gap-2">
            {lineage.forked_menus.slice(0, 4).map((fork) =>
              fork.is_public ? (
                <Link
                  key={fork.id}
                  href={`/menus/${fork.slug}`}
                  className="rounded-full border border-slate-800 px-3 py-1 text-[11px] text-emerald-200"
                >
                  {fork.title}
                </Link>
              ) : (
                <span
                  key={fork.id}
                  className="rounded-full border border-slate-800 px-3 py-1 text-[11px]"
                >
                  {fork.title}
                </span>
              )
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function AvailabilityChips({ availability }: { availability?: AvailabilitySummaryItem }) {
  if (!availability) return null;
  const providers = availability.providers ?? [];
  const availableCount = availability.status_counts?.available ?? 0;
  const providerLabel =
    providers.slice(0, 3).join(', ') + (providers.length > 3 ? ` +${providers.length - 3}` : '');
  const statusLabel = availableCount > 0 ? `${availableCount} available` : 'Availability unknown';
  return (
    <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-emerald-100">
      <span className="rounded-full border border-emerald-400/40 bg-emerald-500/10 px-2 py-0.5">
        {statusLabel}
      </span>
      {providerLabel && (
        <span className="rounded-full border border-slate-800 px-2 py-0.5 text-slate-300">
          {providerLabel}
        </span>
      )}
      {availability.last_checked_at && (
        <span className="text-slate-500">
          Checked {new Date(availability.last_checked_at).toLocaleDateString()}
        </span>
      )}
    </div>
  );
}

async function loadAvailability(menu: Menu) {
  const mediaItemIds = Array.from(
    new Set(menu.courses.flatMap((course) => course.items.map((item) => item.media_item_id)))
  );
  if (!mediaItemIds.length) return {};
  try {
    const summaries = await getAvailabilitySummary(mediaItemIds, { isServer: true });
    return summaries.reduce<Record<string, AvailabilitySummaryItem>>((acc, item) => {
      acc[item.media_item_id] = item;
      return acc;
    }, {});
  } catch {
    return {};
  }
}

async function loadLineage(slug: string) {
  try {
    return await getPublicMenuLineage(slug);
  } catch {
    return null;
  }
}

function collectPreviewImages(menu: Menu) {
  const covers: string[] = [];
  menu.courses.forEach((course) => {
    course.items.forEach((item) => {
      if (item.media_item?.cover_image_url) {
        covers.push(item.media_item.cover_image_url);
      }
    });
  });
  return covers.slice(0, 4);
}

function buildShareUrl(slug: string) {
  // Normalize base URL to avoid accidental double slashes.
  const normalizedBase = appBaseUrl.endsWith('/') ? appBaseUrl.slice(0, -1) : appBaseUrl;
  return `${normalizedBase}/menus/${slug}`;
}

function getPreviewItems(menu: Menu): PreviewItem[] {
  return menu.courses
    .flatMap((course) =>
      course.items.map((item) => ({
        ...item,
        coursePosition: course.position,
      }))
    )
    .slice(0, 3);
}
