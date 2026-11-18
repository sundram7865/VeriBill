import { Router } from 'express';
import multer from 'multer';
import { z } from 'zod';
import type { AppDeps } from '../../app.deps';
import { badRequest } from '../../lib/errors';
import { authenticate, authOf, requireRole } from '../../middleware/authenticate';
import { rateLimit } from '../../middleware/rateLimit';
import { documentsService } from './documents.service';

const STATUSES = [
  'uploaded',
  'processing',
  'auto_approved',
  'needs_review',
  'approved',
  'rejected',
  'failed',
] as const;

const listQuery = z.object({
  status: z.enum(STATUSES).optional(),
  page: z.coerce.number().int().min(1).default(1),
  pageSize: z.coerce.number().int().min(1).max(100).default(25),
});
const idParam = z.object({ id: z.string().uuid() });

/** RFC 5987 encoding so non-ASCII file names survive the Content-Disposition header. */
function contentDisposition(name: string): string {
  const ascii = name.replace(/[^\x20-\x7e]|["\\]/g, '_');
  return `inline; filename="${ascii}"; filename*=UTF-8''${encodeURIComponent(name)}`;
}

export function documentsRoutes(deps: AppDeps): Router {
  const router = Router();
  const service = documentsService(deps);
  const upload = multer({
    storage: multer.memoryStorage(),
    // multer stops reading at the limit, so an oversized upload never fills memory.
    limits: {
      fileSize: deps.config.MAX_UPLOAD_MB * 1024 * 1024,
      files: deps.config.MAX_FILES_PER_UPLOAD,
    },
  });
  const uploadLimiter = rateLimit(deps.redis, {
    name: 'upload',
    limit: deps.config.RATE_LIMIT_UPLOAD_PER_MIN,
    windowSeconds: 60,
    key: (req) => req.auth?.userId ?? req.ip ?? 'unknown',
  });

  router.use('/documents', authenticate(deps.config.JWT_ACCESS_SECRET));

  router.post('/documents', uploadLimiter, upload.array('files'), async (req, res) => {
    const files = (req.files as Express.Multer.File[] | undefined) ?? [];
    if (files.length === 0) throw badRequest('Attach at least one file in the "files" field');
    const result = await service.upload(authOf(req), files);
    res.status(result.documents.length > 0 ? 201 : 422).json(result);
  });

  router.get('/documents', async (req, res) => {
    res.json(await service.list(authOf(req), listQuery.parse(req.query)));
  });

  router.get('/documents/:id', async (req, res) => {
    res.json(await service.detail(authOf(req), idParam.parse(req.params).id));
  });

  router.get('/documents/:id/file', async (req, res) => {
    const file = await service.file(authOf(req), idParam.parse(req.params).id);
    res.setHeader('Content-Type', file.mime);
    res.setHeader('Content-Disposition', contentDisposition(file.name));
    res.setHeader('Cache-Control', 'private, no-store');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.send(file.bytes);
  });

  router.post('/documents/:id/reprocess', requireRole('admin'), async (req, res) => {
    res.status(202).json(await service.reprocess(authOf(req), idParam.parse(req.params).id));
  });

  return router;
}
