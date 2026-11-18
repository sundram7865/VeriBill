import { Router } from 'express';
import type { AppDeps } from './app.deps';
import { authRoutes } from './modules/auth/auth.routes';
import { documentsRoutes } from './modules/documents/documents.routes';
import { exportRoutes } from './modules/export/export.routes';
import { healthRoutes } from './modules/health/health.routes';
import { invoicesRoutes } from './modules/invoices/invoices.routes';
import { metricsRoutes } from './modules/metrics/metrics.routes';
import { reviewRoutes } from './modules/review/review.routes';

/** Mounts every module router under /api. */
export function apiRoutes(deps: AppDeps): Router {
  const router = Router();
  router.use(healthRoutes(deps));
  router.use(authRoutes(deps));
  router.use(documentsRoutes(deps));
  router.use(reviewRoutes(deps));
  router.use(metricsRoutes(deps));
  router.use(exportRoutes(deps));
  router.use(invoicesRoutes(deps));
  return router;
}
