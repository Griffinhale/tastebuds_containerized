// Draft menu page rendered from a share token.
import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';

import type { Course, CourseItem, Menu } from '../../../../lib/menus';
import { getDraftMenuByToken } from '../../../../lib/menus';
import { getAvailabilitySummary } from '../../../../lib/availability';
import type { AvailabilitySummaryItem } from '../../../../lib/availability';
import { ShareMenuActions } from '@/components/share-menu-actions';

type PageProps = {
  params: { token: string };
};

const appBaseUrl = process.env.NEXT_PUBLIC_APP_BASE_URL || 'http://localhost:3000';

async function loadDraft(token: string) {
  try {
    return await getDraftMenuByToken(token);
  } catch {
    notFound();
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const response = await loadDraft(params.token);
  const menu = response.menu;
  const totalItems = menu.courses.reduce((count, course) => count + course.items.length, 0);
  return {
    title: `${menu.title} · Tastebuds draft`,
    description:
      menu.description ||
      `A draft menu with ${menu.courses.length} courses and ${totalItems} featured picks.`,
  };
}

export default async function DraftMenuPage({ params }: PageProps) {
  const response = await loadDraft(params.token);
  const menu = response.menu;
  const totalItems = menu.courses.reduce((count, course) => count + course.items.length, 0);
  const shareUrl = buildShareUrl(params.token);
  const availability = await loadAvailability(menu);

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-12">
      <Link href="/menus" className="text-sm text-emerald-300 underline decoration-emerald-300/60">
        {'<- Back to menus'}
      </Link>

      <header className="space-y-3 rounded-2xl border border-slate-800 bg-slate-950/60 p-6 shadow-lg shadow-emerald-500/10">
        <p className="text-xs uppercase tracking-wide text-emerald-300">Draft menu</p>
        <h1 className="text-3xl font-semibold text-white">{menu.title}</h1>
        {menu.description && (
          <p className="text-base leading-relaxed text-slate-200">{menu.description}</p>
        )}
        <dl className="grid gap-4 border-t border-slate-800 pt-4 text-sm sm:grid-cols-3">
          <InfoItem label="Token" value={response.share_token_id.slice(0, 8)} />
          <InfoItem label="Courses" value={`${menu.courses.length}`} />
          <InfoItem label="Items" value={`${totalItems}`} />
        </dl>
        {response.share_token_expires_at && (
          <p className="text-xs text-slate-300">
            Expires {new Date(response.share_token_expires_at).toLocaleString()}
          </p>
        )}
      </header>

      <section className="space-y-4">
        {menu.courses.length === 0 ? (
          <p className="rounded-xl border border-slate-800 bg-slate-950/40 p-6 text-sm text-slate-300">
            This draft has no courses yet.
          </p>
        ) : (
          menu.courses.map((course) => (
            <CourseSection key={course.id} course={course} availability={availability} />
          ))
        )}
      </section>

      {menu.pairings && menu.pairings.length > 0 && <PairingsSection pairings={menu.pairings} />}

      <ShareMenuActions title={menu.title} shareUrl={shareUrl} />
    </main>
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
            {availability && availability.providers.length > 0 && (
              <p className="text-xs text-emerald-200">
                Available via {availability.providers.slice(0, 2).join(', ')}
                {availability.providers.length > 2 ? ` +${availability.providers.length - 2}` : ''}
              </p>
            )}
            {item.notes && (
              <p className="mt-2 text-xs text-emerald-200">Annotation: {item.notes}</p>
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

function InfoItem({ label, value }: { label: string; value: string }) {
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

function buildShareUrl(token: string) {
  const normalizedBase = appBaseUrl.endsWith('/') ? appBaseUrl.slice(0, -1) : appBaseUrl;
  return `${normalizedBase}/menus/draft/${token}`;
}
