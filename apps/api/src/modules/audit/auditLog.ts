import type { Prisma } from '@prisma/client';
import { assertTenant, type Db } from '../../lib/db';

export interface AuditEntry {
  tenantId: string;
  actorId: string | null;
  action: string; // e.g. "document.uploaded", "review.approved"
  entityType: string;
  entityId: string;
  meta?: Prisma.InputJsonValue; // ids and counts only, never invoice contents
}

/** Append-only: there is deliberately no update or delete function here. */
export async function recordAudit(db: Db, entry: AuditEntry): Promise<void> {
  assertTenant(entry.tenantId);
  await db.auditLog.create({ data: { ...entry, meta: entry.meta ?? {} } });
}
