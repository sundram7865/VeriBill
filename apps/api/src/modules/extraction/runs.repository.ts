import type { ExtractionRun, Prisma } from '@prisma/client';
import { assertTenant, type Db } from '../../lib/db';

export interface NewRun {
  documentId: string;
  attempt: number;
  model: string;
  tokensIn: number;
  tokensOut: number;
  costUsd: number;
  latencyMs: number;
  nodeTimings: Prisma.InputJsonValue;
  repairAttempts: number;
  decision: string;
  documentConfidence: number;
  result: Prisma.InputJsonValue;
}

export function runsRepository(db: Db) {
  return {
    create(tenantId: string, data: NewRun): Promise<ExtractionRun> {
      assertTenant(tenantId);
      return db.extractionRun.create({ data: { ...data, tenantId } });
    },

    find(tenantId: string, documentId: string, attempt: number): Promise<ExtractionRun | null> {
      assertTenant(tenantId);
      return db.extractionRun.findFirst({ where: { tenantId, documentId, attempt } });
    },

    latest(tenantId: string, documentId: string): Promise<ExtractionRun | null> {
      assertTenant(tenantId);
      return db.extractionRun.findFirst({
        where: { tenantId, documentId },
        orderBy: { attempt: 'desc' },
      });
    },
  };
}
