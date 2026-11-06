"""InvoiceIQ: deterministic invoice extraction, PO reconciliation and decisions.

This prototype supports text-based PDFs and pasted invoice text. It does not
verify bank accounts, tax registrations, or vendor identity with external systems.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable

import fitz  # PyMuPDF
import pandas as pd

StageCallback = Callable[[str, str], None]


def normalize(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", value.lower())


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract embedded text from a PDF. Scanned PDFs need OCR and are flagged."""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        text = "\n".join(page.get_text("text") for page in doc)
    if not text.strip():
        raise ValueError(
            "No selectable text found. This appears to be a scanned PDF. "
            "For this prototype, use a text-based PDF or paste its OCR text."
        )
    return text


def extract_invoice_fields(text: str) -> dict[str, Any]:
    """Conservative regex extraction; uncertain/missing fields remain blank."""
    patterns = {
        "invoice_number": [r"(?im)^\s*invoice\s*(?:number|no\.?|#)\s*[:#-]?\s*([A-Z0-9][A-Z0-9/_-]+)", r"(?i)invoice\s*#\s*([A-Z0-9][A-Z0-9/_-]+)"],
        "po_number": [r"(?im)^\s*(?:purchase\s*order|po)\s*(?:number|no\.?|#)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9/_-]+)"],
        "invoice_date": [r"(?im)^\s*invoice\s*date\s*[:#-]?\s*([A-Za-z0-9,./ -]+?)\s*$", r"(?im)^\s*date\s*[:#-]?\s*([0-9]{1,4}[./-][0-9]{1,2}[./-][0-9]{1,4})\s*$"],
        
"total_amount": [
    r"(?i)(?:invoice\s+grand\s+total|grand\s+total|invoice\s+total|total\s+due|total)"
    r"\s*(?:\(\s*(?:USD|INR|EUR|GBP)\s*\))?"
    r"\s*[:\-]?\s*(?:USD|INR|EUR|GBP|\$|₹|€|£)?\s*"
    r"([0-9][0-9,]*(?:\.\d{1,2})?)"
],

       


    }
    result: dict[str, Any] = {"invoice_number": "", "po_number": "", "vendor_name": "", "invoice_date": "", "total_amount": None, "currency": "USD"}
    for field, candidates in patterns.items():
        for pattern in candidates:
            match = re.search(pattern, text)
            if match:
                value = match.group(1).strip().rstrip(".,")
                result[field] = float(value.replace(",", "")) if field == "total_amount" else value
                break
    # Common vendor labels; don't guess from arbitrary first line.
    vendor_match = re.search(r"(?im)^\s*(?:vendor|supplier|from|billed\s+by)\s*[:#-]\s*(.+?)\s*$", text)
    if vendor_match:
        result["vendor_name"] = vendor_match.group(1).strip()
    # Detect currency only when explicitly present.
    currency_match = re.search(r"(?i)\b(USD|INR|EUR|GBP)\b|([₹€£$])", text)
    if currency_match:
        token = (currency_match.group(1) or currency_match.group(2)).upper()
        result["currency"] = {"₹": "INR", "€": "EUR", "£": "GBP", "$": "USD"}.get(token, token)
    return result


def load_purchase_orders(csv_path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype={"po_number": str, "vendor_name": str, "currency": str})
    required = {"po_number", "vendor_name", "po_amount", "currency"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"PO CSV is missing required columns: {', '.join(sorted(missing))}")
    df["po_amount"] = pd.to_numeric(df["po_amount"], errors="coerce")
    return df


def reconcile_invoice(fields: dict[str, Any], po_df: pd.DataFrame, prior_hashes: set[str], document_hash: str, tolerance: float = 5.0) -> dict[str, Any]:
    reasons: list[str] = []
    checks: list[dict[str, str]] = []
    invoice_no = str(fields.get("invoice_number") or "").strip()
    po_no = str(fields.get("po_number") or "").strip()
    vendor = str(fields.get("vendor_name") or "").strip()
    amount = fields.get("total_amount")
    currency = str(fields.get("currency") or "USD").upper()

    if document_hash in prior_hashes:
        return {"status": "REJECTED", "reasons": ["Exact same document has already been processed."], "checks": [{"check": "Duplicate document", "result": "FAIL"}], "matched_po": None, "variance": None}
    if not invoice_no:
        reasons.append("Invoice number is missing.")
    if not po_no:
        reasons.append("Purchase order reference is missing.")
    if not vendor:
        reasons.append("Vendor name could not be extracted.")
    if amount is None:
        reasons.append("Invoice total could not be extracted.")
    if any([not invoice_no, not po_no, not vendor, amount is None]):
        checks.append({"check": "Required fields", "result": "FAIL"})
        return {"status": "NEEDS REVIEW", "reasons": reasons, "checks": checks, "matched_po": None, "variance": None}
    checks.append({"check": "Required fields", "result": "PASS"})

    po_rows = po_df[po_df["po_number"].astype(str).str.casefold() == po_no.casefold()]
    if po_rows.empty:
        reasons.append(f"PO {po_no} was not found in the supplied purchase-order register.")
        checks.append({"check": "PO lookup", "result": "FAIL"})
        return {"status": "NEEDS REVIEW", "reasons": reasons, "checks": checks, "matched_po": None, "variance": None}
    po = po_rows.iloc[0].to_dict()
    checks.append({"check": "PO lookup", "result": "PASS"})

    if normalize(vendor) != normalize(po["vendor_name"]):
        reasons.append(f"Vendor mismatch: invoice says '{vendor}', PO register says '{po['vendor_name']}'.")
        checks.append({"check": "Vendor match", "result": "FAIL"})
    else:
        checks.append({"check": "Vendor match", "result": "PASS"})

    if currency != str(po["currency"]).upper():
        reasons.append(f"Currency mismatch: invoice is {currency}, PO is {po['currency']}.")
        checks.append({"check": "Currency match", "result": "FAIL"})
    else:
        checks.append({"check": "Currency match", "result": "PASS"})

    variance = round(float(amount) - float(po["po_amount"]), 2)
    if abs(variance) > tolerance:
        reasons.append(f"Invoice total differs from PO by {variance:,.2f} {currency}; allowed absolute tolerance is {tolerance:,.2f}.")
        checks.append({"check": "Amount tolerance", "result": "FAIL"})
    else:
        checks.append({"check": "Amount tolerance", "result": "PASS"})

    status = "NEEDS REVIEW" if reasons else "APPROVED"
    if not reasons:
        reasons.append("All configured checks passed. Invoice is eligible for human approval.")
    return {"status": status, "reasons": reasons, "checks": checks, "matched_po": po, "variance": variance}


def run_workflow(pdf_bytes: bytes | None, pasted_text: str | None, fields_override: dict[str, Any], po_df: pd.DataFrame, prior_hashes: set[str], on_stage: StageCallback | None = None) -> dict[str, Any]:
    def stage(name: str, detail: str):
        if on_stage:
            on_stage(name, detail)
    if pdf_bytes:
        stage("Document intake", "Reading uploaded PDF")
        raw_text = extract_pdf_text(pdf_bytes)
        doc_hash = hashlib.sha256(pdf_bytes).hexdigest()
    else:
        raw_text = pasted_text or ""
        if not raw_text.strip():
            raise ValueError("Upload a PDF or paste invoice text.")
        doc_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    stage("Information extraction", "Extracting invoice fields")
    extracted = extract_invoice_fields(raw_text)
    fields = {**extracted, **{k: v for k, v in fields_override.items() if v not in (None, "")}}
    stage("PO reconciliation", "Matching invoice to the purchase-order register")
    decision = reconcile_invoice(fields, po_df, prior_hashes, doc_hash)
    stage("Decision & explanation", "Applying deterministic checks and generating reasons")
    return {"fields": fields, "raw_text": raw_text, "document_hash": doc_hash, **decision}
