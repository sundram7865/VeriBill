/* eslint-disable no-console */
/**
 * Mint a read-only token for the MCP server: pnpm mint:mcp-token -- <user email> [days]
 * The token can only make GET requests (enforced in middleware/authenticate.ts).
 */
import { PrismaClient } from '@prisma/client';
import { env } from '../config/env';
import { signAccessToken } from '../modules/auth/accessToken';

async function main(): Promise<void> {
  const email = process.argv[2];
  const days = Number(process.argv[3] ?? 30);
  if (!email) throw new Error('usage: pnpm mint:mcp-token -- <user email> [days]');
  const db = new PrismaClient();
  try {
    const user = await db.user.findUnique({ where: { email } });
    if (!user) throw new Error(`no user with email ${email}`);
    const token = signAccessToken(
      { userId: user.id, tenantId: user.tenantId, role: user.role, scope: 'mcp:read' },
      env().JWT_ACCESS_SECRET,
      days * 86_400,
    );
    console.log(token);
  } finally {
    await db.$disconnect();
  }
}

main().catch((err: unknown) => {
  console.error(err instanceof Error ? err.message : err);
  process.exit(1);
});
