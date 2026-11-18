import type { Correction } from '@prisma/client';
import { assertTenant, type Db } from '../../lib/db';

export interface NewCorrection {
  reviewTaskId: string;
  documentId: string;
  fieldPath: string;
  before: string | null;
  after: string | null;
  reason: string | null;
  hadValidatorIssue: boolean;
  createdById: string;
}

export function correctionsRepository(db: Db) {
  return {
    async createMany(tenantId: string, corrections: NewCorrection[]): Promise<void> {
      assertTenant(tenantId);
      if (corrections.length === 0) return;
      await db.correction.createMany({ data: corrections.map((c) => ({ ...c, tenantId })) });
    },

    listForTask(tenantId: string, reviewTaskId: string): Promise<Correction[]> {
      assertTenant(tenantId);
      return db.correction.findMany({
        where: { tenantId, reviewTaskId },
        orderBy: { createdAt: 'asc' },
      });
    },

    listForDocuments(tenantId: string, documentIds: string[]): Promise<Correction[]> {
      assertTenant(tenantId);
      return db.correction.findMany({
        where: { tenantId, documentId: { in: documentIds } },
        orderBy: { createdAt: 'desc' },
      });
    },
  };
}
