import type { ApiErrorBody, User } from './types';

/** Same-origin in every environment: Nginx (prod) or the Next dev rewrite proxies /api. */
const API_BASE = '/api';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details?: unknown,
  ) {
    super(message);
  }
}

interface Session {
  accessToken: string;
  user: User;
}

// The access token lives only in memory (never localStorage), so XSS cannot read a stored copy;
// the refresh token is an httpOnly cookie that JavaScript cannot see at all.
let accessToken: string | null = null;
let refreshInFlight: Promise<Session | null> | null = null;
let onSessionLost: (() => void) | null = null;

export function setSessionLostHandler(handler: () => void): void {
  onSessionLost = handler;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

async function toError(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as ApiErrorBody;
    return new ApiError(res.status, body.error.code, body.error.message, body.error.details);
  } catch {
    return new ApiError(res.status, 'http_error', `Request failed (${res.status})`);
  }
}

/** One refresh at a time, shared by every request that hit a 401 concurrently. */
export function refreshSession(): Promise<Session | null> {
  refreshInFlight ??= (async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        credentials: 'same-origin',
      });
      if (!res.ok) return null;
      const session = (await res.json()) as Session;
      accessToken = session.accessToken;
      return session;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

async function send(path: string, init: RequestInit): Promise<Response> {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set('authorization', `Bearer ${accessToken}`);
  return fetch(`${API_BASE}${path}`, { ...init, headers, credentials: 'same-origin' });
}

/**
 * fetch with auth; on 401 refreshes the access token once and retries. `okStatuses` lists
 * non-2xx statuses whose body the caller wants to read itself (e.g. 422 upload rejections).
 */
export async function apiFetch(
  path: string,
  init: RequestInit = {},
  okStatuses: number[] = [],
): Promise<Response> {
  let res = await send(path, init);
  if (res.status === 401 && !path.startsWith('/auth/')) {
    const session = await refreshSession();
    if (!session) {
      onSessionLost?.();
      throw await toError(res);
    }
    res = await send(path, init);
  }
  if (!res.ok && !okStatuses.includes(res.status)) throw await toError(res);
  return res;
}

export async function apiJson<T>(
  path: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<T> {
  const { json, ...rest } = init;
  const headers = new Headers(rest.headers);
  if (json !== undefined) headers.set('content-type', 'application/json');
  const res = await apiFetch(path, {
    ...rest,
    headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export async function login(email: string, password: string): Promise<Session> {
  const session = await apiJson<Session>('/auth/login', {
    method: 'POST',
    json: { email, password },
  });
  accessToken = session.accessToken;
  return session;
}

export async function logout(): Promise<void> {
  try {
    await apiFetch('/auth/logout', { method: 'POST' });
  } finally {
    accessToken = null;
  }
}
