import type { ExtractInput, ExtractorClient } from '../../src/extractor/extractorClient';
import type { ExtractResponse } from '../../src/extractor/extractorSchemas';

/** Field values of a clean synthetic invoice, as the extractor would return them. */
export const CLEAN_FIELDS: Record<string, string | null> = {
  'header.supplier_name': 'Kaveri Steel Pvt Ltd',
  'header.supplier_gstin': '27AAPFU0939F1ZV',
  'header.buyer_name': 'Deccan Foods LLP',
  'header.buyer_gstin': '29AAACK1234L1ZJ',
  'header.invoice_number': 'INV/2025-26/0042',
  'header.invoice_date': '2026-03-15',
  'header.place_of_supply': 'Maharashtra (27)',
  'header.currency': 'INR',
  'line_items.0.description': 'Copper Wire 2.5 sq mm',
  'line_items.0.hsn_sac': '8544',
  'line_items.0.quantity': '10.00',
  'line_items.0.unit': 'MTR',
  'line_items.0.rate': '100.00',
  'line_items.0.discount': null,
  'line_items.0.taxable_value': '1000.00',
  'line_items.0.cgst_rate': '9.00',
  'line_items.0.cgst_amount': '90.00',
  'line_items.0.sgst_rate': '9.00',
  'line_items.0.sgst_amount': '90.00',
  'line_items.0.igst_rate': null,
  'line_items.0.igst_amount': null,
  'totals.subtotal': '1000.00',
  'totals.total_tax': '180.00',
  'totals.round_off': null,
  'totals.grand_total': '1180.00',
};

export function fakeResponse(
  input: ExtractInput,
  overrides: Partial<ExtractResponse> = {},
  fieldValues: Record<string, string | null> = CLEAN_FIELDS,
  flaggedPaths: string[] = [],
): ExtractResponse {
  const fields = Object.entries(fieldValues).map(([path, value]) => ({
    path,
    value,
    confidence: flaggedPaths.includes(path) ? 0.3 : 0.98,
    page: value === null ? null : 1,
    bbox: value === null ? null : [0.1, 0.1, 0.3, 0.12],
    grounded: value !== null,
    issues: flaggedPaths.includes(path)
      ? [
          {
            path,
            code: 'grand_total_mismatch',
            severity: 'error' as const,
            message: 'does not add up',
          },
        ]
      : [],
  }));
  return {
    document_id: input.metadata.document_id,
    attempt: input.metadata.attempt,
    pipeline_version: '1',
    decision: 'auto_approve',
    decision_reason: 'All checks passed',
    document_confidence: 0.98,
    required_grounded: true,
    pages: 1,
    used_ocr: false,
    invoice: null,
    fields,
    issues: fields.flatMap((f) => f.issues),
    repair_attempts: 0,
    model: 'gemini-3.5-flash-lite',
    tokens_in: 2400,
    tokens_out: 600,
    cost_usd: 0.00054,
    latency_ms: 1800,
    node_timings: { ingest: 5, parse: 40, extract: 1700, ground: 30, validate: 2, decide: 1 },
    llm_calls: [],
    ...overrides,
  };
}

/** Programmable fake: each call runs the next behaviour (or the last one repeatedly). */
export class FakeExtractor implements ExtractorClient {
  calls: ExtractInput[] = [];
  constructor(
    private behaviours: Array<(input: ExtractInput) => ExtractResponse | Promise<ExtractResponse>>,
  ) {}

  async extract(input: ExtractInput): Promise<ExtractResponse> {
    this.calls.push(input);
    const behaviour = this.behaviours[Math.min(this.calls.length - 1, this.behaviours.length - 1)];
    if (!behaviour) throw new Error('FakeExtractor has no behaviour configured');
    return behaviour(input);
  }
}
