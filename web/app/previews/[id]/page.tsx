// External preview detail page.
import Link from 'next/link';
import { cookies } from 'next/headers';
import { notFound } from 'next/navigation';

import { ApiError } from '../../../lib/api';
import { buildTypeFields } from '../../../lib/media-detail';
import { getPreviewDetail } from '../../../lib/media';
import { formatSearchSource } from '../../../lib/search-format';

type PreviewDetailPageProps = {
  params: {
    id: string;
  };
};

export default async function PreviewDetailPage({ params }: PreviewDetailPageProps) {
  const accessToken = cookies().get('access_token')?.value;
  let preview;
  try {
    preview = await getPreviewDetail(params.id, { isServer: true, token: accessToken });
  } catch (err) {
    if (err instanceof ApiError && (err.status === 404 || err.status === 401)) {
      notFound();
    }
    throw err;
  }

  const releaseDate = preview.release_date
    ? new Date(preview.release_date).toLocaleDateString()
    : null;
  const previewExpiresAt = preview.preview_expires_at
    ? new Date(preview.preview_expires_at).toLocaleString()
    : null;
  const detailFields = buildTypeFields(preview);
  const sourceLabel = formatSearchSource(preview.source_name);

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-12">
      <Link href="/" className="text-sm text-emerald-300 underline decoration-emerald-300/60">
        &lt;- Back home
      </Link>

      <section className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
        <div className="flex flex-col gap-6 md:flex-row">
          <div className="h-44 w-32 overflow-hidden rounded-lg border border-slate-800 bg-slate-900">
            {preview.cover_image_url ? (
              <img
                src={preview.cover_image_url}
                alt={preview.title}
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
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-xs uppercase tracking-wide text-emerald-200">
                  {preview.media_type}
                </p>
                <span className="rounded-full border border-amber-400/50 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-100">
                  External preview
                </span>
              </div>
              <h1 className="text-3xl font-semibold text-white">{preview.title}</h1>
              {preview.subtitle && <p className="text-sm text-slate-300">{preview.subtitle}</p>}
            </div>
            {preview.description && (
              <p className="text-sm leading-relaxed text-slate-200">{preview.description}</p>
            )}
            <div className="flex flex-wrap gap-3 text-xs text-slate-300">
              {releaseDate && <span>Release date: {releaseDate}</span>}
              <span>Source: {sourceLabel}</span>
              <span>Preview expires: {previewExpiresAt ?? 'Unknown'}</span>
            </div>
            {preview.canonical_url && (
              <a
                href={preview.canonical_url}
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
          <p className="mt-3 text-sm text-slate-400">
            This preview does not include extra fields yet.
          </p>
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
        <p className="mt-3 text-sm text-slate-400">
          Availability tracking starts once you ingest this item into your catalog.
        </p>
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
        <header className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-emerald-200">Preview source</p>
          <h2 className="text-lg font-semibold text-white">Where this preview came from</h2>
        </header>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-4 py-3 text-sm text-slate-200">
            <span className="text-xs uppercase tracking-wide text-slate-400">Source</span>
            <p className="mt-1 font-semibold text-white">{sourceLabel}</p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-4 py-3 text-sm text-slate-200">
            <span className="text-xs uppercase tracking-wide text-slate-400">External ID</span>
            <p className="mt-1 font-semibold text-white">{preview.source_id}</p>
          </div>
          {preview.source_url && (
            <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-4 py-3 text-sm text-slate-200">
              <span className="text-xs uppercase tracking-wide text-slate-400">Source URL</span>
              <a
                href={preview.source_url}
                target="_blank"
                rel="noreferrer"
                className="mt-1 inline-flex text-xs font-semibold text-emerald-200 underline decoration-emerald-200/60"
              >
                View source record
              </a>
            </div>
          )}
          {previewExpiresAt && (
            <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-4 py-3 text-sm text-slate-200">
              <span className="text-xs uppercase tracking-wide text-slate-400">
                Preview expires
              </span>
              <p className="mt-1 font-semibold text-white">{previewExpiresAt}</p>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
