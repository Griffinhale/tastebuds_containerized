import type { MediaDetailBase } from './media';

export type DetailField = {
  label: string;
  value: string;
};

const formatList = (items?: (string | null | undefined)[] | null) => {
  if (!items) return null;
  const filtered = items.map((item) => (item ?? '').trim()).filter(Boolean);
  return filtered.length ? filtered.join(', ') : null;
};

const formatRuntime = (runtimeMinutes?: number | null) => {
  if (!runtimeMinutes) return null;
  return `${runtimeMinutes} min`;
};

const formatDuration = (durationMs?: number | null) => {
  if (!durationMs || durationMs <= 0) return null;
  const totalSeconds = Math.floor(durationMs / 1000);
  const totalMinutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (totalMinutes >= 60) {
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return `${hours}h ${minutes}m`;
  }
  return `${totalMinutes}:${seconds.toString().padStart(2, '0')}`;
};

export const buildTypeFields = (media: MediaDetailBase) => {
  const fields: DetailField[] = [];
  const pushField = (label: string, value?: string | null) => {
    if (!value) return;
    fields.push({ label, value });
  };

  if (media.media_type === 'book') {
    const book = media.book;
    pushField('Authors', formatList(book?.authors));
    pushField('Pages', book?.page_count ? `${book.page_count}` : null);
    pushField('Publisher', book?.publisher);
    pushField('Language', book?.language);
    pushField('ISBN-10', book?.isbn_10);
    pushField('ISBN-13', book?.isbn_13);
  } else if (media.media_type === 'movie' || media.media_type === 'tv') {
    const movie = media.movie;
    pushField('Runtime', formatRuntime(movie?.runtime_minutes));
    pushField('Directors', formatList(movie?.directors));
    pushField('Producers', formatList(movie?.producers));
    pushField('TMDB type', movie?.tmdb_type);
  } else if (media.media_type === 'game') {
    const game = media.game;
    pushField('Platforms', formatList(game?.platforms));
    pushField('Developers', formatList(game?.developers));
    pushField('Publishers', formatList(game?.publishers));
    pushField('Genres', formatList(game?.genres));
  } else if (media.media_type === 'music') {
    const music = media.music;
    pushField('Artist', music?.artist_name);
    pushField('Album', music?.album_name);
    pushField('Track', music?.track_number ? `${music.track_number}` : null);
    pushField('Duration', formatDuration(music?.duration_ms));
  }

  return fields;
};
