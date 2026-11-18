/** Field kinds, mirroring services/extractor/extractor/schemas/field_types.py. */
export type FieldKind = 'text' | 'date' | 'number';

const DATE_FIELDS = new Set(['invoice_date']);
const TEXT_FIELDS = new Set([
  'supplier_name',
  'supplier_gstin',
  'buyer_name',
  'buyer_gstin',
  'invoice_number',
  'place_of_supply',
  'currency',
  'description',
  'hsn_sac',
  'unit',
]);

export function fieldKind(path: string): FieldKind {
  const name = path.split('.').at(-1) ?? '';
  if (DATE_FIELDS.has(name)) return 'date';
  if (TEXT_FIELDS.has(name)) return 'text';
  return 'number';
}

/** Accepts "1,180.00", "Rs. 1180" or "-0.40"; returns null for anything else. */
export function parseNumber(value: string | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const cleaned = value.replace(/^(rs\.?|inr|₹)\s*/i, '').replace(/[,\s%]/g, '');
  if (!/^[+-]?\d+(\.\d+)?$/.test(cleaned)) return null;
  return Number(cleaned);
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export function parseIsoDate(value: string | null | undefined): Date | null {
  if (!value || !ISO_DATE.test(value)) return null;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== value ? null : date;
}

/** Why a reviewer-entered value is unacceptable for its field, or null if it is fine. */
export function valueProblem(path: string, value: string | null): string | null {
  if (value === null || value.trim() === '') return null;
  const kind = fieldKind(path);
  if (kind === 'number' && parseNumber(value) === null) return 'must be a number';
  if (kind === 'date' && !parseIsoDate(value)) return 'must be a date in YYYY-MM-DD format';
  return null;
}
