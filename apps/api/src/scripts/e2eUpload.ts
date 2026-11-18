/* eslint-disable no-console */
/**
 * End-to-end check against a running stack: log in, upload one synthetic invoice, wait for the
 * worker and extractor, print the stored result.
 *
 *   pnpm e2e [path/to/invoice.pdf]
 *
 * Exits 0 when the document reaches a stored decision (auto_approved / needs_review / rejected),
 * 1 when it ends in "failed" or times out.
 */
import path from 'node:path';
import { ApiSession } from './apiSession';
import { demoCredentials } from './demoCredentials';

const DONE = new Set(['auto_approved', 'needs_review', 'rejected', 'approved', 'failed']);
const DEFAULT_FILE = path.resolve(
  __dirname,
  '../../../../evals/fixtures/generated/files/c0001.pdf',
);

interface Detail {
  document: { status: string; errorMessage: string | null };
  run: { decision: string; costUsd: number; latencyMs: number; repairAttempts: number } | null;
  fields: unknown[];
}

async function main(): Promise<void> {
  const api = new ApiSession(process.env.API_URL ?? 'http://127.0.0.1:4000/api');
  const { admin } = demoCredentials();
  await api.login(admin.email, admin.password);
  const file = process.argv[2] ?? DEFAULT_FILE;
  const uploaded = await api.upload([file]);
  const doc = uploaded.documents[0];
  if (!doc) throw new Error(`upload rejected: ${JSON.stringify(uploaded.rejected)}`);
  console.log(`uploaded ${doc.originalName} as ${doc.id}`);

  const deadline = Date.now() + Number(process.env.E2E_TIMEOUT_MS ?? 180_000);
  while (Date.now() < deadline) {
    const detail = await api.get<Detail>(`/documents/${doc.id}`);
    if (DONE.has(detail.document.status)) {
      console.log(
        JSON.stringify(
          {
            status: detail.document.status,
            error: detail.document.errorMessage,
            decision: detail.run?.decision ?? null,
            fields: detail.fields.length,
            costUsd: detail.run?.costUsd ?? null,
            latencyMs: detail.run?.latencyMs ?? null,
            repairs: detail.run?.repairAttempts ?? null,
          },
          null,
          2,
        ),
      );
      process.exit(detail.document.status === 'failed' ? 1 : 0);
    }
    await new Promise((r) => setTimeout(r, 1500));
  }
  console.error('timed out waiting for the worker');
  process.exit(1);
}

main().catch((err: unknown) => {
  console.error(err);
  process.exit(1);
});
