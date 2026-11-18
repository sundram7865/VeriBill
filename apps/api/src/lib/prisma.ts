import { PrismaClient } from '@prisma/client';

let client: PrismaClient | undefined;

/** One PrismaClient per process; it owns a connection pool. */
export function prisma(): PrismaClient {
  client ??= new PrismaClient();
  return client;
}

export async function disconnectPrisma(): Promise<void> {
  if (client) {
    await client.$disconnect();
    client = undefined;
  }
}
