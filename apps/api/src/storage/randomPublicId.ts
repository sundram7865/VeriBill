import { randomUUID } from 'node:crypto';

/** Random, unguessable object id grouped by tenant. Never derived from the file name. */
export function randomPublicId(folder: string, tenantId: string): string {
  return `${folder}/${tenantId}/${randomUUID()}`;
}
