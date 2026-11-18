export interface Credentials {
  email: string;
  password: string;
}

/**
 * Demo users. The defaults are for local development only; production must set the
 * SEED_* variables (the seed refuses to run in production without them).
 */
export function demoCredentials(): { admin: Credentials; reviewer: Credentials } {
  if (process.env.NODE_ENV === 'production' && !process.env.SEED_ADMIN_PASSWORD) {
    throw new Error('Set SEED_ADMIN_PASSWORD and SEED_REVIEWER_PASSWORD in production');
  }
  return {
    admin: {
      email: process.env.SEED_ADMIN_EMAIL ?? 'admin@demo.invoiceiq.test',
      password: process.env.SEED_ADMIN_PASSWORD ?? 'demo-admin-password',
    },
    reviewer: {
      email: process.env.SEED_REVIEWER_EMAIL ?? 'reviewer@demo.invoiceiq.test',
      password: process.env.SEED_REVIEWER_PASSWORD ?? 'demo-reviewer-password',
    },
  };
}
