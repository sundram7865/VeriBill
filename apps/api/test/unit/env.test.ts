import { describe, expect, it } from 'vitest';
import { loadEnv } from '../../src/config/env';

const base = {
  DATABASE_URL: 'postgresql://x',
  JWT_ACCESS_SECRET: 'a'.repeat(32),
  EXTRACTOR_SERVICE_TOKEN: 'b'.repeat(32),
};

describe('loadEnv', () => {
  it('applies defaults', () => {
    const env = loadEnv(base);
    expect(env.PORT).toBe(4000);
    expect(env.STORAGE_DRIVER).toBe('local');
    expect(env.MAX_PAGES).toBe(20);
    expect(env.COOKIE_SECURE).toBe(false);
  });

  it('rejects a missing database url', () => {
    expect(() => loadEnv({ ...base, DATABASE_URL: '' })).toThrow(/DATABASE_URL/);
  });

  it('requires Cloudinary credentials when the cloudinary driver is selected', () => {
    expect(() => loadEnv({ ...base, STORAGE_DRIVER: 'cloudinary' })).toThrow(
      /CLOUDINARY_CLOUD_NAME/,
    );
  });
});
