import { Router } from 'express';
import type { AppDeps } from '../../app.deps';

type CheckResult = 'ok' | 'down';

async function check(fn: () => Promise<unknown>): Promise<CheckResult> {
  try {
    await fn();
    return 'ok';
  } catch {
    return 'down';
  }
}

/** Liveness plus dependency checks; used by Docker health checks and Nginx. */
export function healthRoutes(deps: Pick<AppDeps, 'db' | 'redis'>): Router {
  const router = Router();
  router.get('/health', async (_req, res) => {
    const [db, redis] = await Promise.all([
      check(() => deps.db.$queryRaw`SELECT 1`),
      check(() => deps.redis.ping()),
    ]);
    const healthy = db === 'ok' && redis === 'ok';
    res.status(healthy ? 200 : 503).json({ status: healthy ? 'ok' : 'degraded', db, redis });
  });
  return router;
}
