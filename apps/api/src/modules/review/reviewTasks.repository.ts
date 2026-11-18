import type { ReviewOutcome, ReviewTask, ReviewTaskStatus, ReviewTaskType } from '@prisma/client';
import { assertTenant, type Db } from '../../lib/db';

export function reviewTasksRepository(db: Db) {
  return {
    create(tenantId: string, documentId: string, type: ReviewTaskType): Promise<ReviewTask> {
      assertTenant(tenantId);
      return db.reviewTask.create({ data: { tenantId, documentId, type } });
    },

    findById(tenantId: string, id: string): Promise<ReviewTask | null> {
      assertTenant(tenantId);
      return db.reviewTask.findFirst({ where: { id, tenantId } });
    },

    list(
      tenantId: string,
      filter: { status?: ReviewTaskStatus; type?: ReviewTaskType; take: number },
    ) {
      assertTenant(tenantId);
      return db.reviewTask.findMany({
        where: {
          tenantId,
          ...(filter.status ? { status: filter.status } : {}),
          ...(filter.type ? { type: filter.type } : {}),
        },
        orderBy: { openedAt: 'asc' },
        take: filter.take,
        include: {
          document: {
            select: {
              id: true,
              originalName: true,
              status: true,
              documentConfidence: true,
              createdAt: true,
            },
          },
        },
      });
    },

    /** Closes the task only if it is still open; false means someone else closed it first. */
    async close(
      tenantId: string,
      id: string,
      outcome: ReviewOutcome,
      userId: string,
    ): Promise<boolean> {
      assertTenant(tenantId);
      const result = await db.reviewTask.updateMany({
        where: { id, tenantId, status: 'open' },
        data: { status: 'closed', outcome, assignedToId: userId, closedAt: new Date() },
      });
      return result.count === 1;
    },

    async closeOpenForDocument(tenantId: string, documentId: string): Promise<void> {
      assertTenant(tenantId);
      await db.reviewTask.updateMany({
        where: { tenantId, documentId, status: 'open' },
        data: { status: 'closed', closedAt: new Date() },
      });
    },
  };
}
