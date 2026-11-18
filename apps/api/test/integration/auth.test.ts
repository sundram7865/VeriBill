import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { startTestApp, tokenFor, type TestContext } from '../helpers/app';
import { createTenant, PASSWORD, resetDatabase, type TenantFixture } from '../helpers/db';
import { call, refreshCookie } from '../helpers/http';

let ctx: TestContext;
let acme: TenantFixture;

beforeAll(async () => {
  ctx = await startTestApp();
});
afterAll(async () => ctx.close());
beforeEach(async () => {
  await resetDatabase(ctx.deps.db);
  acme = await createTenant(ctx.deps.db, 'Acme');
});

async function login(email: string, password = PASSWORD) {
  return call(ctx.baseUrl, '/auth/login', { method: 'POST', json: { email, password } });
}

describe('auth', () => {
  it('logs in and returns an access token plus an httpOnly refresh cookie', async () => {
    const res = await login(acme.admin.email);
    expect(res.status).toBe(200);
    expect(res.body.accessToken).toBeTypeOf('string');
    expect(res.body.user).toMatchObject({ email: acme.admin.email, role: 'admin' });
    const setCookie = res.headers.get('set-cookie') ?? '';
    expect(setCookie).toContain('HttpOnly');
    expect(setCookie).toContain('Path=/api/auth');
    expect(setCookie.toLowerCase()).toContain('samesite=strict');
  });

  it('gives the same error for an unknown email and a wrong password', async () => {
    const unknown = await login('nobody@acme.test');
    const wrong = await login(acme.admin.email, 'wrong password');
    expect(unknown.status).toBe(401);
    expect(wrong.status).toBe(401);
    expect(unknown.body.error.message).toBe(wrong.body.error.message);
  });

  it('rotates the refresh token and detects reuse of an old one', async () => {
    const first = refreshCookie((await login(acme.reviewer.email)).headers);
    const rotated = await call(ctx.baseUrl, '/auth/refresh', {
      method: 'POST',
      headers: { cookie: first },
    });
    expect(rotated.status).toBe(200);
    const second = refreshCookie(rotated.headers);
    expect(second).not.toBe(first);

    // Replaying the first (already rotated) token is treated as theft: the family is revoked...
    const replay = await call(ctx.baseUrl, '/auth/refresh', {
      method: 'POST',
      headers: { cookie: first },
    });
    expect(replay.status).toBe(401);
    // ...so even the newest token of that login no longer works.
    const afterRevoke = await call(ctx.baseUrl, '/auth/refresh', {
      method: 'POST',
      headers: { cookie: second },
    });
    expect(afterRevoke.status).toBe(401);
  });

  it('logout revokes the refresh token', async () => {
    const cookie = refreshCookie((await login(acme.admin.email)).headers);
    expect(
      (await call(ctx.baseUrl, '/auth/logout', { method: 'POST', headers: { cookie } })).status,
    ).toBe(204);
    expect(
      (await call(ctx.baseUrl, '/auth/refresh', { method: 'POST', headers: { cookie } })).status,
    ).toBe(401);
  });

  it('protects routes and returns the current user', async () => {
    expect((await call(ctx.baseUrl, '/auth/me')).status).toBe(401);
    const me = await call(ctx.baseUrl, '/auth/me', {
      headers: { authorization: `Bearer ${tokenFor(acme.reviewer)}` },
    });
    expect(me.body.user.role).toBe('reviewer');
  });

  it('read-only MCP tokens cannot write', async () => {
    const token = tokenFor(acme.admin, undefined, 'mcp:read');
    const read = await call(ctx.baseUrl, '/documents', {
      headers: { authorization: `Bearer ${token}` },
    });
    expect(read.status).toBe(200);
    const write = await call(ctx.baseUrl, '/documents', {
      method: 'POST',
      headers: { authorization: `Bearer ${token}` },
    });
    expect(write.status).toBe(403);
  });
});
