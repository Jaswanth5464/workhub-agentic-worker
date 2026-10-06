"""
Seed data script — run once to initialize databases and generate PDFs.

Usage: python scripts/seed_data.py
"""

from __future__ import annotations

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from environment.seed import INVOICES, VENDORS, EXISTING_PAYABLE
from environment.acmefinance.db import init_db, seed_duplicate, count_payables
from environment.vendorhub.pdfgen import generate_invoice_pdf, InvoiceData


def main() -> None:
    print("=== Seeding AI Task Worker data ===\n")

    # 1. Initialize AcmeFinance database
    print("[1/3] Initializing AcmeFinance database...")
    init_db()
    print(f"      Database ready. Current payable count: {count_payables()}")

    # 2. Seed the pre-existing payable (for duplicate_exists test)
    print("[2/3] Seeding pre-existing payable (for duplicate test)...")
    seed_duplicate(
        vendor=EXISTING_PAYABLE["vendor"],
        invoice_no=EXISTING_PAYABLE["invoice_no"],
        amount=EXISTING_PAYABLE["amount"],
        currency=EXISTING_PAYABLE["currency"],
        due_date=EXISTING_PAYABLE["due_date"],
    )
    print(f"      Payable for {EXISTING_PAYABLE['vendor']} / {EXISTING_PAYABLE['invoice_no']} ensured.")
    print(f"      Total payables: {count_payables()}")

    # 3. Generate invoice PDFs
    pdf_dir = os.path.join(os.path.dirname(__file__), "..", "environment", "vendorhub", "data", "pdfs")
    os.makedirs(pdf_dir, exist_ok=True)
    print(f"[3/3] Generating {len(INVOICES)} invoice PDFs...")

    for inv in INVOICES:
        pdf_path = os.path.join(pdf_dir, f"invoice_{inv.id}.pdf")
        data = InvoiceData(
            invoice_no=inv.invoice_no,
            vendor=inv.vendor,
            vendor_address=VENDORS.get(inv.vendor, {}).get("address", ""),
            issue_date=inv.issue_date,
            due_date=inv.due_date,
            currency=inv.currency,
            line_items=inv.line_items,
        )
        generate_invoice_pdf(data, pdf_path)
        print(f"      ✓ {inv.invoice_no} → {os.path.basename(pdf_path)}")

    # Also create an inbox folder with a copy of the latest Globex invoice
    inbox_dir = os.path.join(os.path.dirname(__file__), "..", "environment", "inbox")
    os.makedirs(inbox_dir, exist_ok=True)

    # Find latest Globex invoice
    globex_invoices = [i for i in INVOICES if i.vendor == "Globex"]
    latest = max(globex_invoices, key=lambda x: x.issue_date)
    inbox_pdf = os.path.join(inbox_dir, f"{latest.invoice_no}.pdf")
    data = InvoiceData(
        invoice_no=latest.invoice_no,
        vendor=latest.vendor,
        vendor_address=VENDORS.get(latest.vendor, {}).get("address", ""),
        issue_date=latest.issue_date,
        due_date=latest.due_date,
        currency=latest.currency,
        line_items=latest.line_items,
    )
    generate_invoice_pdf(data, inbox_pdf)
    print(f"      ✓ Inbox copy: {latest.invoice_no}.pdf")

    print(f"\n=== Done! {len(INVOICES)} invoices, {count_payables()} payable(s) ===")
    print("\nReady to start the apps:")
    print("  VendorHub:    python -m environment.vendorhub.app     (port 8001)")
    print("  AcmeFinance:  python -m environment.acmefinance.app   (port 8002)")


if __name__ == "__main__":
    main()
