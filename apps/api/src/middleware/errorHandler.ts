import type { ErrorRequestHandler, RequestHandler } from 'express';
import { MulterError } from 'multer';
import { ZodError } from 'zod';
import { HttpError } from '../lib/errors';

export const notFoundHandler: RequestHandler = (_req, res) => {
  res.status(404).json({ error: { code: 'not_found', message: 'Route not found' } });
};

export const errorHandler: ErrorRequestHandler = (err, req, res, _next) => {
  const mapped = toHttpError(err);
  if (mapped.status >= 500) {
    req.log?.error({ err }, 'unhandled error');
  }
  if (mapped.status === 429) {
    const retry = (mapped.details as { retryAfterSeconds?: number } | undefined)?.retryAfterSeconds;
    if (retry) res.setHeader('Retry-After', String(retry));
  }
  res.status(mapped.status).json({
    error: { code: mapped.code, message: mapped.message, details: mapped.details },
    requestId: req.id,
  });
};

function toHttpError(err: unknown): HttpError {
  if (err instanceof HttpError) return err;
  if (err instanceof ZodError) {
    const details = err.issues.map((i) => ({ path: i.path.join('.'), message: i.message }));
    return new HttpError(400, 'validation_error', 'Request validation failed', details);
  }
  if (err instanceof MulterError) {
    const status = err.code === 'LIMIT_FILE_SIZE' ? 413 : 400;
    return new HttpError(status, 'upload_error', err.message);
  }
  if (isBodyParserError(err)) {
    return new HttpError(400, 'bad_request', 'Malformed request body');
  }
  return new HttpError(500, 'internal_error', 'Something went wrong');
}

function isBodyParserError(err: unknown): boolean {
  return typeof err === 'object' && err !== null && 'type' in err && 'status' in err;
}
