import { mkdtempSync } from 'node:fs';
import type { Server } from 'node:http';
import type { AddressInfo } from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { PrismaClient, type User } from '@prisma/client';
import { Redis } from 'ioredis';
import { createApp } from '../../src/app';
import type { AppDeps } from '../../src/app.deps';
import { loadEnv } from '../../src/config/env';
import { signAccessToken } from '../../src/modules/auth/accessToken';
import type { ExtractionJobData, ExtractionQueue } from '../../src/queue/extractionQueue';
import { LocalStorage } from '../../src/storage/localStorage';

/** Records enqueued jobs instead of sending them to Redis (HTTP tests don't need a worker). */
export class RecordingQueue implements ExtractionQueue {
  jobs: ExtractionJobData[] = [];
  async enqueue(job: ExtractionJobData): Promise<void> {
    this.jobs.push(job);
  }
  async close(): Promise<void> {}
}

export interface TestContext {
  deps: AppDeps & { queue: RecordingQueue };
  baseUrl: string;
  close: () => Promise<void>;
}

export async function startTestApp(): Promise<TestContext> {
  const config = loadEnv();
  const deps = {
    config,
    db: new PrismaClient(),
    redis: new Redis(config.REDIS_URL, { maxRetriesPerRequest: null }),
    storage: new LocalStorage(mkdtempSync(path.join(os.tmpdir(), 'iq-storage-'))),
    queue: new RecordingQueue(),
  };
  const server: Server = await new Promise((resolve) => {
    const s = createApp(deps).listen(0, '127.0.0.1', () => resolve(s));
  });
  const { port } = server.address() as AddressInfo;
  return {
    deps,
    baseUrl: `http://127.0.0.1:${port}/api`,
    close: async () => {
      await new Promise<void>((resolve) => server.close(() => resolve()));
      await deps.redis.quit();
      await deps.db.$disconnect();
    },
  };
}

export function tokenFor(
  user: User,
  config = loadEnv(),
  scope: 'user' | 'mcp:read' = 'user',
): string {
  return signAccessToken(
    { userId: user.id, tenantId: user.tenantId, role: user.role, scope },
    config.JWT_ACCESS_SECRET,
    600,
  );
}

export function authHeader(user: User): Record<string, string> {
  return { authorization: `Bearer ${tokenFor(user)}` };
}
