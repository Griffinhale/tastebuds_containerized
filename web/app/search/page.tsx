// Search workspace page.
import Link from 'next/link';

import { MediaSearchExplorer } from '../../components/media-search-explorer';

export default function SearchPage() {
  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-8 px-6 py-12">
      <div className="flex flex-wrap items-center gap-4 text-sm">
        <Link href="/" className="text-emerald-300 underline decoration-emerald-300/60">
          {'<- Back home'}
        </Link>
        <Link href="/library" className="text-emerald-300 underline decoration-emerald-300/60">
          Library
        </Link>
        <Link href="/menus" className="text-emerald-300 underline decoration-emerald-300/60">
          Menus
        </Link>
      </div>

      <MediaSearchExplorer />
    </main>
  );
}
