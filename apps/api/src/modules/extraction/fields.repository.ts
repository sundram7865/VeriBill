import type { ExtractedField, Prisma } from '@prisma/client';
import { assertTenant, type Db } from '../../lib/db';

export interface NewField {
  path: string;
  value: string | null;
  confidence: number;
  page: number | null;
  bbox: Prisma.InputJsonValue | null;
  issues: Prisma.InputJsonValue;
}

export function fieldsRepository(db: Db) {
  return {
    async createMany(
      tenantId: string,
      documentId: string,
      runId: string,
      fields: NewField[],
    ): Promise<void> {
      assertTenant(tenantId);
      await db.extractedField.createMany({
        data: fields.map((f) => ({
          tenantId,
          documentId,
          runId,
          path: f.path,
          value: f.value,
          confidence: f.confidence,
          page: f.page,
          bbox: f.bbox ?? undefined,
          issues: f.issues,
        })),
      });
    },

    listForRun(tenantId: string, runId: string): Promise<ExtractedField[]> {
      assertTenant(tenantId);
      return db.extractedField.findMany({ where: { tenantId, runId }, orderBy: { path: 'asc' } });
    },

    async updateValue(tenantId: string, id: string, value: string | null): Promise<void> {
      assertTenant(tenantId);
      await db.extractedField.updateMany({ where: { id, tenantId }, data: { value } });
    },
  };
}
