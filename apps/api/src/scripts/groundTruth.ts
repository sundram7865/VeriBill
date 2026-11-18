import { fieldKind, parseNumber } from '../modules/invoices/fieldTypes';

const HEADER = [
  'supplier_name',
  'supplier_gstin',
  'buyer_name',
  'buyer_gstin',
  'invoice_number',
  'invoice_date',
  'place_of_supply',
  'currency',
] as const;
const LINE = [
  'description',
  'hsn_sac',
  'quantity',
  'unit',
  'rate',
  'discount',
  'taxable_value',
  'cgst_rate',
  'cgst_amount',
  'sgst_rate',
  'sgst_amount',
  'igst_rate',
  'igst_amount',
] as const;
const TOTALS = ['subtotal', 'total_tax', 'round_off', 'grand_total'] as const;

type Value = string | number | null;

/** Field rows (path/value) -> the invoice JSON shape the Python eval harness expects. */
export function groundTruthFromFields(fields: Array<{ path: string; value: string | null }>) {
  const byPath = new Map(fields.map((f) => [f.path, f.value]));
  const typed = (p: string): Value => {
    const value = byPath.get(p) ?? null;
    return fieldKind(p) === 'number' ? parseNumber(value) : value;
  };
  const lineCount = Math.max(
    0,
    ...fields
      .filter((f) => f.path.startsWith('line_items.'))
      .map((f) => Number(f.path.split('.')[1]) + 1),
  );
  return {
    header: Object.fromEntries(HEADER.map((k) => [k, typed(`header.${k}`)])),
    line_items: Array.from({ length: lineCount }, (_, i) =>
      Object.fromEntries(LINE.map((k) => [k, typed(`line_items.${i}.${k}`)])),
    ),
    totals: Object.fromEntries(TOTALS.map((k) => [k, typed(`totals.${k}`)])),
  };
}
