import { createApp } from './app';
import type { AppDeps } from './app.deps';
import { env } from './config/env';
import { logger } from './lib/logger';
import { disconnectPrisma, prisma } from './lib/prisma';
import { createRedis, disconnectRedis, redis } from './lib/redis';
import { onShutdown } from './lib/shutdown';
import { BullExtractionQueue } from './queue/bullmqQueue';
import { createStorage } from './storage/createStorage';

function buildDeps(): AppDeps {
  const config = env();
  return {
    config,
    db: prisma(),
    redis: redis(),
    storage: createStorage(config),
    queue: new BullExtractionQueue(createRedis(config.REDIS_URL), {
      attempts: config.JOB_ATTEMPTS,
      backoffMs: config.JOB_BACKOFF_MS,
    }),
  };
}

function main(): void {
  const deps = buildDeps();
  const server = createApp(deps).listen(deps.config.PORT, () => {
    logger.info({ port: deps.config.PORT, storage: deps.storage.name }, 'api listening');
  });

  onShutdown(async () => {
    await new Promise<void>((resolve) => server.close(() => resolve()));
    await deps.queue.close();
    await disconnectRedis();
    await disconnectPrisma();
  });
}

main();
