export interface ApiResponse<T = unknown> {
  status: number;
  body: T;
  headers: Headers;
}

/** fetch wrapper for tests: JSON in, JSON (or text) out. */
export async function call<T = any>(
  baseUrl: string,
  path: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<ApiResponse<T>> {
  const headers = new Headers(init.headers);
  let body = init.body;
  if (init.json !== undefined) {
    headers.set('content-type', 'application/json');
    body = JSON.stringify(init.json);
  }
  const res = await fetch(`${baseUrl}${path}`, { ...init, headers, body });
  const type = res.headers.get('content-type') ?? '';
  const parsed = type.includes('application/json') ? await res.json() : await res.text();
  return { status: res.status, body: parsed as T, headers: res.headers };
}

/** The refresh cookie value from a Set-Cookie header, ready to send back as a Cookie header. */
export function refreshCookie(headers: Headers): string {
  const setCookie = headers.get('set-cookie') ?? '';
  const match = /iq_refresh=([^;]*)/.exec(setCookie);
  return match ? `iq_refresh=${match[1]}` : '';
}
