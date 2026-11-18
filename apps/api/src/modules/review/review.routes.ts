import { Router } from 'express';
import { z } from 'zod';
import type { AppDeps } from '../../app.deps';
import { authenticate, authOf } from '../../middleware/authenticate';
import { reviewService } from './review.service';

const listQuery = z.object({
  status: z.enum(['open', 'closed']).optional().default('open'),
  type: z.enum(['needs_review', 'audit']).optional(),
  limit: z.coerce.number().int().min(1).max(200).default(50),
});

const submitBody = z.object({
  action: z.enum(['approve', 'reject']),
  corrections: z
    .array(
      z.object({
        fieldPath: z.string().min(1).max(100),
        after: z.string().max(500).nullable(),
        reason: z.string().max(500).optional(),
      }),
    )
    .max(300)
    .default([]),
});

export function reviewRoutes(deps: AppDeps): Router {
  const router = Router();
  const service = reviewService(deps);
  router.use('/review-tasks', authenticate(deps.config.JWT_ACCESS_SECRET));

  router.get('/review-tasks', async (req, res) => {
    const tasks = await service.list(authOf(req), listQuery.parse(req.query));
    res.json({ items: tasks });
  });

  router.post('/review-tasks/:id/submit', async (req, res) => {
    const id = z.string().uuid().parse(req.params.id);
    res.json(await service.submit(authOf(req), id, submitBody.parse(req.body)));
  });

  return router;
}
