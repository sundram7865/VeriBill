export type StorageDriverName = 'local' | 'cloudinary';

/** Where a stored file lives. These three values are persisted on the document row. */
export interface StoredObject {
  provider: StorageDriverName;
  publicId: string;
  resourceType: string;
}

export interface PutOptions {
  tenantId: string;
  mime: string;
}

/**
 * The only storage operations the product needs: one upload and one download per
 * document (plus delete for cleanup). Keeping the interface this small is what makes
 * the local driver a faithful stand-in for Cloudinary in tests.
 */
export interface StorageProvider {
  readonly name: StorageDriverName;
  put(bytes: Buffer, options: PutOptions): Promise<StoredObject>;
  get(object: Pick<StoredObject, 'publicId' | 'resourceType'>): Promise<Buffer>;
  remove(object: Pick<StoredObject, 'publicId' | 'resourceType'>): Promise<void>;
}
