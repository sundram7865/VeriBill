import { Router, type CookieOptions, type Response } from 'express';
import { z } from 'zod';
import type { AppDeps } from '../../app.deps';
import { authenticate, authOf } from '../../middleware/authenticate';
import { rateLimit } from '../../middleware/rateLimit';
import { authService, type Session } from './auth.service';

export const REFRESH_COOKIE = 'iq_refresh';

const loginBody = z.object({
  email: z.string().email().max(254),
  password: z.string().min(1).max(200),
});

function cookieOptions(secure: boolean, expires?: Date): CookieOptions {
  // httpOnly: JavaScript can never read it. Path-scoped: only sent to the auth endpoints.
  return { httpOnly: true, secure, sameSite: 'strict', path: '/api/auth', expires };
}

function sendSession(res: Response, session: Session, secure: boolean): void {
  res.cookie(REFRESH_COOKIE, session.refreshToken, cookieOptions(secure, session.refreshExpiresAt));
  res.json({ accessToken: session.accessToken, user: session.user });
}

export function authRoutes(deps: AppDeps): Router {
  const router = Router();
  const service = authService(deps.db, deps.config);
  const secure = deps.config.COOKIE_SECURE;
  const limiter = rateLimit(deps.redis, {
    name: 'auth',
    limit: deps.config.RATE_LIMIT_AUTH_PER_MIN,
    windowSeconds: 60,
  });

  router.post('/auth/login', limiter, async (req, res) => {
    const { email, password } = loginBody.parse(req.body);
    sendSession(res, await service.login(email, password), secure);
  });

  router.post('/auth/refresh', limiter, async (req, res) => {
    const presented = req.cookies?.[REFRESH_COOKIE] as string | undefined;
    try {
      sendSession(res, await service.refresh(presented), secure);
    } catch (err) {
      res.clearCookie(REFRESH_COOKIE, cookieOptions(secure));
      throw err;
    }
  });

  router.post('/auth/logout', async (req, res) => {
    await service.logout(req.cookies?.[REFRESH_COOKIE] as string | undefined);
    res.clearCookie(REFRESH_COOKIE, cookieOptions(secure));
    res.status(204).end();
  });

  router.get('/auth/me', authenticate(deps.config.JWT_ACCESS_SECRET), async (req, res) => {
    res.json({ user: await service.me(authOf(req)) });
  });

  return router;
}
