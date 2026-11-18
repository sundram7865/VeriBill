// Test environment. Integration tests need a real Postgres and Redis; locally these come from
// `docker compose up -d postgres redis` (the dev compose creates the invoiceiq_test database).
process.env.NODE_ENV = 'test';
process.env.LOG_LEVEL = process.env.LOG_LEVEL ?? 'silent';
process.env.DATABASE_URL =
  process.env.TEST_DATABASE_URL ?? 'postgresql://invoiceiq:invoiceiq@127.0.0.1:5432/invoiceiq_test';
process.env.REDIS_URL = process.env.TEST_REDIS_URL ?? 'redis://127.0.0.1:6379';
process.env.JWT_ACCESS_SECRET = 'test-access-secret-0123456789abcdef';
process.env.EXTRACTOR_SERVICE_TOKEN = 'test-service-token-0123456789abcdef';
process.env.STORAGE_DRIVER = 'local';
process.env.RATE_LIMIT_AUTH_PER_MIN = '1000';
process.env.RATE_LIMIT_UPLOAD_PER_MIN = '1000';
