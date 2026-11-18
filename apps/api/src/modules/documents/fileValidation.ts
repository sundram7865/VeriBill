/** Upload checks done before anything is stored: magic bytes, size and a page-count pre-check. */

export type AllowedMime = 'application/pdf' | 'image/png' | 'image/jpeg';

const SIGNATURES: Array<{ mime: AllowedMime; bytes: number[] }> = [
  { mime: 'application/pdf', bytes: [0x25, 0x50, 0x44, 0x46, 0x2d] }, // %PDF-
  { mime: 'image/png', bytes: [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a] },
  { mime: 'image/jpeg', bytes: [0xff, 0xd8, 0xff] },
];

/** The file type comes from its first bytes, never from the name or the browser's claim. */
export function detectMime(data: Buffer): AllowedMime | null {
  for (const signature of SIGNATURES) {
    if (signature.bytes.every((byte, i) => data[i] === byte)) return signature.mime;
  }
  return null;
}

/**
 * Counts page objects in an uncompressed PDF ("/Type /Page", not "/Pages"). PDFs that keep
 * objects in compressed streams report 0 here; the extractor's ingest node does the
 * authoritative count with PyMuPDF (see DECISIONS D-009).
 */
export function countPdfPagesHeuristic(data: Buffer): number {
  const matches = data.toString('latin1').match(/\/Type\s*\/Page(?![a-zA-Z])/g);
  return matches ? matches.length : 0;
}

export interface UploadLimits {
  maxBytes: number;
  maxPages: number;
}

export type FileCheck =
  | { ok: true; mime: AllowedMime; pages: number | null }
  | { ok: false; code: string; message: string };

export function checkUpload(data: Buffer, limits: UploadLimits): FileCheck {
  if (data.length === 0) return { ok: false, code: 'empty_file', message: 'The file is empty' };
  if (data.length > limits.maxBytes) {
    const mb = Math.round(limits.maxBytes / (1024 * 1024));
    return { ok: false, code: 'file_too_large', message: `Files must be at most ${mb} MB` };
  }
  const mime = detectMime(data);
  if (!mime) {
    return {
      ok: false,
      code: 'unsupported_type',
      message: 'Only PDF, PNG and JPEG files are accepted',
    };
  }
  if (mime !== 'application/pdf') return { ok: true, mime, pages: 1 };
  const pages = countPdfPagesHeuristic(data);
  if (pages > limits.maxPages) {
    return {
      ok: false,
      code: 'too_many_pages',
      message: `PDF has ${pages} pages; the limit is ${limits.maxPages}`,
    };
  }
  return { ok: true, mime, pages: pages > 0 ? pages : null };
}
