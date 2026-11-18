import type { Document, DocumentStatus, Prisma } from '@prisma/client';
import { assertTenant, type Db } from '../../lib/db';

export interface NewDocument {
  uploadedById: string | null;
  storageProvider: string;
  storagePublicId: string;
  storageResourceType: string;
  originalName: string;
  mime: string;
  sizeBytes: number;
  pages: number | null;
  contentHash: string;
}

/** Every query is filtered by tenantId; there is no way to read a document without one. */
export function documentsRepository(db: Db) {
  return {
    create(tenantId: string, data: NewDocument): Promise<Document> {
      assertTenant(tenantId);
      return db.document.create({
        data: { ...data, tenantId, status: 'uploaded', processingAttempt: 1 },
      });
    },

    findById(tenantId: string, id: string): Promise<Document | null> {
      assertTenant(tenantId);
      return db.document.findFirst({ where: { id, tenantId } });
    },

    findByContentHash(tenantId: string, contentHash: string): Promise<Document | null> {
      assertTenant(tenantId);
      return db.document.findFirst({
        where: { tenantId, contentHash, status: { not: 'failed' } },
        orderBy: { createdAt: 'asc' },
      });
    },

    /** Another live document of this tenant with the same invoice identity, if any. */
    findByDedupeKey(
      tenantId: string,
      dedupeKey: string,
      excludeId: string,
    ): Promise<Document | null> {
      assertTenant(tenantId);
      return db.document.findFirst({
        where: {
          tenantId,
          dedupeKey,
          id: { not: excludeId },
          status: { notIn: ['rejected', 'failed'] },
        },
        orderBy: { createdAt: 'asc' },
      });
    },

    list(
      tenantId: string,
      filter: { status?: DocumentStatus; skip: number; take: number },
    ): Promise<
      Array<
        Document & {
          invoice: {
            supplierName: string | null;
            invoiceNumber: string | null;
            grandTotal: Prisma.Decimal | null;
          } | null;
        }
      >
    > {
      assertTenant(tenantId);
      return db.document.findMany({
        where: { tenantId, ...(filter.status ? { status: filter.status } : {}) },
        orderBy: { createdAt: 'desc' },
        skip: filter.skip,
        take: filter.take,
        include: {
          invoice: { select: { supplierName: true, invoiceNumber: true, grandTotal: true } },
        },
      });
    },

    count(tenantId: string, status?: DocumentStatus): Promise<number> {
      assertTenant(tenantId);
      return db.document.count({ where: { tenantId, ...(status ? { status } : {}) } });
    },

    async update(
      tenantId: string,
      id: string,
      data: Prisma.DocumentUncheckedUpdateManyInput,
    ): Promise<boolean> {
      assertTenant(tenantId);
      const result = await db.document.updateMany({ where: { id, tenantId }, data });
      return result.count === 1;
    },

    /** Everything the review screen needs, from the latest extraction run. */
    detail(tenantId: string, id: string) {
      assertTenant(tenantId);
      return db.document.findFirst({
        where: { id, tenantId },
        include: {
          extractionRuns: { orderBy: { attempt: 'desc' }, take: 1 },
          reviewTasks: { orderBy: { openedAt: 'desc' } },
          invoice: true,
        },
      });
    },
  };
}

export type DocumentsRepository = ReturnType<typeof documentsRepository>;
