import { execSync } from 'node:child_process';
import path from 'node:path';

/** Applies migrations to the test database once per run. */
export default function setup(): void {
  const databaseUrl =
    process.env.TEST_DATABASE_URL ??
    'postgresql://invoiceiq:invoiceiq@127.0.0.1:5432/invoiceiq_test';
  execSync('pnpm exec prisma migrate deploy', {
    cwd: path.resolve(__dirname, '../..'),
    env: { ...process.env, DATABASE_URL: databaseUrl },
    stdio: 'pipe',
  });
}
