# Assumptions

These are assumptions I made while building the prototype. Each is a deliberate
simplification documented here for transparency.

## Environment
1. **Currency is INR** for all seed invoices. The schema supports other currencies
   but the test data is all Indian Rupees.
2. **Tax rate is 18% GST** for all invoices (fixed in PDF generation).
3. **VendorHub login is cosmetic** — there is no real authentication. The login
   page exists so the agent can demonstrate navigating past it, but `demo/demo`
   is accepted without server-side validation.
4. **Invoice IDs are globally unique integers** across all vendors (1 through 17).

## Workflow
5. **"Latest invoice" means the one with the most recent `issue_date`**, not the
   most recent creation time or the highest invoice number.
6. **One workflow focus: invoice entry** between a vendor portal and an internal
   finance system. This is narrow by design — the assignment says "a narrow
   prototype that genuinely works is better than a broad system where most
   functionality is mocked."
7. **The agent enters one payable per run** (the latest invoice for the requested
   vendor). Batch entry is a documented next step.

## Technical
8. **SQLite is the database** — no external database server needed. Suitable for
   a local single-user prototype.
9. **Playwright uses Chromium** (not Firefox or WebKit) — it is the most reliable
   and widely tested browser engine for automation.
10. **LLM calls use free tiers** of Groq and Google Gemini. Rate limits may
    affect evaluation speed. Cassette replay mitigates this for demos.

## Out of scope (documented, not hidden)
11. **No real email, Slack, or external service integration.** The tools only
    interact with localhost practice apps.
12. **No multi-user authentication or RBAC.** One operator at a time.
13. **No Docker or container deployment.** Everything runs directly on the host.
