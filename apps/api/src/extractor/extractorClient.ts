import {
  extractMetadataSchema,
  extractResponseSchema,
  type ExtractMetadata,
  type ExtractResponse,
} from './extractorSchemas';

const NON_RETRYABLE_CODES = new Set([
  'llm_not_configured',
  'llm_replay_miss',
  'ocr_unavailable',
  'not_configured',
]);

/** A non-2xx answer from the extractor, with its machine-readable error code. */
export class ExtractorHttpError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ExtractorHttpError';
  }

  /**
   * 4xx (including the 429 budget cap) can never succeed as-is. 5xx is usually transient,
   * except configuration problems that a retry a few seconds later cannot fix.
   */
  get retryable(): boolean {
    return this.status >= 500 && !NON_RETRYABLE_CODES.has(this.code);
  }
}

export interface ExtractInput {
  bytes: Buffer;
  filename: string;
  mime: string;
  metadata: ExtractMetadata;
}

export interface ExtractorClient {
  extract(input: ExtractInput): Promise<ExtractResponse>;
}

interface HttpExtractorOptions {
  baseUrl: string;
  serviceToken: string;
  timeoutMs: number;
  fetchImpl?: typeof fetch;
}

async function errorFrom(response: Response): Promise<ExtractorHttpError> {
  let code = 'extractor_error';
  let message = `Extractor responded with HTTP ${response.status}`;
  try {
    const body = (await response.json()) as { error?: { code?: string; message?: string } };
    code = body.error?.code ?? code;
    message = body.error?.message ?? message;
  } catch {
    // Non-JSON error body (e.g. a proxy page); keep the generic message.
  }
  return new ExtractorHttpError(response.status, code, message);
}

/** Calls POST /v1/extract on the private network with the shared service token. */
export function httpExtractorClient(options: HttpExtractorOptions): ExtractorClient {
  const doFetch = options.fetchImpl ?? fetch;
  return {
    async extract(input) {
      const form = new FormData();
      form.append(
        'file',
        new Blob([new Uint8Array(input.bytes)], { type: input.mime }),
        input.filename,
      );
      form.append('metadata', JSON.stringify(extractMetadataSchema.parse(input.metadata)));
      const response = await doFetch(`${options.baseUrl}/v1/extract`, {
        method: 'POST',
        headers: { authorization: `Bearer ${options.serviceToken}` },
        body: form,
        signal: AbortSignal.timeout(options.timeoutMs),
      });
      if (!response.ok) throw await errorFrom(response);
      // Validate on our side too: a contract violation must fail loudly, not corrupt data.
      return extractResponseSchema.parse(await response.json());
    },
  };
}
