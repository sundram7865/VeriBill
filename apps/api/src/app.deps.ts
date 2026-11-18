import type { PrismaClient } from '@prisma/client';
import type { Redis } from 'ioredis';
import type { Env } from './config/env';
import type { ExtractionQueue } from './queue/extractionQueue';
import type { StorageProvider } from './storage/storageProvider';

/**
 * Everything the HTTP app needs from the outside world. Passing these in (instead of
 * importing singletons inside route files) is what lets tests swap in a local storage
 * driver or an in-memory queue without touching production code paths.
 */
export interface AppDeps {
  config: Env;
  db: PrismaClient;
  redis: Redis;
  storage: StorageProvider;
  queue: ExtractionQueue;
}
