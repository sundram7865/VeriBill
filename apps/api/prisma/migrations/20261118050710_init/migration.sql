-- CreateEnum
CREATE TYPE "UserRole" AS ENUM ('admin', 'reviewer');

-- CreateEnum
CREATE TYPE "DocumentStatus" AS ENUM ('uploaded', 'processing', 'auto_approved', 'needs_review', 'approved', 'rejected', 'failed');

-- CreateEnum
CREATE TYPE "ReviewTaskType" AS ENUM ('needs_review', 'audit');

-- CreateEnum
CREATE TYPE "ReviewTaskStatus" AS ENUM ('open', 'closed');

-- CreateEnum
CREATE TYPE "ReviewOutcome" AS ENUM ('approved', 'rejected');

-- CreateTable
CREATE TABLE "tenants" (
    "id" UUID NOT NULL,
    "name" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "tenants_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "users" (
    "id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "email" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "password_hash" TEXT NOT NULL,
    "role" "UserRole" NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "refresh_tokens" (
    "id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "token_hash" TEXT NOT NULL,
    "family_id" UUID NOT NULL,
    "expires_at" TIMESTAMP(3) NOT NULL,
    "revoked_at" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "refresh_tokens_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "documents" (
    "id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "uploaded_by_id" UUID,
    "storage_provider" TEXT NOT NULL,
    "storage_public_id" TEXT NOT NULL,
    "storage_resource_type" TEXT NOT NULL,
    "original_name" TEXT NOT NULL,
    "mime" TEXT NOT NULL,
    "size_bytes" INTEGER NOT NULL,
    "pages" INTEGER,
    "status" "DocumentStatus" NOT NULL DEFAULT 'uploaded',
    "content_hash" TEXT NOT NULL,
    "dedupe_key" TEXT,
    "duplicate_of" UUID,
    "processing_attempt" INTEGER NOT NULL DEFAULT 0,
    "document_confidence" DOUBLE PRECISION,
    "error_message" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "documents_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "extraction_runs" (
    "id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "document_id" UUID NOT NULL,
    "attempt" INTEGER NOT NULL,
    "model" TEXT NOT NULL,
    "tokens_in" INTEGER NOT NULL,
    "tokens_out" INTEGER NOT NULL,
    "cost_usd" DOUBLE PRECISION NOT NULL,
    "latency_ms" INTEGER NOT NULL,
    "node_timings" JSONB NOT NULL,
    "repair_attempts" INTEGER NOT NULL,
    "decision" TEXT NOT NULL,
    "document_confidence" DOUBLE PRECISION NOT NULL,
    "result" JSONB NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "extraction_runs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "extracted_fields" (
    "id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "document_id" UUID NOT NULL,
    "run_id" UUID NOT NULL,
    "path" TEXT NOT NULL,
    "value" TEXT,
    "confidence" DOUBLE PRECISION NOT NULL,
    "page" INTEGER,
    "bbox" JSONB,
    "issues" JSONB NOT NULL DEFAULT '[]',

    CONSTRAINT "extracted_fields_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "review_tasks" (
    "id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "document_id" UUID NOT NULL,
    "type" "ReviewTaskType" NOT NULL,
    "status" "ReviewTaskStatus" NOT NULL DEFAULT 'open',
    "outcome" "ReviewOutcome",
    "assigned_to" UUID,
    "opened_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "closed_at" TIMESTAMP(3),

    CONSTRAINT "review_tasks_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "corrections" (
    "id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "review_task_id" UUID NOT NULL,
    "document_id" UUID NOT NULL,
    "field_path" TEXT NOT NULL,
    "before" TEXT,
    "after" TEXT,
    "reason" TEXT,
    "had_validator_issue" BOOLEAN NOT NULL DEFAULT false,
    "created_by_id" UUID,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "corrections_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "invoices" (
    "id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "document_id" UUID NOT NULL,
    "supplier_id" UUID,
    "supplier_name" TEXT,
    "supplier_gstin" TEXT,
    "buyer_name" TEXT,
    "buyer_gstin" TEXT,
    "invoice_number" TEXT,
    "invoice_date" DATE,
    "place_of_supply" TEXT,
    "currency" TEXT,
    "subtotal" DECIMAL(14,2),
    "total_tax" DECIMAL(14,2),
    "round_off" DECIMAL(14,2),
    "grand_total" DECIMAL(14,2),
    "line_items" JSONB NOT NULL,
    "dedupe_key" TEXT,
    "approved_via" TEXT NOT NULL,
    "approved_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "invoices_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "suppliers" (
    "id" UUID NOT NULL,
    "tenant_id" UUID NOT NULL,
    "gstin" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "suppliers_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "audit_log" (
    "id" BIGSERIAL NOT NULL,
    "tenant_id" UUID NOT NULL,
    "actor_id" UUID,
    "action" TEXT NOT NULL,
    "entity_type" TEXT NOT NULL,
    "entity_id" TEXT NOT NULL,
    "meta" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "audit_log_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE INDEX "users_tenant_id_idx" ON "users"("tenant_id");

-- CreateIndex
CREATE UNIQUE INDEX "refresh_tokens_token_hash_key" ON "refresh_tokens"("token_hash");

-- CreateIndex
CREATE INDEX "refresh_tokens_family_id_idx" ON "refresh_tokens"("family_id");

-- CreateIndex
CREATE INDEX "documents_tenant_id_status_idx" ON "documents"("tenant_id", "status");

-- CreateIndex
CREATE INDEX "documents_tenant_id_content_hash_idx" ON "documents"("tenant_id", "content_hash");

-- CreateIndex
CREATE INDEX "documents_tenant_id_dedupe_key_idx" ON "documents"("tenant_id", "dedupe_key");

-- CreateIndex
CREATE INDEX "documents_tenant_id_created_at_idx" ON "documents"("tenant_id", "created_at");

-- CreateIndex
CREATE INDEX "extraction_runs_tenant_id_created_at_idx" ON "extraction_runs"("tenant_id", "created_at");

-- CreateIndex
CREATE UNIQUE INDEX "extraction_runs_document_id_attempt_key" ON "extraction_runs"("document_id", "attempt");

-- CreateIndex
CREATE INDEX "extracted_fields_tenant_id_document_id_idx" ON "extracted_fields"("tenant_id", "document_id");

-- CreateIndex
CREATE UNIQUE INDEX "extracted_fields_run_id_path_key" ON "extracted_fields"("run_id", "path");

-- CreateIndex
CREATE INDEX "review_tasks_tenant_id_status_type_idx" ON "review_tasks"("tenant_id", "status", "type");

-- CreateIndex
CREATE INDEX "review_tasks_document_id_idx" ON "review_tasks"("document_id");

-- CreateIndex
CREATE INDEX "corrections_tenant_id_created_at_idx" ON "corrections"("tenant_id", "created_at");

-- CreateIndex
CREATE INDEX "corrections_document_id_idx" ON "corrections"("document_id");

-- CreateIndex
CREATE UNIQUE INDEX "invoices_document_id_key" ON "invoices"("document_id");

-- CreateIndex
CREATE INDEX "invoices_tenant_id_supplier_gstin_idx" ON "invoices"("tenant_id", "supplier_gstin");

-- CreateIndex
CREATE INDEX "invoices_tenant_id_invoice_date_idx" ON "invoices"("tenant_id", "invoice_date");

-- CreateIndex
CREATE INDEX "invoices_tenant_id_grand_total_idx" ON "invoices"("tenant_id", "grand_total");

-- CreateIndex
CREATE UNIQUE INDEX "suppliers_tenant_id_gstin_key" ON "suppliers"("tenant_id", "gstin");

-- CreateIndex
CREATE INDEX "audit_log_tenant_id_created_at_idx" ON "audit_log"("tenant_id", "created_at");

-- AddForeignKey
ALTER TABLE "users" ADD CONSTRAINT "users_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "tenants"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "refresh_tokens" ADD CONSTRAINT "refresh_tokens_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "documents" ADD CONSTRAINT "documents_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "tenants"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "documents" ADD CONSTRAINT "documents_duplicate_of_fkey" FOREIGN KEY ("duplicate_of") REFERENCES "documents"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "extraction_runs" ADD CONSTRAINT "extraction_runs_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "documents"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "extracted_fields" ADD CONSTRAINT "extracted_fields_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "documents"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "extracted_fields" ADD CONSTRAINT "extracted_fields_run_id_fkey" FOREIGN KEY ("run_id") REFERENCES "extraction_runs"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "review_tasks" ADD CONSTRAINT "review_tasks_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "documents"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "corrections" ADD CONSTRAINT "corrections_review_task_id_fkey" FOREIGN KEY ("review_task_id") REFERENCES "review_tasks"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "invoices" ADD CONSTRAINT "invoices_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "documents"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "invoices" ADD CONSTRAINT "invoices_supplier_id_fkey" FOREIGN KEY ("supplier_id") REFERENCES "suppliers"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "suppliers" ADD CONSTRAINT "suppliers_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "tenants"("id") ON DELETE CASCADE ON UPDATE CASCADE;
