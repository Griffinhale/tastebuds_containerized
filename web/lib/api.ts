type ApiFetchOptions = {
  isServer?: boolean;
  token?: string;
  withCredentials?: boolean;
};

const browserBase = process.env.NEXT_PUBLIC_API_BASE || 'https://localhost/api';
const serverBase =
  process.env.API_INTERNAL_BASE || process.env.NEXT_PUBLIC_API_BASE || 'http://api:8000/api';

export function getApiBase(isServer: boolean) {
  return isServer ? serverBase : browserBase;
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
  opts: ApiFetchOptions = {}
): Promise<T> {
  const base = getApiBase(opts.isServer ?? typeof window === 'undefined');
  const url = `${base}${path.startsWith('/') ? path : `/${path}`}`;

  const res = await fetch(url, {
    ...init,
    credentials: init?.credentials ?? (opts.withCredentials === false ? 'same-origin' : 'include'),
    headers: {
      'Content-Type': 'application/json',
      ...(opts.token ? { Authorization: `Bearer ${opts.token}` } : {}),
      ...(init?.headers || {}),
    },
    cache: init?.cache ?? 'no-store',
  });

  if (!res.ok) {
    let message = `API request failed: ${res.status} ${res.statusText}`;
    try {
      const errorBody = await res.json();
      const detail = errorBody?.detail || errorBody?.message;
      if (detail) {
        message = typeof detail === 'string' ? detail : JSON.stringify(detail);
      }
    } catch {
      // swallow parse errors and surface the generic message
    }
    throw new Error(message);
  }

  if (res.status === 204 || res.status === 205) {
    // @ts-expect-error allow undefined for empty responses
    return undefined;
  }

  return (await res.json()) as T;
}
