/* eslint-disable no-console */
/**
 * Upload a handful of synthetic sample invoices through the running API, like a user would:
 *
 *   python -m evals.generate        # once, creates evals/fixtures/generated/
 *   pnpm seed:samples               # API_URL defaults to http://127.0.0.1:4000/api
 *
 * Going through HTTP means the files land in whatever storage the API uses (local or Cloudinary)
 * and are processed by the real worker. Only needs the API URL and the demo admin's credentials.
 */
import { existsSync } from 'node:fs';
import path from 'node:path';
import { ApiSession } from './apiSession';
import { demoCredentials } from './demoCredentials';

// Five clean digital invoices (one per template), a scan, a wrong total and a prompt injection.
const SAMPLE_CASES = ['c0001', 'c0002', 'c0003', 'c0004', 'c0005', 'c0066', 'c0112', 'c0131'];
const SUITE_FILES = path.resolve(__dirname, '../../../../evals/fixtures/generated/files');

function sampleFiles(): string[] {
  return SAMPLE_CASES.flatMap((id) =>
    ['pdf', 'png', 'jpg'].map((ext) => path.join(SUITE_FILES, `${id}.${ext}`)).filter(existsSync),
  );
}

async function main(): Promise<void> {
  const files = sampleFiles();
  if (files.length === 0) {
    throw new Error('No samples found: run `python -m evals.generate` first');
  }
  const { admin } = demoCredentials();
  const api = new ApiSession(process.env.API_URL ?? 'http://127.0.0.1:4000/api');
  await api.login(admin.email, admin.password);
  const result = await api.upload(files);
  console.log(
    `uploaded ${result.documents.length} sample invoices, ${result.rejected.length} rejected`,
  );
}

main().catch((err: unknown) => {
  console.error(err);
  process.exit(1);
});
