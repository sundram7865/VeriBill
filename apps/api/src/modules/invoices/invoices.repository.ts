import { Prisma, type Invoice } from '@prisma/client';
import { assertTenant, type Db } from '../../lib/db';
import type { InvoiceRecord } from './invoiceRecord';

export interface InvoiceSearch {
  supplier?: string; // name substring or exact GSTIN
  from?: Date;
  to?: Date;
  minAmount?: number;
  maxAmount?: number;
  take: number;
}

function toData(record: InvoiceRecord) {
  const { lineItems, ...rest } = record;
  return { ...rest, lineItems: lineItems as Prisma.InputJsonValue };
}

export function invoicesRepository(db: Db) {
  return {
    async upsertForDocument(
      tenantId: string,
      documentId: string,
      record: InvoiceRecord,
      approvedVia: 'auto' | 'review',
    ): Promise<Invoice> {
      assertTenant(tenantId);
      const supplier = record.supplierGstin
        ? await db.supplier.upsert({
            where: { tenantId_gstin: { tenantId, gstin: record.supplierGstin } },
            create: { tenantId, gstin: record.supplierGstin, name: record.supplierName ?? '' },
            update: record.supplierName ? { name: record.supplierName } : {},
          })
        : null;
      const data = { ...toData(record), supplierId: supplier?.id ?? null, approvedVia };
      return db.invoice.upsert({
        where: { documentId },
        create: { ...data, tenantId, documentId },
        update: data,
      });
    },

    async deleteForDocument(tenantId: string, documentId: string): Promise<void> {
      assertTenant(tenantId);
      await db.invoice.deleteMany({ where: { tenantId, documentId } });
    },

    search(tenantId: string, query: InvoiceSearch): Promise<Invoice[]> {
      assertTenant(tenantId);
      const where: Prisma.InvoiceWhereInput = { tenantId };
      if (query.supplier) {
        where.OR = [
          { supplierName: { contains: query.supplier, mode: 'insensitive' } },
          { supplierGstin: query.supplier.toUpperCase() },
        ];
      }
      if (query.from || query.to) where.invoiceDate = { gte: query.from, lte: query.to };
      if (query.minAmount !== undefined || query.maxAmount !== undefined) {
        where.grandTotal = { gte: query.minAmount, lte: query.maxAmount };
      }
      return db.invoice.findMany({ where, orderBy: { invoiceDate: 'desc' }, take: query.take });
    },

    findByDocument(tenantId: string, documentId: string): Promise<Invoice | null> {
      assertTenant(tenantId);
      return db.invoice.findFirst({ where: { tenantId, documentId } });
    },
  };
}
