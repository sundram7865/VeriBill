import { sha256Hex } from '../../lib/hash';

/**
 * Deterministic sampling of auto-approved documents for human audit. Hashing the document id
 * (instead of Math.random) makes the choice reproducible and testable, while still spreading
 * evenly across documents.
 */
export function shouldAudit(documentId: string, rate: number): boolean {
  if (rate <= 0) return false;
  if (rate >= 1) return true;
  const bucket = parseInt(sha256Hex(documentId).slice(0, 8), 16) % 10_000;
  return bucket < Math.round(rate * 10_000);
}
