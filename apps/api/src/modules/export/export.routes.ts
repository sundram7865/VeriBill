import { Router } from 'express';
import { z } from 'zod';
import type { AppDeps } from '../../app.deps';
import { authenticate, authOf, requireRole } from '../../middleware/authenticate';
import { exportService } from './export.service';

const rangeQuery = z.object({
  from: z.coerce.date().optional(),
  to: z.coerce.date().optional(),
});

export function exportRoutes(deps: AppDeps): Router {
  const router = Router();
  const service = exportService(deps);
  // Exports carry every approved invoice of the tenant, so only admins may download them.
  router.use('/export', authenticate(deps.config.JWT_ACCESS_SECRET), requireRole('admin'));

  router.get('/export/invoices.csv', async (req, res) => {
    const csv = await service.csv(authOf(req), rangeQuery.parse(req.query));
    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', 'attachment; filename="invoices.csv"');
    res.send(csv);
  });

  router.get('/export/invoices.json', async (req, res) => {
    const invoices = await service.json(authOf(req), rangeQuery.parse(req.query));
    res.setHeader('Content-Disposition', 'attachment; filename="invoices.json"');
    res.json({ invoices });
  });

  return router;
}
