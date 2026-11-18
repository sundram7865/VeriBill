import jwt from 'jsonwebtoken';
import { z } from 'zod';
import { unauthorized } from '../../lib/errors';
import type { AuthContext } from './auth.types';

const claimsSchema = z.object({
  sub: z.string().uuid(),
  tid: z.string().uuid(),
  role: z.enum(['admin', 'reviewer']),
  scope: z.enum(['user', 'mcp:read']),
});

export function signAccessToken(ctx: AuthContext, secret: string, ttlSeconds: number): string {
  return jwt.sign({ tid: ctx.tenantId, role: ctx.role, scope: ctx.scope }, secret, {
    algorithm: 'HS256',
    subject: ctx.userId,
    expiresIn: ttlSeconds,
  });
}

export function verifyAccessToken(token: string, secret: string): AuthContext {
  let payload: unknown;
  try {
    payload = jwt.verify(token, secret, { algorithms: ['HS256'] });
  } catch {
    throw unauthorized('Invalid or expired access token');
  }
  const claims = claimsSchema.safeParse(payload);
  if (!claims.success) throw unauthorized('Malformed access token');
  return {
    userId: claims.data.sub,
    tenantId: claims.data.tid,
    role: claims.data.role,
    scope: claims.data.scope,
  };
}
