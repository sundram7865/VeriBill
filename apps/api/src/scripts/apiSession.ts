import { readFile } from 'node:fs/promises';
import path from 'node:path';

/** Tiny HTTP client for scripts that drive the running API like a browser would. */
export class ApiSession {
  private token = '';

  constructor(private readonly baseUrl: string) {}

  async login(email: string, password: string): Promise<void> {
    const res = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) throw new Error(`login failed: HTTP ${res.status} ${await res.text()}`);
    this.token = ((await res.json()) as { accessToken: string }).accessToken;
  }

  async get<T>(route: string): Promise<T> {
    const res = await fetch(`${this.baseUrl}${route}`, {
      headers: { authorization: `Bearer ${this.token}` },
    });
    if (!res.ok) throw new Error(`GET ${route} failed: HTTP ${res.status}`);
    return (await res.json()) as T;
  }

  async upload(
    filePaths: string[],
  ): Promise<{ documents: Array<{ id: string; originalName: string }>; rejected: unknown[] }> {
    const form = new FormData();
    for (const file of filePaths) {
      const data = await readFile(file);
      form.append('files', new Blob([new Uint8Array(data)]), path.basename(file));
    }
    const res = await fetch(`${this.baseUrl}/documents`, {
      method: 'POST',
      headers: { authorization: `Bearer ${this.token}` },
      body: form,
    });
    if (res.status !== 201 && res.status !== 422) {
      throw new Error(`upload failed: HTTP ${res.status} ${await res.text()}`);
    }
    return (await res.json()) as {
      documents: Array<{ id: string; originalName: string }>;
      rejected: unknown[];
    };
  }
}
