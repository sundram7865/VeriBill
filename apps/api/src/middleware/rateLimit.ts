import type { Request, RequestHandler } from 'express';
import type { Redis } from 'ioredis';
import { tooManyRequests } from '../lib/errors';

interface RateLimitOptions {
  name: string;
  limit: number;
  windowSeconds: number;
  key?: (req: Request) => string;
}

/**
 * Fixed-window limiter in Redis: INCR a per-window counter, set its expiry on first hit.
 * Simple and good enough for login and upload abuse; it allows at most 2x the limit across a
 * window boundary, which is acceptable here.
 */
export function rateLimit(redis: Redis, options: RateLimitOptions): RequestHandler {
  const keyOf = options.key ?? ((req: Request) => req.ip ?? 'unknown');
  return async (req, _res, next) => {
    const window = Math.floor(Date.now() / 1000 / options.windowSeconds);
    const key = `ratelimit:${options.name}:${keyOf(req)}:${window}`;
    const count = await redis.incr(key);
    if (count === 1) await redis.expire(key, options.windowSeconds);
    if (count > options.limit) {
      const retryAfter =
        options.windowSeconds - (Math.floor(Date.now() / 1000) % options.windowSeconds);
      throw tooManyRequests(retryAfter);
    }
    next();
  };
}
