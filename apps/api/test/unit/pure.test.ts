import { readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { dedupeKey } from '../../src/modules/documents/dedupeKey';
import {
  checkUpload,
  countPdfPagesHeuristic,
  detectMime,
} from '../../src/modules/documents/fileValidation';
import { csvCell, csvLine } from '../../src/modules/export/csv';
import { parseNumber, valueProblem } from '../../src/modules/invoices/fieldTypes';
import { buildInvoiceRecord } from '../../src/modules/invoices/invoiceRecord';
import { hashPassword, verifyPassword } from '../../src/modules/auth/password';
import { shouldAudit } from '../../src/modules/review/auditSampling';
import { CLEAN_FIELDS } from '../helpers/fakeExtractor';
import { pdfWithPages, tinyPdf, tinyPng } from '../helpers/files';

const LIMITS = { maxBytes: 10 * 1024 * 1024, maxPages: 20 };

describe('file validation', () => {
  it('detects type from magic bytes', () => {
    expect(detectMime(tinyPdf())).toBe('application/pdf');
    expect(detectMime(tinyPng())).toBe('image/png');
    expect(detectMime(Buffer.from([0xff, 0xd8, 0xff, 0xe0]))).toBe('image/jpeg');
    expect(detectMime(Buffer.from('GIF89a'))).toBeNull();
  });

  it('counts pages but not the /Pages tree node', () => {
    expect(countPdfPagesHeuristic(pdfWithPages(3))).toBe(3);
  });

  it('enforces size and page limits', () => {
    expect(checkUpload(Buffer.alloc(0), LIMITS)).toMatchObject({ ok: false, code: 'empty_file' });
    expect(checkUpload(pdfWithPages(21), LIMITS)).toMatchObject({
      ok: false,
      code: 'too_many_pages',
    });
    expect(checkUpload(tinyPdf(), { ...LIMITS, maxBytes: 10 })).toMatchObject({
      code: 'file_too_large',
    });
    expect(checkUpload(pdfWithPages(20), LIMITS)).toMatchObject({ ok: true, pages: 20 });
  });
});

describe('dedupe key', () => {
  it('matches the Python implementation on shared vectors', () => {
    const vectors = JSON.parse(
      readFileSync(
        path.resolve(__dirname, '../../../../evals/fixtures/dedupe_vectors.json'),
        'utf8',
      ),
    ) as Array<{
      supplier_gstin: string | null;
      invoice_number: string;
      grand_total: number;
      key: string | null;
    }>;
    for (const v of vectors) {
      expect(dedupeKey(v.supplier_gstin, v.invoice_number, v.grand_total)).toBe(v.key);
    }
  });
});

describe('csv', () => {
  it('quotes, escapes and defuses formulas but keeps negative numbers', () => {
    expect(csvCell('a,b')).toBe('"a,b"');
    expect(csvCell('say "hi"')).toBe('"say ""hi"""');
    expect(csvCell('=HYPERLINK("x")')).toBe(`"'=HYPERLINK(""x"")"`);
    expect(csvCell(-0.4)).toBe('-0.4');
    expect(csvLine(['x', null, 3])).toBe('x,,3');
  });
});

describe('field types and invoice records', () => {
  it('parses human-entered numbers', () => {
    expect(parseNumber('Rs. 1,23,456.50')).toBe(123456.5);
    expect(parseNumber('9%')).toBe(9);
    expect(parseNumber('abc')).toBeNull();
  });

  it('validates corrected values', () => {
    expect(valueProblem('header.invoice_date', '2026-02-30')).toMatch(/YYYY-MM-DD/);
    expect(valueProblem('header.invoice_date', '2026-02-28')).toBeNull();
    expect(valueProblem('line_items.0.rate', '12.5')).toBeNull();
    expect(valueProblem('header.supplier_name', 'anything')).toBeNull();
  });

  it('builds a typed invoice record from field values', () => {
    const record = buildInvoiceRecord(
      Object.entries(CLEAN_FIELDS).map(([p, value]) => ({ path: p, value })),
    );
    expect(record.grandTotal).toBe(1180);
    expect(record.invoiceDate?.toISOString().slice(0, 10)).toBe('2026-03-15');
    expect(record.lineItems).toHaveLength(1);
    expect(record.lineItems[0]).toMatchObject({
      description: 'Copper Wire 2.5 sq mm',
      quantity: 10,
      igst_amount: null,
    });
    expect(record.dedupeKey).toBe(dedupeKey('27AAPFU0939F1ZV', 'INV/2025-26/0042', 1180));
  });
});

describe('passwords', () => {
  it('hashes with a salt and verifies', async () => {
    const a = await hashPassword('s3cret');
    const b = await hashPassword('s3cret');
    expect(a).not.toBe(b);
    expect(await verifyPassword('s3cret', a)).toBe(true);
    expect(await verifyPassword('wrong', a)).toBe(false);
    expect(await verifyPassword('s3cret', 'garbage')).toBe(false);
  });
});

describe('audit sampling', () => {
  it('is deterministic and close to the configured rate', () => {
    const ids = Array.from(
      { length: 2000 },
      (_, i) => `00000000-0000-4000-8000-${String(i).padStart(12, '0')}`,
    );
    const sampled = ids.filter((id) => shouldAudit(id, 0.1)).length;
    expect(sampled / ids.length).toBeGreaterThan(0.07);
    expect(sampled / ids.length).toBeLessThan(0.13);
    expect(shouldAudit(ids[0] as string, 0.1)).toBe(shouldAudit(ids[0] as string, 0.1));
    expect(shouldAudit(ids[0] as string, 0)).toBe(false);
    expect(shouldAudit(ids[0] as string, 1)).toBe(true);
  });
});
