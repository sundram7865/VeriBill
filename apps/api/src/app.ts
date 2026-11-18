import cookieParser from 'cookie-parser';
import express, { type Express } from 'express';
import { pinoHttp } from 'pino-http';
import type { AppDeps } from './app.deps';
import { logger } from './lib/logger';
import { errorHandler, notFoundHandler } from './middleware/errorHandler';
import { requestId } from './middleware/requestId';
import { apiRoutes } from './routes';

export function createApp(deps: AppDeps): Express {
  const app = express();
  app.disable('x-powered-by');
  // Nginx sits in front in every deployment; trust exactly one proxy hop for client IPs.
  app.set('trust proxy', 1);

  app.use(requestId);
  app.use(
    pinoHttp({
      logger,
      genReqId: (req) => req.id,
      // Log method, path and status only. Query strings and bodies can carry PII.
      serializers: {
        req: (req: { id: unknown; method: string; url: string }) => ({
          id: req.id,
          method: req.method,
          path: req.url.split('?')[0],
        }),
        res: (res: { statusCode: number }) => ({ statusCode: res.statusCode }),
      },
      autoLogging: { ignore: (req) => req.url === '/api/health' },
    }),
  );
  app.use(express.json({ limit: '1mb' }));
  app.use(cookieParser());

  app.use('/api', apiRoutes(deps));

  app.use(notFoundHandler);
  app.use(errorHandler);
  return app;
}
