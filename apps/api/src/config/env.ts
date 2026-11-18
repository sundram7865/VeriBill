import { z } from 'zod';

/**
 * All configuration comes from environment variables, validated once at startup.
 * Failing fast here is cheaper than discovering a missing secret mid-request.
 */
const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().default(4000),
  LOG_LEVEL: z.enum(['fatal', 'error', 'warn', 'info', 'debug', 'trace', 'silent']).default('info'),

  DATABASE_URL: z.string().min(1),
  REDIS_URL: z.string().min(1).default('redis://localhost:6379'),

  JWT_ACCESS_SECRET: z.string().min(16),
  ACCESS_TOKEN_TTL_SECONDS: z.coerce.number().int().positive().default(900),
  REFRESH_TOKEN_TTL_DAYS: z.coerce.number().int().positive().default(7),
  COOKIE_SECURE: z
    .enum(['true', 'false'])
    .default('false')
    .transform((v) => v === 'true'),

  EXTRACTOR_URL: z.string().url().default('http://localhost:8000'),
  EXTRACTOR_SERVICE_TOKEN: z.string().min(16),
  EXTRACTOR_TIMEOUT_MS: z.coerce.number().int().positive().default(180_000),

  STORAGE_DRIVER: z.enum(['local', 'cloudinary']).default('local'),
  STORAGE_LOCAL_DIR: z.string().default('./.data/uploads'),
  CLOUDINARY_CLOUD_NAME: z.string().optional(),
  CLOUDINARY_API_KEY: z.string().optional(),
  CLOUDINARY_API_SECRET: z.string().optional(),
  CLOUDINARY_FOLDER: z.string().default('veribill'),

  MAX_UPLOAD_MB: z.coerce.number().positive().default(10),
  MAX_PAGES: z.coerce.number().int().positive().default(20),
  MAX_FILES_PER_UPLOAD: z.coerce.number().int().positive().default(20),

  WORKER_CONCURRENCY: z.coerce.number().int().positive().default(1),
  WORKER_HEALTH_PORT: z.coerce.number().int().default(4001),
  JOB_ATTEMPTS: z.coerce.number().int().positive().default(3),
  JOB_BACKOFF_MS: z.coerce.number().int().positive().default(5_000),

  AUDIT_SAMPLE_RATE: z.coerce.number().min(0).max(1).default(0.1),
  FEW_SHOT_MAX_SUPPLIERS: z.coerce.number().int().min(0).default(50),
  FEW_SHOT_PER_SUPPLIER: z.coerce.number().int().min(0).default(3),

  RATE_LIMIT_AUTH_PER_MIN: z.coerce.number().int().positive().default(10),
  RATE_LIMIT_UPLOAD_PER_MIN: z.coerce.number().int().positive().default(30),
});

export type Env = z.infer<typeof envSchema>;

export function loadEnv(source: NodeJS.ProcessEnv = process.env): Env {
  const parsed = envSchema.safeParse(source);
  if (!parsed.success) {
    const problems = parsed.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`);
    throw new Error(`Invalid environment configuration:\n  ${problems.join('\n  ')}`);
  }
  assertCloudinaryConfigured(parsed.data);
  return parsed.data;
}

function assertCloudinaryConfigured(env: Env): void {
  if (env.STORAGE_DRIVER !== 'cloudinary') return;
  const missing = (
    ['CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET'] as const
  ).filter((key) => !env[key]);
  if (missing.length > 0) {
    throw new Error(`STORAGE_DRIVER=cloudinary but missing: ${missing.join(', ')}`);
  }
}

let cached: Env | undefined;

/** Lazily loaded singleton so tests can set process.env before first use. */
export function env(): Env {
  cached ??= loadEnv();
  return cached;
}

export function resetEnvCache(): void {
  cached = undefined;
}
