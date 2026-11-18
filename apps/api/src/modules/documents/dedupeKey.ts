import { sha256Hex } from '../../lib/hash';

/**
 * Invoice identity for duplicate detection: sha256 of supplier GSTIN | normalized invoice number |
 * grand total. Mirrored in Python (evals/metrics/dedupe.py); both are checked against
 * evals/fixtures/dedupe_vectors.json.
 */
export function normalizeInvoiceNumber(value: string): string {
  return value.toUpperCase().replace(/[^A-Z0-9]/g, '');
}

export function dedupeKey(
  supplierGstin: string | null | undefined,
  invoiceNumber: string | null | undefined,
  grandTotal: number | null | undefined,
): string | null {
  if (!supplierGstin || !invoiceNumber || grandTotal === null || grandTotal === undefined) {
    return null;
  }
  const gstin = supplierGstin.replace(/[\s-]/g, '').toUpperCase();
  return sha256Hex(`${gstin}|${normalizeInvoiceNumber(invoiceNumber)}|${grandTotal.toFixed(2)}`);
}
