import { createHash, randomBytes } from 'node:crypto';

export function sha256Hex(data: Buffer | string): string {
  return createHash('sha256').update(data).digest('hex');
}

/** URL-safe random token, e.g. for opaque refresh tokens. */
export function randomToken(bytes = 32): string {
  return randomBytes(bytes).toString('base64url');
}
