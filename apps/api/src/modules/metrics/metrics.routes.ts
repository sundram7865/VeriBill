import { Router } from 'express';
import { z } from 'zod';
import type { AppDeps } from '../../app.deps';
import { authenticate, authOf } from '../../middleware/authenticate';
import { metricsService } from './metrics.service';

const query = z.object({ days: z.coerce.number().int().min(1).max(365).default(30) });

export function metricsRoutes(deps: AppDeps): Router {
  const router = Router();
  const service = metricsService(deps);
  router.get('/metrics', authenticate(deps.config.JWT_ACCESS_SECRET), async (req, res) => {
    res.json(await service.summary(authOf(req), query.parse(req.query).days));
  });
  return router;
}
