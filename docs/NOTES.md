# NOTES — What I learned building this

## Phase 1: Environment
- VendorHub and AcmeFinance are two separate FastAPI apps that simulate the vendor portal and internal finance system the agent will work with — they serve both HTML pages (for browser automation) and JSON APIs (for direct tool calls).
- The fault injection system lets me toggle failures (renamed buttons, slow loads, bad saves) at runtime via a simple API, which is how the evaluation suite will prove the agent can recover from real problems.
- Seed data creates 17 invoices across 4 vendors with real PDF files and one pre-existing payable for duplicate detection testing — everything is deterministic and regenerable from scratch.
