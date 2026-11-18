import express from 'express';
import type { AddressInfo } from 'node:net';
import { afterEach, describe, expect, it } from 'vitest';
import { healthRoutes } from '../../src/modules/health/health.routes';
import type { AppDeps } from '../../src/app.deps';

type HealthDeps = Pick<AppDeps, 'db' | 'redis'>;
let close: (() => void) | undefined;

async function get(deps: HealthDeps): Promise<{ status: number; body: unknown }> {
  const app = express().use('/api', healthRoutes(deps));
  const server = app.listen(0);
  close = () => server.close();
  const { port } = server.address() as AddressInfo;
  const res = await fetch(`http://127.0.0.1:${port}/api/health`);
  return { status: res.status, body: await res.json() };
}

const okDb = { $queryRaw: async () => [1] } as unknown as HealthDeps['db'];
const okRedis = { ping: async () => 'PONG' } as unknown as HealthDeps['redis'];
const downRedis = {
  ping: async () => {
    throw new Error('down');
  },
} as unknown as HealthDeps['redis'];

afterEach(() => close?.());

describe('GET /api/health', () => {
  it('is 200 when db and redis respond', async () => {
    const res = await get({ db: okDb, redis: okRedis });
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: 'ok', db: 'ok', redis: 'ok' });
  });

  it('is 503 when a dependency is down', async () => {
    const res = await get({ db: okDb, redis: downRedis });
    expect(res.status).toBe(503);
    expect(res.body).toMatchObject({ status: 'degraded', redis: 'down' });
  });
});
