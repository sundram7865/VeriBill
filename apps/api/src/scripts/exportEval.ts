/* eslint-disable no-console */
/**
 * Turn reviewer-approved documents into eval cases: pnpm export:eval [-- --tenant <name>]
 *
 * Writes evals/fixtures/corrections/{manifest.json,files/*} in the same format as the synthetic
 * suite, with the human-approved field values as ground truth. Then:
 *   python -m evals.run --suite-dir evals/fixtures/corrections --extractor pipeline
 * Must run where the API's storage is reachable (Cloudinary, or the same disk for local).
 */
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { PrismaClient } from '@prisma/client';
import { env } from '../config/env';
import { createStorage } from '../storage/createStorage';
import { groundTruthFromFields } from './groundTruth';
import { DEMO_TENANT } from './seedData';

const OUT_DIR = path.resolve(__dirname, '../../../../evals/fixtures/corrections');
const EXTENSIONS: Record<string, string> = {
  'application/pdf': 'pdf',
  'image/png': 'png',
  'image/jpeg': 'jpg',
};

async function main(): Promise<void> {
  const tenantFlag = process.argv.indexOf('--tenant');
  const tenantName = tenantFlag > 0 ? process.argv[tenantFlag + 1] : DEMO_TENANT;
  const db = new PrismaClient();
  const storage = createStorage(env());
  try {
    const tenant = await db.tenant.findFirst({ where: { name: tenantName } });
    if (!tenant) throw new Error(`tenant "${tenantName}" not found`);
    // Every document a human closed with "approve" is labelled data, corrected or not.
    const tasks = await db.reviewTask.findMany({
      where: { tenantId: tenant.id, status: 'closed', outcome: 'approved' },
      include: { document: true, corrections: true },
      orderBy: { closedAt: 'asc' },
    });
    await mkdir(path.join(OUT_DIR, 'files'), { recursive: true });
    const cases = [];
    const seen = new Set<string>();
    for (const task of tasks) {
      const doc = task.document;
      if (seen.has(doc.id)) continue;
      seen.add(doc.id);
      const run = await db.extractionRun.findFirst({
        where: { tenantId: tenant.id, documentId: doc.id },
        orderBy: { attempt: 'desc' },
      });
      if (!run) continue;
      const fields = await db.extractedField.findMany({
        where: { tenantId: tenant.id, runId: run.id },
      });
      const file = `files/${doc.id}.${EXTENSIONS[doc.mime] ?? 'bin'}`;
      const bytes = await storage.get({
        publicId: doc.storagePublicId,
        resourceType: doc.storageResourceType,
      });
      await writeFile(path.join(OUT_DIR, file), bytes);
      cases.push({
        id: doc.id,
        file,
        mime: doc.mime,
        split: 'test',
        template: 'uploaded',
        variant: 'uploaded',
        trick: null,
        duplicate_of: null,
        pages: doc.pages ?? 1,
        expected_issue_paths: [],
        corrected_paths: task.corrections.map((c) => c.fieldPath),
        ground_truth: groundTruthFromFields(fields),
      });
    }
    const manifest = {
      suite: 'corrections',
      seed: 0,
      reference_date: new Date().toISOString().slice(0, 10),
      cases,
    };
    await writeFile(path.join(OUT_DIR, 'manifest.json'), JSON.stringify(manifest, null, 2));
    console.log(`wrote ${cases.length} eval cases to ${OUT_DIR}`);
  } finally {
    await db.$disconnect();
  }
}

main().catch((err: unknown) => {
  console.error(err);
  process.exit(1);
});
