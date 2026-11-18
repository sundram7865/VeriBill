import type { PrismaClient, User } from '@prisma/client';
import { hashPassword } from '../../src/modules/auth/password';

const TABLES = [
  'audit_log',
  'corrections',
  'review_tasks',
  'extracted_fields',
  'extraction_runs',
  'invoices',
  'suppliers',
  'documents',
  'refresh_tokens',
  'users',
  'tenants',
];

export async function resetDatabase(db: PrismaClient): Promise<void> {
  await db.$executeRawUnsafe(`TRUNCATE ${TABLES.join(', ')} RESTART IDENTITY CASCADE`);
}

export const PASSWORD = 'correct horse battery staple';

export interface TenantFixture {
  tenantId: string;
  admin: User;
  reviewer: User;
}

let passwordHash: string | undefined;

export async function createTenant(db: PrismaClient, name: string): Promise<TenantFixture> {
  passwordHash ??= await hashPassword(PASSWORD);
  const tenant = await db.tenant.create({ data: { name } });
  const slug = name.toLowerCase().replace(/[^a-z0-9]/g, '');
  const admin = await db.user.create({
    data: {
      tenantId: tenant.id,
      email: `admin@${slug}.test`,
      name: 'Admin',
      role: 'admin',
      passwordHash,
    },
  });
  const reviewer = await db.user.create({
    data: {
      tenantId: tenant.id,
      email: `reviewer@${slug}.test`,
      name: 'Reviewer',
      role: 'reviewer',
      passwordHash,
    },
  });
  return { tenantId: tenant.id, admin, reviewer };
}
