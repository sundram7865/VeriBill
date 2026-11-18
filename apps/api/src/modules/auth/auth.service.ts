import { randomUUID } from 'node:crypto';
import type { PrismaClient, User } from '@prisma/client';
import type { Env } from '../../config/env';
import { unauthorized } from '../../lib/errors';
import { randomToken, sha256Hex } from '../../lib/hash';
import { signAccessToken } from './accessToken';
import type { AuthContext } from './auth.types';
import { verifyPassword } from './password';
import { refreshTokensRepository } from './refreshTokens.repository';

export interface PublicUser {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'reviewer';
  tenantId: string;
}

export interface Session {
  accessToken: string;
  refreshToken: string;
  refreshExpiresAt: Date;
  user: PublicUser;
}

// Same message for "no such user" and "wrong password" so login cannot probe for emails.
const BAD_CREDENTIALS = 'Invalid email or password';

export function toPublicUser(user: User): PublicUser {
  return {
    id: user.id,
    email: user.email,
    name: user.name,
    role: user.role,
    tenantId: user.tenantId,
  };
}

export function authService(db: PrismaClient, config: Env) {
  const tokens = refreshTokensRepository(db);

  async function issueSession(user: User, familyId: string): Promise<Session> {
    const ctx: AuthContext = {
      userId: user.id,
      tenantId: user.tenantId,
      role: user.role,
      scope: 'user',
    };
    const refreshToken = randomToken();
    const refreshExpiresAt = new Date(Date.now() + config.REFRESH_TOKEN_TTL_DAYS * 86_400_000);
    await tokens.create({
      tenantId: user.tenantId,
      userId: user.id,
      tokenHash: sha256Hex(refreshToken),
      familyId,
      expiresAt: refreshExpiresAt,
    });
    return {
      accessToken: signAccessToken(ctx, config.JWT_ACCESS_SECRET, config.ACCESS_TOKEN_TTL_SECONDS),
      refreshToken,
      refreshExpiresAt,
      user: toPublicUser(user),
    };
  }

  return {
    async login(email: string, password: string): Promise<Session> {
      const user = await db.user.findUnique({ where: { email: email.trim().toLowerCase() } });
      if (!user || !(await verifyPassword(password, user.passwordHash))) {
        throw unauthorized(BAD_CREDENTIALS);
      }
      return issueSession(user, randomUUID());
    },

    /**
     * Rotation: every refresh revokes the presented token and issues a new one in the same
     * family. Presenting a token that was already rotated means it was copied, so the whole
     * family (that login on every device) is revoked.
     */
    async refresh(presented: string | undefined): Promise<Session> {
      if (!presented) throw unauthorized('No refresh token');
      const stored = await tokens.findByHash(sha256Hex(presented));
      if (!stored) throw unauthorized('Unknown refresh token');
      if (stored.revokedAt) {
        await tokens.revokeFamily(stored.familyId);
        throw unauthorized('Refresh token reuse detected; please log in again');
      }
      if (stored.expiresAt < new Date()) throw unauthorized('Refresh token expired');
      if (!(await tokens.revokeIfActive(stored.id))) {
        await tokens.revokeFamily(stored.familyId);
        throw unauthorized('Refresh token reuse detected; please log in again');
      }
      const user = await db.user.findUnique({ where: { id: stored.userId } });
      if (!user) throw unauthorized('User no longer exists');
      return issueSession(user, stored.familyId);
    },

    async logout(presented: string | undefined): Promise<void> {
      if (!presented) return;
      const stored = await tokens.findByHash(sha256Hex(presented));
      if (stored) await tokens.revokeFamily(stored.familyId);
    },

    async me(ctx: AuthContext): Promise<PublicUser> {
      const user = await db.user.findFirst({ where: { id: ctx.userId, tenantId: ctx.tenantId } });
      if (!user) throw unauthorized('User no longer exists');
      return toPublicUser(user);
    },
  };
}
