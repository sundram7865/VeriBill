import http from 'node:http';
import type { Redis } from 'ioredis';

/**
 * The worker has no HTTP API, but Docker needs something to probe. This tiny server
 * answers /health with Redis reachability, which is the worker's one hard dependency.
 */
export function startWorkerHealthServer(port: number, redis: Redis): http.Server {
  const server = http.createServer((req, res) => {
    if (req.url !== '/health') {
      res.writeHead(404).end();
      return;
    }
    redis
      .ping()
      .then(() => respond(res, 200, { status: 'ok', redis: 'ok' }))
      .catch(() => respond(res, 503, { status: 'degraded', redis: 'down' }));
  });
  server.listen(port);
  return server;
}

function respond(res: http.ServerResponse, status: number, body: object): void {
  res.writeHead(status, { 'content-type': 'application/json' }).end(JSON.stringify(body));
}
