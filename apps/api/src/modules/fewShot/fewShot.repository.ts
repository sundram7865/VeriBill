import { assertTenant, type Db } from '../../lib/db';
import type { FewShotSupplier } from '../../extractor/extractorSchemas';

const RECENT_CORRECTIONS = 500;

/**
 * Past reviewer corrections grouped by supplier GSTIN (exact match), newest first. The worker
 * sends these with every extraction; the extractor uses only the group whose GSTIN is printed
 * on the document, so the extractor stays stateless.
 */
export function fewShotRepository(db: Db) {
  return {
    async forTenant(
      tenantId: string,
      maxSuppliers: number,
      perSupplier: number,
    ): Promise<FewShotSupplier[]> {
      assertTenant(tenantId);
      if (maxSuppliers === 0 || perSupplier === 0) return [];
      const corrections = await db.correction.findMany({
        where: { tenantId },
        orderBy: { createdAt: 'desc' },
        take: RECENT_CORRECTIONS,
        select: { documentId: true, fieldPath: true, before: true, after: true },
      });
      if (corrections.length === 0) return [];
      const invoices = await db.invoice.findMany({
        where: { tenantId, documentId: { in: [...new Set(corrections.map((c) => c.documentId))] } },
        select: { documentId: true, supplierGstin: true },
      });
      const gstinByDocument = new Map(invoices.map((i) => [i.documentId, i.supplierGstin]));

      const bySupplier = new Map<string, FewShotSupplier>();
      for (const c of corrections) {
        const gstin = gstinByDocument.get(c.documentId);
        if (!gstin) continue;
        let group = bySupplier.get(gstin);
        if (!group) {
          if (bySupplier.size >= maxSuppliers) continue;
          group = { supplier_gstin: gstin, corrections: [] };
          bySupplier.set(gstin, group);
        }
        if (group.corrections.length < perSupplier) {
          group.corrections.push({ field_path: c.fieldPath, before: c.before, after: c.after });
        }
      }
      return [...bySupplier.values()];
    },
  };
}
