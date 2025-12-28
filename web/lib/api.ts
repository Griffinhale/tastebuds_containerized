// Shared API fetch wrapper with server/client base URL switching.
type ApiFetchOptions = {
  isServer?: boolean;
  token?: string;
  withCredentials?: boolean;
};

export class ApiError extends Error {
  status: number;
  detail?: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

const browserBase = process.env.NEXT_PUBLIC_API_BASE || 'https://localhost/api';
const serverBase =
  process.env.API_INTERNAL_BASE || process.env.NEXT_PUBLIC_API_BASE || 'http://api:8000/api';

export function getApiBase(isServer: boolean) {
  // Use the internal Docker base for server-side requests.
  return isServer ? serverBase : browserBase;
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
  opts: ApiFetchOptions = {}
): Promise<T> {
  // Default to include cookies unless explicitly disabled.
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
    let detail: unknown;
    try {
      const errorBody = await res.json();
      detail = errorBody?.detail || errorBody?.message;
      if (detail) {
        if (typeof detail === 'string') {
          message = detail;
        } else if (detail && typeof detail === 'object' && 'message' in detail) {
          message = String((detail as { message?: string }).message ?? message);
        } else {
          message = JSON.stringify(detail);
        }
      }
    } catch {
      // swallow parse errors and surface the generic message
    }
    throw new ApiError(message, res.status, detail);
  }

  if (res.status === 204 || res.status === 205) {
    // @ts-expect-error allow undefined for empty responses
    return undefined;
  }

  return (await res.json()) as T;
}
