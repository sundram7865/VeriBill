import type {
  Document,
  ExtractedField,
  ExtractionRun,
  Invoice,
  Prisma,
  ReviewTask,
} from '@prisma/client';

type ListRow = Document & {
  invoice: {
    supplierName: string | null;
    invoiceNumber: string | null;
    grandTotal: Prisma.Decimal | null;
  } | null;
};

/** API shapes. Storage ids never leave the server: the browser only gets our own ids. */
export function presentListItem(doc: ListRow) {
  return {
    id: doc.id,
    originalName: doc.originalName,
    mime: doc.mime,
    pages: doc.pages,
    status: doc.status,
    documentConfidence: doc.documentConfidence,
    duplicateOfId: doc.duplicateOfId,
    errorMessage: doc.errorMessage,
    createdAt: doc.createdAt,
    updatedAt: doc.updatedAt,
    supplierName: doc.invoice?.supplierName ?? null,
    invoiceNumber: doc.invoice?.invoiceNumber ?? null,
    grandTotal: doc.invoice?.grandTotal?.toNumber() ?? null,
  };
}

function presentRun(run: ExtractionRun | null) {
  if (!run) return null;
  const result = run.result as { decision_reason?: string; used_ocr?: boolean };
  return {
    id: run.id,
    attempt: run.attempt,
    model: run.model,
    decision: run.decision,
    decisionReason: result.decision_reason ?? null,
    usedOcr: result.used_ocr ?? false,
    documentConfidence: run.documentConfidence,
    repairAttempts: run.repairAttempts,
    tokensIn: run.tokensIn,
    tokensOut: run.tokensOut,
    costUsd: run.costUsd,
    latencyMs: run.latencyMs,
    nodeTimings: run.nodeTimings,
    createdAt: run.createdAt,
  };
}

function presentInvoice(invoice: Invoice | null) {
  if (!invoice) return null;
  return {
    approvedVia: invoice.approvedVia,
    approvedAt: invoice.approvedAt,
    supplierName: invoice.supplierName,
    invoiceNumber: invoice.invoiceNumber,
    grandTotal: invoice.grandTotal?.toNumber() ?? null,
  };
}

export function presentDetail(
  doc: Document & { reviewTasks: ReviewTask[]; invoice: Invoice | null },
  run: ExtractionRun | null,
  fields: ExtractedField[],
) {
  const openTask = doc.reviewTasks.find((t) => t.status === 'open') ?? null;
  return {
    document: presentListItem({ ...doc, invoice: doc.invoice }),
    run: presentRun(run),
    fields: fields.map((f) => ({
      id: f.id,
      path: f.path,
      value: f.value,
      confidence: f.confidence,
      page: f.page,
      bbox: f.bbox as number[] | null,
      issues: f.issues as Array<{ code: string; severity: string; message: string }>,
    })),
    openTask: openTask
      ? { id: openTask.id, type: openTask.type, openedAt: openTask.openedAt }
      : null,
    reviewHistory: doc.reviewTasks
      .filter((t) => t.status === 'closed')
      .map((t) => ({ id: t.id, type: t.type, outcome: t.outcome, closedAt: t.closedAt })),
    invoice: presentInvoice(doc.invoice),
  };
}
