/* eslint-disable no-console */
/**
 * Seed the demo tenant, one admin and one reviewer. There is no public signup: this script is the
 * only way users are created. Needs DATABASE_URL, so run it where the API's environment is:
 *
 *   docker compose exec api node dist/scripts/seed.js     # local Docker stack
 *   ./scripts/deploy.sh --seed                             # production (see docs/DEPLOY.md)
 *
 * Sample invoices are uploaded separately through the API: pnpm seed:samples
 */
import { PrismaClient } from '@prisma/client';
import { demoCredentials } from './demoCredentials';
import { seedTenantAndUsers } from './seedData';

async function main(): Promise<void> {
  const { admin, reviewer } = demoCredentials();
  const db = new PrismaClient();
  try {
    const tenantId = await seedTenantAndUsers(db, [
      { email: admin.email, name: 'Demo Admin', role: 'admin', password: admin.password },
      {
        email: reviewer.email,
        name: 'Demo Reviewer',
        role: 'reviewer',
        password: reviewer.password,
      },
    ]);
    console.log(`tenant ${tenantId}: ${admin.email} (admin), ${reviewer.email} (reviewer)`);
  } finally {
    await db.$disconnect();
  }
}

main().catch((err: unknown) => {
  console.error(err);
  process.exit(1);
});
