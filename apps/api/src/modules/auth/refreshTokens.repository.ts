import type { PrismaClient, RefreshToken } from '@prisma/client';

/** Refresh tokens are looked up by hash only; they carry their own tenant and user ids. */
export function refreshTokensRepository(db: PrismaClient) {
  return {
    create(data: {
      tenantId: string;
      userId: string;
      tokenHash: string;
      familyId: string;
      expiresAt: Date;
    }): Promise<RefreshToken> {
      return db.refreshToken.create({ data });
    },

    findByHash(tokenHash: string): Promise<RefreshToken | null> {
      return db.refreshToken.findUnique({ where: { tokenHash } });
    },

    /** Atomically revoke one token; returns false if it was already revoked (lost a race). */
    async revokeIfActive(id: string): Promise<boolean> {
      const result = await db.refreshToken.updateMany({
        where: { id, revokedAt: null },
        data: { revokedAt: new Date() },
      });
      return result.count === 1;
    },

    revokeFamily(familyId: string): Promise<{ count: number }> {
      return db.refreshToken.updateMany({
        where: { familyId, revokedAt: null },
        data: { revokedAt: new Date() },
      });
    },
  };
}

export type RefreshTokensRepository = ReturnType<typeof refreshTokensRepository>;
