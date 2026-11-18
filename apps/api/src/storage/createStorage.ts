import type { Env } from '../config/env';
import { CloudinaryStorage } from './cloudinaryStorage';
import { LocalStorage } from './localStorage';
import type { StorageProvider } from './storageProvider';

export function createStorage(config: Env): StorageProvider {
  if (config.STORAGE_DRIVER === 'cloudinary') {
    return new CloudinaryStorage({
      // loadEnv() already verified these are present when the driver is cloudinary.
      cloudName: config.CLOUDINARY_CLOUD_NAME as string,
      apiKey: config.CLOUDINARY_API_KEY as string,
      apiSecret: config.CLOUDINARY_API_SECRET as string,
      folder: config.CLOUDINARY_FOLDER,
    });
  }
  return new LocalStorage(config.STORAGE_LOCAL_DIR);
}
