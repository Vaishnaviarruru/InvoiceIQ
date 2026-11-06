# InvoiceIQ

Invoice-to-PO reconciliation prototype with explainable validation decisions and human review.

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run invoiceiq_app.py
```

## What it demonstrates

- PDF invoice text extraction
- Purchase-order lookup and reconciliation
- Required-field, vendor, currency and amount-tolerance checks
- Exact-document duplicate detection
- Explainable APPROVED / NEEDS REVIEW / REJECTED outcomes
- Human review decisions with reviewer and reason audit fields
- Local SQLite run history

## Demo limitations

This is a prototype using synthetic purchase-order data. It does not verify supplier legal identity, bank ownership, tax registration, goods receipt or payment status, and it does not execute payments.

## Deployment

Designed for Streamlit Community Cloud. Select `invoiceiq_app.py` as the app entrypoint.
