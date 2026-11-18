import { describe, expect, it } from 'vitest';
import { CloudinaryStorage } from '../../src/storage/cloudinaryStorage';

const config = {
  cloudName: 'demo-cloud',
  apiKey: '123456',
  apiSecret: 'not-a-real-secret',
  folder: 'iq',
};

describe('CloudinaryStorage (no network)', () => {
  it('builds short-lived signed download links for authenticated raw assets', () => {
    const storage = new CloudinaryStorage(config);
    const url = new URL(storage.signedDownloadUrl('iq/tenant/abc', 'raw'));
    expect(url.hostname).toBe('api.cloudinary.com');
    expect(url.pathname).toBe('/v1_1/demo-cloud/raw/download');
    expect(url.searchParams.get('public_id')).toBe('iq/tenant/abc');
    expect(url.searchParams.get('type')).toBe('authenticated');
    expect(url.searchParams.get('signature')).toBeTruthy();
    const expiresAt = Number(url.searchParams.get('expires_at'));
    expect(expiresAt - Date.now() / 1000).toBeLessThanOrEqual(121);
  });

  it('downloads through the signed link and surfaces HTTP errors', async () => {
    const seen: string[] = [];
    const ok = new CloudinaryStorage(config, async (input) => {
      seen.push(String(input));
      return new Response(new Uint8Array([1, 2, 3]));
    });
    expect([...(await ok.get({ publicId: 'iq/t/x', resourceType: 'raw' }))]).toEqual([1, 2, 3]);
    expect(seen[0]).toContain('/raw/download');

    const denied = new CloudinaryStorage(config, async () => new Response('no', { status: 401 }));
    await expect(denied.get({ publicId: 'iq/t/x', resourceType: 'raw' })).rejects.toThrow(/401/);
  });
});
