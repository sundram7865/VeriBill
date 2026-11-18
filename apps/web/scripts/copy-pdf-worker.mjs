// Copies the pdf.js worker into public/ so the static export can serve it from our own
// origin. Bundler-specific worker imports are fragile under static export; a plain file is not.
import { copyFileSync, existsSync, mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const pdfjsDir = path.dirname(require.resolve('pdfjs-dist/package.json'));
const source = path.join(pdfjsDir, 'build', 'pdf.worker.min.mjs');
const targetDir = path.join(here, '..', 'public');

if (!existsSync(source)) {
  console.error(`pdf.js worker not found at ${source}`);
  process.exit(1);
}
mkdirSync(targetDir, { recursive: true });
copyFileSync(source, path.join(targetDir, 'pdf.worker.min.mjs'));
