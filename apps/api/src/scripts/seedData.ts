import type { PrismaClient } from '@prisma/client';
import { hashPassword } from '../modules/auth/password';

export const DEMO_TENANT = 'Demo Traders';

export interface SeedUser {
  email: string;
  name: string;
  role: 'admin' | 'reviewer';
  password: string;
}

/** Idempotent: re-running updates passwords instead of creating duplicates. */
export async function seedTenantAndUsers(db: PrismaClient, users: SeedUser[]): Promise<string> {
  const tenant =
    (await db.tenant.findFirst({ where: { name: DEMO_TENANT } })) ??
    (await db.tenant.create({ data: { name: DEMO_TENANT } }));
  for (const user of users) {
    const passwordHash = await hashPassword(user.password);
    await db.user.upsert({
      where: { email: user.email },
      create: {
        tenantId: tenant.id,
        email: user.email,
        name: user.name,
        role: user.role,
        passwordHash,
      },
      update: { passwordHash, role: user.role, name: user.name },
    });
  }
  return tenant.id;
}
