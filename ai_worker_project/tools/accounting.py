"""
Accounting & Finance Domain Tools.

These 10 tools represent deep domain knowledge and business logic required
for real-world autonomous record processing, strictly adhering to the local sandbox.
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel
from config.loader import finance_rules as _fr

# 1. Tax Calculator
class TaxCalculatorTool(Tool):
    name = "calculate_tax"
    description = "Calculates GST or TDS for a record amount. USE THIS TOOL when you need to compute the tax separately from the base amount before submitting a record."
    risk_level = RiskLevel.LOW
    parameters = {
        "type": "object",
        "properties": {
            "base_amount": {"type": "number"},
            "tax_type": {"type": "string", "enum": ["GST", "TDS"]}
        },
        "required": ["base_amount", "tax_type"]
    }
    async def execute(self, base_amount: float, tax_type: str, **kwargs) -> ToolResult:
        rates = _fr.get("tax_rates", {})
        rate = rates.get(tax_type)
        if rate is None:
            return ToolResult(success=False, error=f"Unknown tax type: {tax_type}. Configured types: {list(rates.keys())}")
        tax = round(base_amount * rate, 2)
        total = round(base_amount + tax, 2) if tax_type == "GST" else round(base_amount - tax, 2)
        return ToolResult(success=True, data={"base": base_amount, "tax": tax, "final_amount": total, "rate": rate})

# 2. Payment Terms Calculator
class PaymentTermsTool(Tool):
    name = "calculate_due_date"
    description = "Calculates the exact due date based on payment terms (e.g. Net 30). USE THIS TOOL when an record only provides the issue date and terms, but you need the exact YYYY-MM-DD due date for InternalDB."
    risk_level = RiskLevel.LOW
    parameters = {
        "type": "object",
        "properties": {
            "issue_date": {"type": "string", "description": "YYYY-MM-DD"},
            "terms": {"type": "integer", "description": "Number of days (e.g. 30 for Net 30)"}
        },
        "required": ["issue_date", "terms"]
    }
    async def execute(self, issue_date: str, terms: int, **kwargs) -> ToolResult:
        try:
            dt = datetime.strptime(issue_date, "%Y-%m-%d")
            due = dt + timedelta(days=terms)
            return ToolResult(success=True, data={"calculated_due_date": due.strftime("%Y-%m-%d")})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

# 3. Duplicate Checker (Real SQLite Integration)
class DuplicateRecordCheckerTool(Tool):
    name = "check_duplicate_record"
    description = "Checks InternalDB database locally to see if an record is already processed. ALWAYS USE THIS TOOL before creating a new entry to prevent duplicate payments."
    risk_level = RiskLevel.LOW
    parameters = {
        "type": "object",
        "properties": {
            "entity_name": {"type": "string"},
            "record_id": {"type": "string"}
        },
        "required": ["entity_name", "record_id"]
    }
    async def execute(self, entity_name: str, record_id: str, **kwargs) -> ToolResult:
        db_path = os.path.join(os.path.dirname(__file__), "..", "environment", "internal_db", "internal_db.db")
        if not os.path.exists(db_path):
            return ToolResult(success=True, data={"is_duplicate": False, "msg": "No DB found, safe to proceed."})
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, record_id FROM payables WHERE entity = ? AND record_id = ?", (entity_name, record_id))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return ToolResult(success=True, data={"is_duplicate": True, "existing_entry_id": row[0], "record_id": row[1]})
            return ToolResult(success=True, data={"is_duplicate": False})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

# 4. Fraud & Anomaly Detector
class FraudDetectorTool(Tool):
    name = "detect_record_anomalies"
    description = "Runs business logic checks on an record to flag potential fraud. USE THIS TOOL to assess the risk of an record (e.g., weekend issues, high amounts) before approving payment."
    risk_level = RiskLevel.LOW
    parameters = {
        "type": "object",
        "properties": {
            "amount": {"type": "number"},
            "issue_date": {"type": "string", "description": "YYYY-MM-DD"}
        },
        "required": ["amount", "issue_date"]
    }
    async def execute(self, amount: float, issue_date: str, **kwargs) -> ToolResult:
        flags = []
        if amount > 10000:
            flags.append("High Value: Requires manual approval.")
        
        try:
            dt = datetime.strptime(issue_date, "%Y-%m-%d")
            if dt.weekday() >= 5: # Saturday or Sunday
                flags.append("Weekend Issue Date: Unusual business activity.")
            if dt > datetime.now():
                flags.append("Future Date: Record date is in the future.")
        except:
            pass
            
        return ToolResult(success=True, data={"is_flagged": len(flags) > 0, "flags": flags})

# 5. Local Currency Standardizer
class CurrencyStandardizerTool(Tool):
    name = "standardize_currency"
    description = "Converts foreign currencies to INR using configured local exchange rates. USE THIS TOOL when a record is in USD, EUR, or GBP, but you must enter the value into InternalDB in INR."
    risk_level = RiskLevel.LOW
    parameters = {
        "type": "object",
        "properties": {
            "amount": {"type": "number"},
            "currency": {"type": "string", "description": "e.g., USD, EUR, GBP"}
        },
        "required": ["amount", "currency"]
    }
    async def execute(self, amount: float, currency: str, **kwargs) -> ToolResult:
        rates = _fr.get("fx_rates", {})
        currency = currency.upper()
        if currency not in rates:
            return ToolResult(success=False, error=f"Unsupported currency: {currency}. Configured: {list(rates.keys())}")
            
        inr_amount = round(amount * rates[currency], 2)
        return ToolResult(success=True, data={"original": amount, "currency": currency, "inr_amount": inr_amount})

# 6. Transaction Categorization
class CategoryClassifierTool(Tool):
    name = "categorize_transaction"
    description = "Categorizes an record based on entity name or description. USE THIS TOOL to determine the correct transaction category (e.g. 'Software & IT' vs 'Office Supplies') before recording the transaction."
    risk_level = RiskLevel.LOW
    parameters = {
        "type": "object",
        "properties": {
            "entity_name": {"type": "string"},
            "description": {"type": "string"}
        },
        "required": ["entity_name"]
    }
    async def execute(self, entity_name: str, description: str = "", **kwargs) -> ToolResult:
        text = f"{entity_name} {description}".lower()
        if any(x in text for x in ["tech", "cloud", "software", "host", "digital"]):
            category = "Software & IT"
        elif any(x in text for x in ["office", "supply", "stationery", "paper"]):
            category = "Office Supplies"
        elif any(x in text for x in ["consult", "legal", "advis"]):
            category = "Professional Services"
        else:
            category = "General/Misc"
        return ToolResult(success=True, data={"category": category})

# 7. Entity History Analyzer
class EntityHistoryAnalyzerTool(Tool):
    name = "analyze_entity_history"
    description = "Queries local DB to see how much we have paid this entity historically. USE THIS TOOL when you need to know the historical spend for a entity."
    risk_level = RiskLevel.LOW
    parameters = {
        "type": "object",
        "properties": {
            "entity_name": {"type": "string"}
        },
        "required": ["entity_name"]
    }
    async def execute(self, entity_name: str, **kwargs) -> ToolResult:
        db_path = os.path.join(os.path.dirname(__file__), "..", "environment", "internal_db", "internal_db.db")
        if not os.path.exists(db_path):
            return ToolResult(success=True, data={"total_paid": 0, "record_count": 0})
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT amount FROM payables WHERE entity = ?", (entity_name,))
            rows = cursor.fetchall()
            conn.close()
            
            total = sum(r[0] for r in rows)
            return ToolResult(success=True, data={"entity": entity_name, "total_paid": total, "record_count": len(rows)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

# 8. Early Payment Discount Calculator
class DiscountCalculatorTool(Tool):
    name = "calculate_early_discount"
    description = "Calculates early-payment discount per configured terms. USE THIS TOOL when a record explicitly mentions early payment discounts."
    risk_level = RiskLevel.LOW
    parameters = {
        "type": "object",
        "properties": {
            "amount": {"type": "number"}
        },
        "required": ["amount"]
    }
    async def execute(self, amount: float, **kwargs) -> ToolResult:
        ep = _fr.get("early_payment", {})
        rate = ep.get("discount_rate", 0.02)
        within = ep.get("within_days", 10)
        discount = round(amount * rate, 2)
        new_amount = round(amount - discount, 2)
        return ToolResult(success=True, data={"original_amount": amount, "discount_amount": discount, "discounted_total": new_amount, "discount_rate": rate, "within_days": within})

# 9. Record Schema Validator
class RecordDataValidatorTool(Tool):
    name = "validate_record_schema"
    description = "Strictly validates if extracted record data matches InternalDB requirements. USE THIS TOOL to verify you have all required JSON fields before making the final API call."
    risk_level = RiskLevel.LOW
    parameters = {
        "type": "object",
        "properties": {
            "record_data": {"type": "string", "description": "JSON string of record data"}
        },
        "required": ["record_data"]
    }
    async def execute(self, record_data: str, **kwargs) -> ToolResult:
        required_fields = _fr.get("required_payable_fields", ["entity", "record_id", "amount", "due_date"])
        try:
            data = json.loads(record_data)
            missing = [f for f in required_fields if not data.get(f)]
            if missing:
                return ToolResult(success=False, error=f"Missing required fields: {', '.join(missing)}")
            return ToolResult(success=True, data={"is_valid": True})
        except Exception as e:
            return ToolResult(success=False, error=f"Invalid JSON provided: {e}")

# 10. Ledger Balance Check
class LedgerBalanceTool(Tool):
    name = "check_ledger_balance"
    description = "Checks the simulated local ledger to ensure sufficient funds exist. USE THIS TOOL to verify we have enough money before approving a large record."
    risk_level = RiskLevel.LOW
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    async def execute(self, **kwargs) -> ToolResult:
        balance = _fr.get("simulation", {}).get("ledger_balance", 0.0)
        return ToolResult(success=True, data={"available_balance": balance, "currency": "INR"})


