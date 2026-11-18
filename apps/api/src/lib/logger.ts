import pino from 'pino';

/**
 * Structured JSON logs. Redaction is a safety net: we never log request bodies or
 * invoice contents on purpose, but auth headers and cookies must never leak either.
 */
export const logger = pino({
  level: process.env.LOG_LEVEL ?? 'info',
  base: { service: process.env.SERVICE_NAME ?? 'api' },
  redact: {
    paths: [
      'req.headers.authorization',
      'req.headers.cookie',
      'res.headers["set-cookie"]',
      '*.password',
      '*.token',
    ],
    censor: '[redacted]',
  },
  timestamp: pino.stdTimeFunctions.isoTime,
});

export type Logger = typeof logger;
