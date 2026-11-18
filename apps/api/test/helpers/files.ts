/** Minimal but structurally valid files for upload tests (no real invoice data). */

export function tinyPdf(label = 'test'): Buffer {
  const content = `BT /F1 12 Tf 72 720 Td (${label}) Tj ET`;
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>',
    `<< /Length ${content.length} >>\nstream\n${content}\nendstream`,
  ];
  let body = '%PDF-1.4\n';
  const offsets: number[] = [];
  objects.forEach((obj, i) => {
    offsets.push(body.length);
    body += `${i + 1} 0 obj\n${obj}\nendobj\n`;
  });
  const xref = body.length;
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  body += offsets.map((o) => `${String(o).padStart(10, '0')} 00000 n \n`).join('');
  body += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(body, 'latin1');
}

export function pdfWithPages(pages: number): Buffer {
  const kids = Array.from({ length: pages }, (_, i) => `${i + 3} 0 R`).join(' ');
  let body = `%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n`;
  body += `2 0 obj << /Type /Pages /Kids [${kids}] /Count ${pages} >> endobj\n`;
  for (let i = 0; i < pages; i++) {
    body += `${i + 3} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj\n`;
  }
  return Buffer.from(body + '%%EOF\n', 'latin1');
}

export function tinyPng(): Buffer {
  return Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
    'base64',
  );
}

export async function uploadForm(
  files: Array<{ name: string; data: Buffer; type: string }>,
): Promise<FormData> {
  const form = new FormData();
  for (const file of files) {
    form.append('files', new Blob([new Uint8Array(file.data)], { type: file.type }), file.name);
  }
  return form;
}
