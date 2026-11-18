import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { randomPublicId } from './randomPublicId';
import type { PutOptions, StorageProvider, StoredObject } from './storageProvider';

/** Disk-backed driver for development and tests (STORAGE_DRIVER=local). */
export class LocalStorage implements StorageProvider {
  readonly name = 'local' as const;
  private readonly root: string;

  constructor(rootDir: string) {
    this.root = path.resolve(rootDir);
  }

  async put(bytes: Buffer, options: PutOptions): Promise<StoredObject> {
    const publicId = randomPublicId('docs', options.tenantId);
    const filePath = this.resolve(publicId);
    await mkdir(path.dirname(filePath), { recursive: true });
    await writeFile(filePath, bytes);
    return { provider: 'local', publicId, resourceType: 'raw' };
  }

  async get(object: Pick<StoredObject, 'publicId'>): Promise<Buffer> {
    return readFile(this.resolve(object.publicId));
  }

  async remove(object: Pick<StoredObject, 'publicId'>): Promise<void> {
    await rm(this.resolve(object.publicId), { force: true });
  }

  /** Public ids come from our database, but refuse anything that escapes the root anyway. */
  private resolve(publicId: string): string {
    const resolved = path.resolve(this.root, publicId);
    if (!resolved.startsWith(this.root + path.sep)) {
      throw new Error('Invalid storage id');
    }
    return resolved;
  }
}
