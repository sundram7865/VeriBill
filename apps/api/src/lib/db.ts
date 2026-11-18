import type { Prisma, PrismaClient } from '@prisma/client';

/** Repositories accept either the client or a transaction, so callers can compose them. */
export type Db = PrismaClient | Prisma.TransactionClient;

/**
 * Every tenant-scoped repository function calls this first. A missing tenant id is a
 * programming error, and failing loudly beats silently querying across tenants.
 */
export function assertTenant(tenantId: string): void {
  if (!tenantId || typeof tenantId !== 'string') {
    throw new Error('tenantId is required for tenant-scoped queries');
  }
}
