import { apiFetch } from './api';

/** Downloads an authenticated API response as a file (an <a href> could not send the token). */
export async function downloadFile(path: string, fileName: string): Promise<void> {
  const res = await apiFetch(path);
  const url = URL.createObjectURL(await res.blob());
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}
