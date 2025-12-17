const browserBase = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000/api';
const serverBase =
  process.env.API_INTERNAL_BASE || process.env.NEXT_PUBLIC_API_BASE || 'http://api:8000/api';

export function getApiBase(isServer: boolean) {
  return isServer ? serverBase : browserBase;
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
  opts: { isServer?: boolean } = {}
): Promise<T> {
  const base = getApiBase(opts.isServer ?? typeof window === 'undefined');
  const url = `${base}${path.startsWith('/') ? path : `/${path}`}`;

  const res = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {})
    },
    cache: init?.cache ?? 'no-store'
  });

  if (!res.ok) {
    const message = `API request failed: ${res.status} ${res.statusText}`;
    throw new Error(message);
  }

  return (await res.json()) as T;
}
