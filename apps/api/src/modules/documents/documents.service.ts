import type { DocumentStatus } from '@prisma/client';
import type { AppDeps } from '../../app.deps';
import { conflict, notFound } from '../../lib/errors';
import { sha256Hex } from '../../lib/hash';
import type { AuthContext } from '../auth/auth.types';
import { recordAudit } from '../audit/auditLog';
import { fieldsRepository } from '../extraction/fields.repository';
import { checkUpload } from './fileValidation';
import { documentsRepository } from './documents.repository';
import { presentDetail, presentListItem } from './documents.presenter';

export interface IncomingFile {
  originalname: string;
  buffer: Buffer;
}

export interface UploadRejection {
  name: string;
  code: string;
  message: string;
  existingDocumentId?: string;
}

export function documentsService(deps: AppDeps) {
  const docs = documentsRepository(deps.db);
  const limits = {
    maxBytes: deps.config.MAX_UPLOAD_MB * 1024 * 1024,
    maxPages: deps.config.MAX_PAGES,
  };

  async function uploadOne(ctx: AuthContext, file: IncomingFile) {
    const check = checkUpload(file.buffer, limits);
    if (!check.ok)
      return { rejected: { name: file.originalname, code: check.code, message: check.message } };

    // The exact same file again: no second upload and no second LLM bill.
    const contentHash = sha256Hex(file.buffer);
    const existing = await docs.findByContentHash(ctx.tenantId, contentHash);
    if (existing) {
      return {
        rejected: {
          name: file.originalname,
          code: 'duplicate_file',
          message: 'This exact file was already uploaded',
          existingDocumentId: existing.id,
        },
      };
    }

    const stored = await deps.storage.put(file.buffer, {
      tenantId: ctx.tenantId,
      mime: check.mime,
    });
    const doc = await docs.create(ctx.tenantId, {
      uploadedById: ctx.userId,
      storageProvider: stored.provider,
      storagePublicId: stored.publicId,
      storageResourceType: stored.resourceType,
      originalName: file.originalname.slice(0, 255),
      mime: check.mime,
      sizeBytes: file.buffer.length,
      pages: check.pages,
      contentHash,
    });
    await recordAudit(deps.db, {
      tenantId: ctx.tenantId,
      actorId: ctx.userId,
      action: 'document.uploaded',
      entityType: 'document',
      entityId: doc.id,
    });
    await deps.queue.enqueue({
      documentId: doc.id,
      tenantId: ctx.tenantId,
      attempt: doc.processingAttempt,
    });
    return { document: presentListItem({ ...doc, invoice: null }) };
  }

  return {
    async upload(ctx: AuthContext, files: IncomingFile[]) {
      const documents = [];
      const rejected: UploadRejection[] = [];
      for (const file of files) {
        const outcome = await uploadOne(ctx, file);
        if (outcome.document) documents.push(outcome.document);
        if (outcome.rejected) rejected.push(outcome.rejected);
      }
      return { documents, rejected };
    },

    async list(
      ctx: AuthContext,
      query: { status?: DocumentStatus; page: number; pageSize: number },
    ) {
      const [items, total] = await Promise.all([
        docs.list(ctx.tenantId, {
          status: query.status,
          skip: (query.page - 1) * query.pageSize,
          take: query.pageSize,
        }),
        docs.count(ctx.tenantId, query.status),
      ]);
      return {
        items: items.map(presentListItem),
        total,
        page: query.page,
        pageSize: query.pageSize,
      };
    },

    async detail(ctx: AuthContext, id: string) {
      const doc = await docs.detail(ctx.tenantId, id);
      if (!doc) throw notFound('Document not found');
      const run = doc.extractionRuns[0] ?? null;
      const fields = run ? await fieldsRepository(deps.db).listForRun(ctx.tenantId, run.id) : [];
      return presentDetail(doc, run, fields);
    },

    async file(ctx: AuthContext, id: string) {
      const doc = await docs.findById(ctx.tenantId, id);
      if (!doc) throw notFound('Document not found');
      const bytes = await deps.storage.get({
        publicId: doc.storagePublicId,
        resourceType: doc.storageResourceType,
      });
      return { bytes, mime: doc.mime, name: doc.originalName };
    },

    /** Admin action: run the pipeline again (e.g. after a failure or a pipeline upgrade). */
    async reprocess(ctx: AuthContext, id: string) {
      const doc = await docs.findById(ctx.tenantId, id);
      if (!doc) throw notFound('Document not found');
      if (doc.status === 'processing' || doc.status === 'uploaded') {
        throw conflict('Document is already queued or processing');
      }
      const attempt = doc.processingAttempt + 1;
      await docs.update(ctx.tenantId, id, {
        status: 'uploaded',
        processingAttempt: attempt,
        errorMessage: null,
      });
      await recordAudit(deps.db, {
        tenantId: ctx.tenantId,
        actorId: ctx.userId,
        action: 'document.reprocess',
        entityType: 'document',
        entityId: id,
        meta: { attempt },
      });
      await deps.queue.enqueue({ documentId: id, tenantId: ctx.tenantId, attempt });
      return { id, attempt };
    },
  };
}
