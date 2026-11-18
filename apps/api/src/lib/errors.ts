/** An error that maps directly to an HTTP response. Anything else becomes a 500. */
export class HttpError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = 'HttpError';
  }
}

export const badRequest = (message: string, details?: unknown) =>
  new HttpError(400, 'bad_request', message, details);
export const unauthorized = (message = 'Authentication required') =>
  new HttpError(401, 'unauthorized', message);
export const forbidden = (message = 'Not allowed') => new HttpError(403, 'forbidden', message);
export const notFound = (message = 'Not found') => new HttpError(404, 'not_found', message);
export const conflict = (message: string, details?: unknown) =>
  new HttpError(409, 'conflict', message, details);
export const payloadTooLarge = (message: string) =>
  new HttpError(413, 'payload_too_large', message);
export const unsupportedMedia = (message: string) =>
  new HttpError(415, 'unsupported_media_type', message);
export const tooManyRequests = (retryAfterSeconds: number) =>
  new HttpError(429, 'rate_limited', 'Too many requests, slow down', { retryAfterSeconds });
