import { v2 as cloudinary, type UploadApiResponse } from 'cloudinary';
import { randomPublicId } from './randomPublicId';
import type { PutOptions, StorageProvider, StoredObject } from './storageProvider';

export interface CloudinaryConfig {
  cloudName: string;
  apiKey: string;
  apiSecret: string;
  folder: string;
}

/** How long a server-side download link stays valid. The browser never sees it. */
const DOWNLOAD_LINK_TTL_SECONDS = 120;

// Files are stored as "raw" so Cloudinary never transforms them, and as "authenticated"
// so they cannot be fetched without a signature generated with our API secret.
const RESOURCE_TYPE = 'raw';
const DELIVERY_TYPE = 'authenticated';

export class CloudinaryStorage implements StorageProvider {
  readonly name = 'cloudinary' as const;

  constructor(
    private readonly config: CloudinaryConfig,
    private readonly fetchImpl: typeof fetch = fetch,
  ) {
    cloudinary.config({
      cloud_name: config.cloudName,
      api_key: config.apiKey,
      api_secret: config.apiSecret,
      secure: true,
    });
  }

  async put(bytes: Buffer, options: PutOptions): Promise<StoredObject> {
    const publicId = randomPublicId(this.config.folder, options.tenantId);
    const result = await this.uploadBuffer(bytes, publicId);
    return { provider: 'cloudinary', publicId: result.public_id, resourceType: RESOURCE_TYPE };
  }

  async get(object: Pick<StoredObject, 'publicId' | 'resourceType'>): Promise<Buffer> {
    const url = this.signedDownloadUrl(object.publicId, object.resourceType);
    const response = await this.fetchImpl(url);
    if (!response.ok) {
      throw new Error(`Cloudinary download failed with HTTP ${response.status}`);
    }
    return Buffer.from(await response.arrayBuffer());
  }

  async remove(object: Pick<StoredObject, 'publicId' | 'resourceType'>): Promise<void> {
    await cloudinary.uploader.destroy(object.publicId, {
      resource_type: object.resourceType,
      type: DELIVERY_TYPE,
      invalidate: true,
    });
  }

  /** Time-limited, API-secret-signed download link for an authenticated asset. */
  signedDownloadUrl(publicId: string, resourceType: string): string {
    return cloudinary.utils.private_download_url(publicId, '', {
      resource_type: resourceType,
      type: DELIVERY_TYPE,
      expires_at: Math.floor(Date.now() / 1000) + DOWNLOAD_LINK_TTL_SECONDS,
    });
  }

  private uploadBuffer(bytes: Buffer, publicId: string): Promise<UploadApiResponse> {
    return new Promise((resolve, reject) => {
      const stream = cloudinary.uploader.upload_stream(
        {
          public_id: publicId,
          resource_type: RESOURCE_TYPE,
          type: DELIVERY_TYPE,
          overwrite: false,
          unique_filename: false,
          use_filename: false,
        },
        (error, result) => {
          if (error || !result) reject(error ?? new Error('Cloudinary upload returned no result'));
          else resolve(result);
        },
      );
      stream.end(bytes);
    });
  }
}
