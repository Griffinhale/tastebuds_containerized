// Media detail page (base fields + source list).
import Link from 'next/link';
import { notFound } from 'next/navigation';

import { ApiError } from '../../../lib/api';
import { getMediaAvailability } from '../../../lib/availability';
import { buildTypeFields } from '../../../lib/media-detail';
import { getMediaDetail } from '../../../lib/media';

type MediaDetailPageProps = {
  params: {
    id: string;
  };
};

const availabilityTone = (status: string) => {
  if (status === 'available') {
    return 'border-emerald-400/50 bg-emerald-500/10 text-emerald-100';
  }
  if (status === 'unavailable') {
    return 'border-rose-400/50 bg-rose-500/10 text-rose-100';
  }
  return 'border-amber-400/50 bg-amber-500/10 text-amber-100';
};

const availabilityLabel = (status: string) => {
  if (status === 'available') return 'Available';
  if (status === 'unavailable') return 'Unavailable';
  return 'Unknown';
};

export default async function MediaDetailPage({ params }: MediaDetailPageProps) {
  let media;
  try {
    media = await getMediaDetail(params.id, { isServer: true });
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      notFound();
    }
    throw err;
  }

  const availability = await getMediaAvailability(params.id, { isServer: true });

  const releaseDate = media.release_date ? new Date(media.release_date).toLocaleDateString() : null;
  const detailFields = buildTypeFields(media);

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-12">
      <Link href="/" className="text-sm text-emerald-300 underline decoration-emerald-300/60">
        &lt;- Back home
      </Link>

      <section className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
        <div className="flex flex-col gap-6 md:flex-row">
          <div className="h-44 w-32 overflow-hidden rounded-lg border border-slate-800 bg-slate-900">
            {media.cover_image_url ? (
              <img
                src={media.cover_image_url}
                alt={media.title}
                className="h-full w-full object-cover"
                referrerPolicy="no-referrer"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-xs uppercase tracking-wide text-slate-500">
                No art
              </div>
            )}
          </div>
          <div className="space-y-3">
            <div className="space-y-1">
              <p className="text-xs uppercase tracking-wide text-emerald-200">{media.media_type}</p>
              <h1 className="text-3xl font-semibold text-white">{media.title}</h1>
              {media.subtitle && <p className="text-sm text-slate-300">{media.subtitle}</p>}
            </div>
            {media.description && (
              <p className="text-sm leading-relaxed text-slate-200">{media.description}</p>
            )}
            <div className="flex flex-wrap gap-3 text-xs text-slate-300">
              {releaseDate && <span>Release date: {releaseDate}</span>}
              <span>Sources: {media.sources.length}</span>
              <span>
                Availability:{' '}
                {availability.length ? `${availability.length} listings` : 'Not tracked'}
              </span>
            </div>
            {media.canonical_url && (
              <a
                href={media.canonical_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex text-xs font-semibold text-emerald-200 underline decoration-emerald-200/60"
              >
                View canonical source
              </a>
            )}
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
        <header className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-emerald-200">Format details</p>
          <h2 className="text-lg font-semibold text-white">What makes this unique</h2>
        </header>
        {detailFields.length === 0 ? (
          <p className="mt-3 text-sm text-slate-400">No extra details captured yet.</p>
        ) : (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {detailFields.map((field) => (
              <div
                key={field.label}
                className="flex flex-col gap-1 rounded-lg border border-slate-800 bg-slate-900/70 px-4 py-3 text-sm text-slate-200"
              >
                <span className="text-xs uppercase tracking-wide text-slate-400">
                  {field.label}
                </span>
                <span className="font-semibold text-white">{field.value}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
        <header className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-emerald-200">Availability</p>
          <h2 className="text-lg font-semibold text-white">Where to find it</h2>
        </header>
        {!availability.length && (
          <p className="mt-3 text-sm text-slate-400">
            Availability entries have not been added yet.
          </p>
        )}
        {availability.length > 0 && (
          <ul className="mt-4 space-y-3">
            {availability.map((entry) => (
              <li
                key={entry.id}
                className="rounded-lg border border-slate-800 bg-slate-900/70 p-4 text-sm text-slate-200"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-white">{entry.provider}</p>
                    <p className="text-xs text-slate-400">
                      {entry.region} / {entry.format}
                    </p>
                  </div>
                  <span
                    className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-wide ${availabilityTone(
                      entry.status
                    )}`}
                  >
                    {availabilityLabel(entry.status)}
                  </span>
                </div>
                {entry.deeplink_url && (
                  <a
                    href={entry.deeplink_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-flex text-xs font-semibold text-emerald-200 underline decoration-emerald-200/60"
                  >
                    Open provider
                  </a>
                )}
                {entry.last_checked_at && (
                  <p className="mt-2 text-xs text-slate-400">
                    Checked {new Date(entry.last_checked_at).toLocaleString()}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
        <header className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-emerald-200">Source records</p>
          <h2 className="text-lg font-semibold text-white">Where this metadata came from</h2>
        </header>
        {!media.sources.length && (
          <p className="mt-3 text-sm text-slate-400">No sources recorded yet.</p>
        )}
        {media.sources.length > 0 && (
          <ul className="mt-4 space-y-3">
            {media.sources.map((source) => (
              <li
                key={source.id}
                className="rounded-lg border border-slate-800 bg-slate-900/70 p-4 text-sm text-slate-200"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs uppercase tracking-wide text-emerald-200">
                    {source.source_name}
                  </p>
                  <span className="text-xs text-slate-400">Fetched {source.fetched_at}</span>
                </div>
                <p className="mt-2 text-xs text-slate-300">External ID: {source.external_id}</p>
                {source.canonical_url && (
                  <a
                    href={source.canonical_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-flex text-xs text-emerald-200 underline decoration-emerald-200/60"
                  >
                    View source
                  </a>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
