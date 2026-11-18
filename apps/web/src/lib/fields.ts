import type { ExtractedField } from './types';

const LABELS: Record<string, string> = {
  supplier_name: 'Supplier name',
  supplier_gstin: 'Supplier GSTIN',
  buyer_name: 'Buyer name',
  buyer_gstin: 'Buyer GSTIN',
  invoice_number: 'Invoice number',
  invoice_date: 'Invoice date (YYYY-MM-DD)',
  place_of_supply: 'Place of supply',
  currency: 'Currency',
  description: 'Description',
  hsn_sac: 'HSN/SAC',
  quantity: 'Quantity',
  unit: 'Unit',
  rate: 'Rate',
  discount: 'Discount',
  taxable_value: 'Taxable value',
  cgst_rate: 'CGST %',
  cgst_amount: 'CGST',
  sgst_rate: 'SGST %',
  sgst_amount: 'SGST',
  igst_rate: 'IGST %',
  igst_amount: 'IGST',
  subtotal: 'Subtotal',
  total_tax: 'Total tax',
  round_off: 'Round-off',
  grand_total: 'Grand total',
};

export function fieldLabel(path: string): string {
  const name = path.split('.').at(-1) ?? path;
  return LABELS[name] ?? name;
}

export interface FieldGroup {
  key: string;
  title: string;
  fields: ExtractedField[];
}

const HEADER_ORDER = Object.keys(LABELS);

function orderOf(path: string): number {
  return HEADER_ORDER.indexOf(path.split('.').at(-1) ?? '');
}

/** Header, one group per line item (in order), then totals: the order of a printed invoice. */
export function groupFields(fields: ExtractedField[]): FieldGroup[] {
  const header = fields.filter((f) => f.path.startsWith('header.'));
  const totals = fields.filter((f) => f.path.startsWith('totals.'));
  const lines = new Map<number, ExtractedField[]>();
  for (const f of fields) {
    if (!f.path.startsWith('line_items.')) continue;
    const index = Number(f.path.split('.')[1]);
    lines.set(index, [...(lines.get(index) ?? []), f]);
  }
  const byOrder = (a: ExtractedField, b: ExtractedField) => orderOf(a.path) - orderOf(b.path);
  return [
    { key: 'header', title: 'Header', fields: header.sort(byOrder) },
    ...[...lines.entries()]
      .sort(([a], [b]) => a - b)
      .map(([index, group]) => ({
        key: `line-${index}`,
        title: `Line ${index + 1}`,
        fields: group.sort(byOrder),
      })),
    { key: 'totals', title: 'Totals', fields: totals.sort(byOrder) },
  ].filter((g) => g.fields.length > 0);
}

/** Fields in display order: what j/k keyboard navigation walks through. */
export function orderedFields(fields: ExtractedField[]): ExtractedField[] {
  return groupFields(fields).flatMap((g) => g.fields);
}
