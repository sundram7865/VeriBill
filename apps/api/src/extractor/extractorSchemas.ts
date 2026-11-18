import { z } from 'zod';

/**
 * Zod mirror of services/extractor/extractor/schemas/contract.py.
 * test/unit/extractorContract.test.ts compares these with the Pydantic JSON Schemas exported to
 * services/extractor/contract/, so the two sides cannot drift silently.
 */

const nullableString = z.string().nullable();
const nullableNumber = z.number().nullable();

export const issueSchema = z
  .object({
    path: z.string(),
    code: z.string(),
    severity: z.enum(['error', 'warn']),
    message: z.string(),
  })
  .strict();

const headerSchema = z
  .object({
    supplier_name: nullableString,
    supplier_gstin: nullableString,
    buyer_name: nullableString,
    buyer_gstin: nullableString,
    invoice_number: nullableString,
    invoice_date: nullableString,
    place_of_supply: nullableString,
    currency: nullableString,
  })
  .strict();

const lineItemSchema = z
  .object({
    description: nullableString,
    hsn_sac: nullableString,
    quantity: nullableNumber,
    unit: nullableString,
    rate: nullableNumber,
    discount: nullableNumber,
    taxable_value: nullableNumber,
    cgst_rate: nullableNumber,
    cgst_amount: nullableNumber,
    sgst_rate: nullableNumber,
    sgst_amount: nullableNumber,
    igst_rate: nullableNumber,
    igst_amount: nullableNumber,
  })
  .strict();

const totalsSchema = z
  .object({
    subtotal: nullableNumber,
    total_tax: nullableNumber,
    round_off: nullableNumber,
    grand_total: nullableNumber,
  })
  .strict();

export const invoiceSchema = z
  .object({ header: headerSchema, line_items: z.array(lineItemSchema), totals: totalsSchema })
  .strict();

export const fieldSchema = z
  .object({
    path: z.string(),
    value: nullableString,
    confidence: z.number(),
    page: z.number().int().nullable(),
    bbox: z.array(z.number()).nullable(),
    grounded: z.boolean(),
    issues: z.array(issueSchema),
  })
  .strict();

const usageSchema = z
  .object({
    purpose: z.string(),
    model: z.string(),
    tokens_in: z.number().int(),
    tokens_out: z.number().int(),
    cost_usd: z.number(),
    from_cache: z.boolean(),
    latency_ms: z.number(),
  })
  .strict();

export const extractResponseSchema = z
  .object({
    document_id: z.string(),
    attempt: z.number().int(),
    pipeline_version: z.string(),
    decision: z.enum(['auto_approve', 'needs_review', 'reject']),
    decision_reason: z.string(),
    document_confidence: z.number(),
    required_grounded: z.boolean(),
    pages: z.number().int(),
    used_ocr: z.boolean(),
    invoice: invoiceSchema.nullable(),
    fields: z.array(fieldSchema),
    issues: z.array(issueSchema),
    repair_attempts: z.number().int(),
    model: nullableString,
    tokens_in: z.number().int(),
    tokens_out: z.number().int(),
    cost_usd: z.number(),
    latency_ms: z.number().int(),
    node_timings: z.record(z.string(), z.number().int()),
    llm_calls: z.array(usageSchema),
  })
  .strict();

const fewShotCorrectionSchema = z
  .object({ field_path: z.string(), before: nullableString, after: nullableString })
  .strict();

const fewShotSupplierSchema = z
  .object({ supplier_gstin: z.string(), corrections: z.array(fewShotCorrectionSchema) })
  .strict();

export const extractMetadataSchema = z
  .object({
    document_id: z.string(),
    attempt: z.number().int().min(1),
    filename: nullableString.optional(),
    reference_date: nullableString.optional(),
    few_shot: z.array(fewShotSupplierSchema).optional(),
  })
  .strict();

export type ExtractResponse = z.infer<typeof extractResponseSchema>;
export type ExtractMetadata = z.infer<typeof extractMetadataSchema>;
export type ExtractedInvoice = z.infer<typeof invoiceSchema>;
export type ExtractedFieldOut = z.infer<typeof fieldSchema>;
export type IssueOut = z.infer<typeof issueSchema>;
export type FewShotSupplier = z.infer<typeof fewShotSupplierSchema>;
