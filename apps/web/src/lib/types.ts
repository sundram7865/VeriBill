/** Shapes returned by the API (apps/api). Kept small and explicit on purpose. */

export type Role = 'admin' | 'reviewer';

export interface User {
  id: string;
  email: string;
  name: string;
  role: Role;
  tenantId: string;
}

export type DocumentStatus =
  'uploaded' | 'processing' | 'auto_approved' | 'needs_review' | 'approved' | 'rejected' | 'failed';

export interface DocumentSummary {
  id: string;
  originalName: string;
  mime: string;
  pages: number | null;
  status: DocumentStatus;
  documentConfidence: number | null;
  duplicateOfId: string | null;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
  supplierName: string | null;
  invoiceNumber: string | null;
  grandTotal: number | null;
}

export interface DocumentList {
  items: DocumentSummary[];
  total: number;
  page: number;
  pageSize: number;
}

export interface FieldIssue {
  code: string;
  severity: 'error' | 'warn';
  message: string;
}

export interface ExtractedField {
  id: string;
  path: string;
  value: string | null;
  confidence: number;
  page: number | null;
  bbox: [number, number, number, number] | null;
  issues: FieldIssue[];
}

export interface RunSummary {
  id: string;
  attempt: number;
  model: string;
  decision: string;
  decisionReason: string | null;
  usedOcr: boolean;
  documentConfidence: number;
  repairAttempts: number;
  tokensIn: number;
  tokensOut: number;
  costUsd: number;
  latencyMs: number;
}

export interface DocumentDetail {
  document: DocumentSummary;
  run: RunSummary | null;
  fields: ExtractedField[];
  openTask: { id: string; type: 'needs_review' | 'audit'; openedAt: string } | null;
  reviewHistory: Array<{
    id: string;
    type: string;
    outcome: string | null;
    closedAt: string | null;
  }>;
  invoice: { approvedVia: string; approvedAt: string; grandTotal: number | null } | null;
}

export interface ReviewTaskItem {
  id: string;
  documentId: string;
  type: 'needs_review' | 'audit';
  status: 'open' | 'closed';
  openedAt: string;
  document: {
    id: string;
    originalName: string;
    status: DocumentStatus;
    documentConfidence: number | null;
    createdAt: string;
  };
}

export interface Metrics {
  windowDays: number;
  documentsByStatus: Partial<Record<DocumentStatus, number>>;
  openReviewTasks: Partial<Record<'needs_review' | 'audit', number>>;
  extractionRuns: number;
  autoApprovalRate: number | null;
  auditedAccuracy: number | null;
  auditedDocuments: number;
  fieldCorrectionRate: number | null;
  corrections: number;
  validatorCatchRate: number | null;
  costPerDocumentUsd: number | null;
  totalCostUsd: number;
  latencyMs: { p50: number | null; p95: number | null };
}

export interface UploadResult {
  documents: DocumentSummary[];
  rejected: Array<{ name: string; code: string; message: string; existingDocumentId?: string }>;
}

export interface ApiErrorBody {
  error: { code: string; message: string; details?: unknown };
}
