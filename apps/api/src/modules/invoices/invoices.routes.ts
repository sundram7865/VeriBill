import type { Invoice } from '@prisma/client';
import { Router } from 'express';
import { z } from 'zod';
import type { AppDeps } from '../../app.deps';
import { notFound } from '../../lib/errors';
import { authenticate, authOf } from '../../middleware/authenticate';
import { invoicesRepository } from './invoices.repository';

const searchQuery = z.object({
  supplier: z.string().max(100).optional(),
  from: z.coerce.date().optional(),
  to: z.coerce.date().optional(),
  minAmount: z.coerce.number().optional(),
  maxAmount: z.coerce.number().optional(),
  limit: z.coerce.number().int().min(1).max(200).default(50),
});

function present(inv: Invoice) {
  return {
    documentId: inv.documentId,
    invoiceNumber: inv.invoiceNumber,
    invoiceDate: inv.invoiceDate?.toISOString().slice(0, 10) ?? null,
    supplierName: inv.supplierName,
    supplierGstin: inv.supplierGstin,
    buyerName: inv.buyerName,
    buyerGstin: inv.buyerGstin,
    placeOfSupply: inv.placeOfSupply,
    currency: inv.currency,
    subtotal: inv.subtotal?.toNumber() ?? null,
    totalTax: inv.totalTax?.toNumber() ?? null,
    roundOff: inv.roundOff?.toNumber() ?? null,
    grandTotal: inv.grandTotal?.toNumber() ?? null,
    lineItems: inv.lineItems,
    approvedVia: inv.approvedVia,
    approvedAt: inv.approvedAt,
  };
}

/** Read-only search over approved invoices (used by the MCP server and the UI). */
export function invoicesRoutes(deps: AppDeps): Router {
  const router = Router();
  const repo = invoicesRepository(deps.db);
  router.use('/invoices', authenticate(deps.config.JWT_ACCESS_SECRET));

  router.get('/invoices', async (req, res) => {
    const q = searchQuery.parse(req.query);
    const items = await repo.search(authOf(req).tenantId, { ...q, take: q.limit });
    res.json({ items: items.map(present) });
  });

  router.get('/invoices/:documentId', async (req, res) => {
    const documentId = z.string().uuid().parse(req.params.documentId);
    const invoice = await repo.findByDocument(authOf(req).tenantId, documentId);
    if (!invoice) throw notFound('Invoice not found');
    res.json({ invoice: present(invoice) });
  });

  return router;
}
