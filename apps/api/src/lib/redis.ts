import { Redis } from 'ioredis';
import { env } from '../config/env';

let shared: Redis | undefined;

/**
 * BullMQ requires maxRetriesPerRequest=null on connections it uses for blocking commands,
 * so every connection is created the same way to keep things predictable.
 */
export function createRedis(url: string = env().REDIS_URL): Redis {
  return new Redis(url, { maxRetriesPerRequest: null });
}

/** Shared connection for non-blocking commands (rate limiting, health checks). */
export function redis(): Redis {
  shared ??= createRedis();
  return shared;
}

export async function disconnectRedis(): Promise<void> {
  if (shared) {
    await shared.quit();
    shared = undefined;
  }
}
