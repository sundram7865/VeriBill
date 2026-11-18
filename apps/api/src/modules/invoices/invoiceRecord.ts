import { dedupeKey } from '../documents/dedupeKey';
import { fieldKind, parseIsoDate, parseNumber } from './fieldTypes';

export interface FieldValue {
  path: string;
  value: string | null;
}

export type LineItemRecord = Record<string, string | number | null>;

export interface InvoiceRecord {
  supplierName: string | null;
  supplierGstin: string | null;
  buyerName: string | null;
  buyerGstin: string | null;
  invoiceNumber: string | null;
  invoiceDate: Date | null;
  placeOfSupply: string | null;
  currency: string | null;
  subtotal: number | null;
  totalTax: number | null;
  roundOff: number | null;
  grandTotal: number | null;
  lineItems: LineItemRecord[];
  dedupeKey: string | null;
}

function typed(path: string, value: string | null): string | number | null {
  return fieldKind(path) === 'number' ? parseNumber(value) : value;
}

/** Builds the normalized invoice from the current field values (model output + corrections). */
export function buildInvoiceRecord(fields: FieldValue[]): InvoiceRecord {
  const header = new Map<string, string | null>();
  const totals = new Map<string, number | null>();
  const lines = new Map<number, LineItemRecord>();
  for (const { path, value } of fields) {
    const [section, a, b] = path.split('.');
    if (section === 'header' && a) header.set(a, value);
    else if (section === 'totals' && a) totals.set(a, parseNumber(value));
    else if (section === 'line_items' && a && b) {
      const index = Number(a);
      const line = lines.get(index) ?? {};
      line[b] = typed(path, value);
      lines.set(index, line);
    }
  }
  const supplierGstin = header.get('supplier_gstin') ?? null;
  const invoiceNumber = header.get('invoice_number') ?? null;
  const grandTotal = totals.get('grand_total') ?? null;
  return {
    supplierName: header.get('supplier_name') ?? null,
    supplierGstin,
    buyerName: header.get('buyer_name') ?? null,
    buyerGstin: header.get('buyer_gstin') ?? null,
    invoiceNumber,
    invoiceDate: parseIsoDate(header.get('invoice_date')),
    placeOfSupply: header.get('place_of_supply') ?? null,
    currency: header.get('currency') ?? null,
    subtotal: totals.get('subtotal') ?? null,
    totalTax: totals.get('total_tax') ?? null,
    roundOff: totals.get('round_off') ?? null,
    grandTotal,
    lineItems: [...lines.entries()].sort(([x], [y]) => x - y).map(([, line]) => line),
    dedupeKey: dedupeKey(supplierGstin, invoiceNumber, grandTotal),
  };
}
