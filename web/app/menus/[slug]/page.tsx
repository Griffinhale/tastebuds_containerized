import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { cache } from 'react';

import type { Course, CourseItem, Menu } from '../../../lib/menus';
import { getPublicMenuBySlug } from '../../../lib/menus';
import { ShareMenuActions } from '@/components/share-menu-actions';

type PageProps = {
  params: { slug: string };
};

const notFoundCopy = 'menu not found';
const appBaseUrl = process.env.NEXT_PUBLIC_APP_BASE_URL || 'http://localhost:3000';

const getMenuBySlug = cache(async (slug: string) => getPublicMenuBySlug(slug));

async function loadMenu(slug: string): Promise<Menu> {
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
    const totalItems = menu.courses.reduce(
      (count, course) => count + course.items.length,
      0,
    );
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
  const totalItems = menu.courses.reduce(
    (count, course) => count + course.items.length,
    0,
  );
  const shareUrl = buildShareUrl(menu.slug);

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-12">
      <Link
        href="/"
        className="text-sm text-emerald-300 underline decoration-emerald-300/60"
      >
        ← Back home
      </Link>

      <header className="space-y-3 rounded-2xl border border-slate-800 bg-slate-950/60 p-6 shadow-lg shadow-emerald-500/10">
        <p className="text-xs uppercase tracking-wide text-emerald-300">
          Public menu
        </p>
        <h1 className="text-3xl font-semibold text-white">{menu.title}</h1>
        {menu.description && (
          <p className="text-base leading-relaxed text-slate-200">
            {menu.description}
          </p>
        )}
        <dl className="grid gap-4 border-t border-slate-800 pt-4 text-sm sm:grid-cols-3">
          <InfoItem label="Slug" value={menu.slug} />
          <InfoItem
            label="Courses"
            value={`${menu.courses.length}`}
          />
          <InfoItem label="Items" value={`${totalItems}`} />
        </dl>
      </header>

      <section className="space-y-4">
        {menu.courses.length === 0 ? (
          <p className="rounded-xl border border-slate-800 bg-slate-950/40 p-6 text-sm text-slate-300">
            This menu is published but has no courses yet. Add courses via the
            dashboard to fill it out.
          </p>
        ) : (
          menu.courses.map((course) => (
            <CourseSection key={course.id} course={course} />
          ))
        )}
      </section>

      <ShareablePreview menu={menu} shareUrl={shareUrl} />
    </main>
  );
}

type PreviewItem = CourseItem & { coursePosition: number };

function ShareablePreview({ menu, shareUrl }: { menu: Menu; shareUrl: string }) {
  const previewItems = getPreviewItems(menu);
  return (
    <section className="space-y-4 rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-slate-950/80 via-slate-900/50 to-emerald-900/30 p-6 shadow-lg shadow-emerald-500/10">
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-wide text-emerald-200">
          Share-ready preview
        </p>
        <h2 className="text-2xl font-semibold text-white">
          Invite someone to browse this menu.
        </h2>
        <p className="text-sm text-emerald-100/80">
          We surface a preview of recent additions below and include metadata
          for social networks, so shared links look polished everywhere.
        </p>
      </div>

      {previewItems.length > 0 ? (
        <ul className="grid gap-3 sm:grid-cols-3">
          {previewItems.map((item) => (
            <li
              key={item.id}
              className="rounded-xl border border-white/10 bg-white/5 p-3"
            >
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
                  <p className="text-xs text-white/70">
                    {item.media_item.subtitle}
                  </p>
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

      <ShareMenuActions title={menu.title} shareUrl={shareUrl} />
    </section>
  );
}

function CourseSection({ course }: { course: Course }) {
  return (
    <article className="space-y-4 rounded-2xl border border-slate-800 bg-slate-950/40 p-6">
      <header className="space-y-1">
        <p className="text-xs uppercase tracking-wide text-slate-400">
          Course {course.position}
        </p>
        <h2 className="text-2xl font-semibold text-white">{course.title}</h2>
        {course.description && (
          <p className="text-sm text-slate-300">{course.description}</p>
        )}
      </header>

      {course.items.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-800 p-4 text-sm text-slate-400">
          No items yet. Once items are added they appear here automatically.
        </p>
      ) : (
        <ul className="space-y-3">
          {course.items.map((item) => (
            <CourseItemCard key={item.id} item={item} />
          ))}
        </ul>
      )}
    </article>
  );
}

function CourseItemCard({ item }: { item: CourseItem }) {
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
            <p className="text-sm font-semibold text-white">
              {media?.title || 'Untitled media'}
            </p>
            {media?.subtitle && (
              <p className="text-xs text-slate-400">{media.subtitle}</p>
            )}
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
            {item.notes && (
              <p className="mt-2 text-xs text-emerald-200">Notes: {item.notes}</p>
            )}
            {media?.description && (
              <p className="mt-2 text-xs leading-relaxed text-slate-300">
                {media.description}
              </p>
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

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-400">
        {label}
      </dt>
      <dd className="text-lg font-semibold text-white">{value}</dd>
    </div>
  );
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
  const normalizedBase = appBaseUrl.endsWith('/')
    ? appBaseUrl.slice(0, -1)
    : appBaseUrl;
  return `${normalizedBase}/menus/${slug}`;
}

function getPreviewItems(menu: Menu): PreviewItem[] {
  return menu.courses
    .flatMap((course) =>
      course.items.map((item) => ({
        ...item,
        coursePosition: course.position,
      })),
    )
    .slice(0, 3);
}
