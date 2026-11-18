import type { Invoice } from '@prisma/client';
import type { AppDeps } from '../../app.deps';
import { assertTenant } from '../../lib/db';
import type { AuthContext } from '../auth/auth.types';
import type { LineItemRecord } from '../invoices/invoiceRecord';
import { csvLine, type Cell } from './csv';

const HEADER_COLUMNS = [
  'document_id',
  'invoice_number',
  'invoice_date',
  'supplier_name',
  'supplier_gstin',
  'buyer_name',
  'buyer_gstin',
  'place_of_supply',
  'currency',
  'subtotal',
  'total_tax',
  'round_off',
  'grand_total',
  'approved_via',
] as const;
const LINE_COLUMNS = [
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

export interface ExportRange {
  from?: Date;
  to?: Date;
}

function headerCells(inv: Invoice): Cell[] {
  return [
    inv.documentId,
    inv.invoiceNumber,
    inv.invoiceDate?.toISOString().slice(0, 10),
    inv.supplierName,
    inv.supplierGstin,
    inv.buyerName,
    inv.buyerGstin,
    inv.placeOfSupply,
    inv.currency,
    inv.subtotal?.toNumber(),
    inv.totalTax?.toNumber(),
    inv.roundOff?.toNumber(),
    inv.grandTotal?.toNumber(),
    inv.approvedVia,
  ];
}

function toJson(inv: Invoice) {
  return {
    documentId: inv.documentId,
    invoiceNumber: inv.invoiceNumber,
    invoiceDate: inv.invoiceDate?.toISOString().slice(0, 10) ?? null,
    supplier: { name: inv.supplierName, gstin: inv.supplierGstin },
    buyer: { name: inv.buyerName, gstin: inv.buyerGstin },
    placeOfSupply: inv.placeOfSupply,
    currency: inv.currency,
    lineItems: inv.lineItems,
    totals: {
      subtotal: inv.subtotal?.toNumber() ?? null,
      totalTax: inv.totalTax?.toNumber() ?? null,
      roundOff: inv.roundOff?.toNumber() ?? null,
      grandTotal: inv.grandTotal?.toNumber() ?? null,
    },
    approvedVia: inv.approvedVia,
    approvedAt: inv.approvedAt,
  };
}

/** Approved invoices only (human-approved or auto-approved), one CSV row per line item. */
export function exportService(deps: AppDeps) {
  async function approvedInvoices(ctx: AuthContext, range: ExportRange): Promise<Invoice[]> {
    assertTenant(ctx.tenantId);
    return deps.db.invoice.findMany({
      where: {
        tenantId: ctx.tenantId,
        document: { status: { in: ['approved', 'auto_approved'] } },
        ...(range.from || range.to ? { invoiceDate: { gte: range.from, lte: range.to } } : {}),
      },
      orderBy: [{ invoiceDate: 'asc' }, { approvedAt: 'asc' }],
    });
  }

  return {
    async csv(ctx: AuthContext, range: ExportRange): Promise<string> {
      const lines = [csvLine(['line_no', ...HEADER_COLUMNS, ...LINE_COLUMNS])];
      for (const inv of await approvedInvoices(ctx, range)) {
        const items = (inv.lineItems as LineItemRecord[]) ?? [];
        const rows = items.length > 0 ? items : [{}];
        rows.forEach((item, index) => {
          lines.push(
            csvLine([
              index + 1,
              ...headerCells(inv),
              ...LINE_COLUMNS.map((c) => (item as LineItemRecord)[c]),
            ]),
          );
        });
      }
      return lines.join('\r\n') + '\r\n';
    },

    async json(ctx: AuthContext, range: ExportRange) {
      return (await approvedInvoices(ctx, range)).map(toJson);
    },
  };
}
