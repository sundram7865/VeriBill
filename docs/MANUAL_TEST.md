# Manual browser test (about 10 minutes)

Prerequisites: the stack is running (`docker compose up --build`), the demo users exist
(`pnpm seed`), sample invoices are optionally uploaded (`pnpm seed:samples`), and for real extractions `OPENAI_API_KEY` is set in `.env`. Without a key every
upload ends as **failed** with "llm_not_configured"; steps 1–3, 8 and 9 still work.

1. **Login.** Open http://localhost:3000. You are sent to `/login`. Sign in as
   `reviewer@demo.invoiceiq.test` / `demo-reviewer-password`. Wrong password shows "Invalid email or password".
2. **Session survives reload.** Reload the page: you stay signed in (refresh cookie), no flash of the login form.
3. **Upload.** On Documents, drop `evals/fixtures/generated/files/c0001.pdf` (generate the suite first:
   `python -m evals.generate`). Also try a `.txt` file renamed to `.pdf`: it is rejected with
   "Only PDF, PNG and JPEG files are accepted". Upload `c0001.pdf` again: "This exact file was already uploaded".
4. **Live status.** The new row goes `uploaded → processing → auto approved / needs review` without
   reloading (polling every 2 s while anything is in flight).
5. **Review screen.** Open a `needs review` document (e.g. upload `c0112.pdf`, a wrong-total invoice).
   - Left: the PDF with green/red boxes where each value was found. Right: fields grouped
     Header / Line N / Totals with confidence badges and red validator messages.
   - Press `j`/`k`: the selection moves and the page scrolls to the field's box. Click a box: its field is selected.
   - Press `e`, change the grand total, press `Esc`. The field turns blue (edited).
   - Press `?` for the shortcut list. Press `Ctrl+Enter` to approve. You land on the next queued document or the queue.
6. **Reject.** On another queued document press `Shift+R` and confirm: status becomes rejected.
7. **Audit sample.** With `AUDIT_SAMPLE_RATE=1` in `.env` (restart api+worker), auto-approved documents
   appear in the queue as "audit sample". Approve one without changes.
8. **Metrics.** Open Metrics: auto-approval rate, audited accuracy, field correction rate, validator catch
   rate, cost per document, p50/p95 latency, open tasks. Numbers change after steps 5–7.
9. **Export (admin only).** Log out, sign in as `admin@demo.invoiceiq.test` / `demo-admin-password`.
   Documents → Export approved: CSV and JSON download. As the reviewer the buttons are not shown and
   the API returns 403.
10. **Tenant isolation (optional).** Create a second tenant's user with Prisma Studio
    (`pnpm --filter @invoiceiq/api exec prisma studio`) and confirm they see none of the demo documents.
