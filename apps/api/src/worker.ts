import { env } from './config/env';
import { httpExtractorClient } from './extractor/extractorClient';
import { logger } from './lib/logger';
import { disconnectPrisma, prisma } from './lib/prisma';
import { createRedis } from './lib/redis';
import { onShutdown } from './lib/shutdown';
import { createExtractionWorker } from './queue/extractionWorker';
import { createStorage } from './storage/createStorage';
import { startWorkerHealthServer } from './worker/healthServer';

function main(): void {
  const config = env();
  const connection = createRedis(config.REDIS_URL);
  const worker = createExtractionWorker(
    connection,
    {
      db: prisma(),
      storage: createStorage(config),
      extractor: httpExtractorClient({
        baseUrl: config.EXTRACTOR_URL,
        serviceToken: config.EXTRACTOR_SERVICE_TOKEN,
        timeoutMs: config.EXTRACTOR_TIMEOUT_MS,
      }),
      config,
    },
    config.WORKER_CONCURRENCY,
  );
  const health = startWorkerHealthServer(config.WORKER_HEALTH_PORT, connection);
  logger.info({ concurrency: config.WORKER_CONCURRENCY }, 'worker started');

  onShutdown(async () => {
    health.close();
    await worker.close(); // lets the in-flight job finish first
    await connection.quit();
    await disconnectPrisma();
  });
}

main();
