import { logger } from './logger';

/** Run cleanup once on SIGTERM/SIGINT (docker stop sends SIGTERM), then exit. */
export function onShutdown(cleanup: () => Promise<void>): void {
  let shuttingDown = false;
  const handler = (signal: string) => {
    if (shuttingDown) return;
    shuttingDown = true;
    logger.info({ signal }, 'shutting down');
    cleanup()
      .then(() => process.exit(0))
      .catch((err: unknown) => {
        logger.error({ err }, 'error during shutdown');
        process.exit(1);
      });
  };
  process.on('SIGTERM', handler);
  process.on('SIGINT', handler);
}
