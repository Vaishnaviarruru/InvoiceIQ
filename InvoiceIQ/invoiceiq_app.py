from pathlib import Path
import json
import time
import pandas as pd
import streamlit as st

from app.services.invoice_workflow import load_purchase_orders, run_workflow
from app.services.run_store import (
    init_db, prior_hashes, save_run, get_runs, get_run, record_review
)

ROOT = Path(__file__).resolve().parent
PO_PATH = ROOT / "data" / "purchase_orders.csv"

st.set_page_config(page_title="InvoiceIQ | AP Automation", page_icon="🧾", layout="wide")
init_db()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;650;700;750;800&display=swap');
:root {
  --paper:#F7F8FA; --surface:#FFFFFF; --ink:#17191F; --muted:#707784;
  --line:#E2E5EA; --blue:#315CFF; --blue-dark:#2348D8;
  --orange:#F06435; --green:#178653; --red:#D83A52; --yellow:#F4C542;
}
html, body, [class*="css"], button, input, textarea {font-family:'Geist',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif !important;}
.stApp {background:var(--paper); color:var(--ink);}
.block-container {max-width:1320px; padding-top:1.25rem; padding-bottom:3rem;}
[data-testid="stHeader"] {background:var(--paper);}
[data-testid="stSidebar"] {background:#17191F; border-right:1px solid #292D36;}
[data-testid="stSidebar"] * {color:#F4F5F7 !important;}
[data-testid="stSidebar"] [data-testid="stRadio"] label {padding:9px 11px; margin:2px 0; border:1px solid transparent; border-radius:6px; font-weight:550;}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {background:#282D38; border-color:#3B4352;}
[data-testid="stSidebar"] [data-testid="stRadio"] [aria-checked="true"] {background:#2B3F91; border-color:#4968E8;}
[data-testid="stSidebar"] hr {border-color:#353A45;}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {color:#A9AFBA !important;}
h1,h2,h3,h4 {color:var(--ink); letter-spacing:-.045em; font-family:'Geist',sans-serif !important;}
h1 {font-size:2.25rem !important; font-weight:750 !important;}
h2 {font-size:1.65rem !important; font-weight:700 !important;}
h3 {font-size:1.12rem !important; font-weight:650 !important;}
p,li,label {line-height:1.55;}
[data-testid="stCaptionContainer"], .small-muted {color:var(--muted);}
[data-testid="stMetric"] {background:var(--surface); border:1px solid var(--line); border-top:2px solid var(--blue); border-radius:7px; padding:13px 15px; box-shadow:none;}
[data-testid="stMetricLabel"] {color:var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.075em; font-weight:650;}
[data-testid="stMetricValue"] {color:var(--ink); font-weight:750; letter-spacing:-.04em;}
.stTextInput input,.stTextArea textarea,.stNumberInput input,.stSelectbox [data-baseweb="select"] {border-radius:6px; background:#fff; border-color:#D4D9E1;}
.stButton button,[data-testid="stFormSubmitButton"] button,[data-testid="stDownloadButton"] button {border-radius:6px; font-weight:600; min-height:2.45rem; border:1px solid #D4D9E1; box-shadow:none;}
.stButton button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"] {background:var(--blue); border-color:var(--blue); color:#fff;}
.stButton button[kind="primary"]:hover,[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {background:var(--blue-dark); border-color:var(--blue-dark);}
div[data-testid="stDataFrame"],div[data-testid="stTable"] {border:1px solid var(--line); border-radius:7px; overflow:hidden; background:#fff;}
details[data-testid="stExpander"] {background:#fff; border:1px solid var(--line); border-radius:7px;}
[data-testid="stAlert"] {border-radius:6px;}
hr {border-color:var(--line);}
.iq-masthead {display:flex; justify-content:space-between; align-items:flex-end; gap:20px; padding:4px 0 17px; margin:0 0 27px; border-bottom:1px solid #C9CED7;}
.iq-kicker {color:var(--blue); font-size:10px; font-weight:750; letter-spacing:.13em; text-transform:uppercase; margin-bottom:7px;}
.iq-brand {color:var(--ink); font-size:29px; line-height:1.08; font-weight:750; letter-spacing:-1.45px;}
.iq-brand span {color:var(--blue) !important;}
.iq-sub {color:var(--muted); font-size:12px; margin-top:6px;}
.iq-index {color:var(--muted); font-size:10px; text-align:right; letter-spacing:.08em;}
.iq-index strong {display:block; color:var(--orange); font-size:13px; letter-spacing:.1em; margin-bottom:3px;}
.iq-section {border-left:3px solid var(--orange); padding:1px 0 1px 11px; margin:8px 0 16px;}
@media (max-width:800px) {.block-container{padding-left:1rem;padding-right:1rem;} .iq-masthead{align-items:flex-start;flex-direction:column;} .iq-index{text-align:left;}}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="iq-masthead">
  <div>
    <div class="iq-kicker">AP OPERATIONS / WORKSPACE</div>
    <div class="iq-brand">InvoiceIQ <span>/</span> Reconciliation</div>
    <div class="iq-sub">A clear record of every invoice, match and decision.</div>
  </div>
  <div class="iq-index"><strong>LOCAL PROTOTYPE</strong>DEMO DATA · NO PAYMENT EXECUTION</div>
</div>
""", unsafe_allow_html=True)


runs = get_runs()
st.sidebar.markdown("<div style='font-size:10px;letter-spacing:.14em;color:#9CA5B5;font-weight:700;margin:8px 0 10px'>WORKSPACE</div>", unsafe_allow_html=True)
nav = st.sidebar.radio("Navigate", ["Process invoice", "Run history", "PO register", "How decisions work"], label_visibility="collapsed")
st.sidebar.divider()
st.sidebar.caption("Prototype mode · Local data · No external bank or tax verification")

if nav == "Process invoice":
    st.subheader("01 / Process an invoice")
    st.write("Upload a text-based PDF or paste invoice text. Review extracted fields before reconciliation.")
    uploaded = st.file_uploader("Invoice PDF", type=["pdf"])
    pasted = st.text_area("Or paste invoice text", height=125,
        placeholder="Invoice Number: INV-1001\\nVendor: Acme Supplies\\nPO Number: PO-1001\\nTotal: USD 1250.00")
    with st.expander("Advanced: override extracted fields", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            invoice_no = st.text_input("Invoice number")
            vendor = st.text_input("Vendor name")
            po_no = st.text_input("PO number")
        with c2:
            date = st.text_input("Invoice date")
            amount = st.number_input("Invoice total (leave 0 to use extraction)", min_value=0.0, step=0.01, format="%.2f")
            currency = st.selectbox("Currency", ["USD", "INR", "EUR", "GBP"])
    if st.button("▶ Run invoice workflow", type="primary", use_container_width=True):
        if not uploaded and not pasted.strip():
            st.error("Upload a PDF or paste invoice text first.")
        else:
            po_df = load_purchase_orders(PO_PATH)
            overrides = {"invoice_number": invoice_no, "vendor_name": vendor, "po_number": po_no, "invoice_date": date}
            if amount > 0:
                overrides["total_amount"] = amount
                overrides["currency"] = currency
            stages = []
            started = time.perf_counter()
            try:
                with st.status("Executing InvoiceIQ workflow…", expanded=True) as status_box:
                    def show_stage(name, detail):
                        item = {"stage": name, "detail": detail, "status": "COMPLETED"}
                        stages.append(item)
                        st.write(f"✓ **{name}**")
                        st.caption(detail)
                    result = run_workflow(
                        uploaded.getvalue() if uploaded else None,
                        pasted if not uploaded else None,
                        overrides, po_df, prior_hashes(), show_stage
                    )
                    duration_ms = round((time.perf_counter() - started) * 1000, 1)
                    result["stages"] = stages
                    result["duration_ms"] = duration_ms
                    run_id = save_run(result, uploaded.name if uploaded else "pasted_invoice.txt")
                    status_box.update(label=f"Workflow completed · Run #{run_id}", state="complete", expanded=False)
                st.session_state["last_result"] = result
                st.session_state["last_run_id"] = run_id
            except Exception as exc:
                st.error(f"Workflow failed: {exc}")

    result = st.session_state.get("last_result")
    if result:
        st.divider()
        status = result["status"]
        if status == "APPROVED":
            st.success("APPROVED — all configured checks passed. Human approval is still required before payment.")
        elif status == "REJECTED":
            st.error("REJECTED — duplicate document detected.")
        else:
            st.warning("NEEDS REVIEW — one or more checks require an AP reviewer.")

        st.markdown("#### Workflow execution")
        stages = result.get("stages", [])
        if stages:
            for i, item in enumerate(stages, 1):
                st.markdown(f"**{i}. {item['stage']}**  ·  :green[✓ {item['status']}]")
                st.caption(item["detail"])
        m1, m2, m3, m4 = st.columns(4)
        f = result["fields"]
        m1.metric("Invoice", f.get("invoice_number") or "Missing")
        m2.metric("Vendor", f.get("vendor_name") or "Missing")
        m3.metric("PO", f.get("po_number") or "Missing")
        m4.metric("Invoice total", f"{f.get('currency','USD')} {f.get('total_amount'):,.2f}" if f.get("total_amount") is not None else "Missing")
        if result.get("variance") is not None:
            st.metric("Invoice vs PO variance", f"{result['variance']:,.2f} {f.get('currency','USD')}")
        st.caption(f"Run #{st.session_state.get('last_run_id')} · Processing time: {result.get('duration_ms', 0):,.1f} ms")

        st.markdown("#### Validation checks")
        st.dataframe(pd.DataFrame(result["checks"]), use_container_width=True, hide_index=True)
        st.markdown("#### Decision explanation")
        for reason in result["reasons"]:
            st.write(f"• {reason}")
        if result.get("matched_po"):
            with st.expander("Matched purchase order"):
                st.json(result["matched_po"])
        with st.expander("Extracted source text"):
            st.text(result["raw_text"][:12000])

elif nav == "Run history":
    st.subheader("02 / Activity and decisions")
    if not runs:
        st.info("No runs yet. Process an invoice to populate this dashboard.")
    else:
        df = pd.DataFrame(runs)
        with st.expander("Find and filter runs", expanded=True):
            f1, f2 = st.columns([2, 1])
            with f1:
                run_search = st.text_input("Search invoice, vendor or PO", placeholder="e.g. INV-2026-205")
            with f2:
                decision_filter = st.selectbox("Machine decision", ["All decisions", "APPROVED", "NEEDS REVIEW", "REJECTED"])
        if run_search.strip():
            q = run_search.strip().lower()
            searchable = df[[c for c in ["invoice_number", "vendor_name", "po_number", "filename"] if c in df.columns]].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
            df = df[searchable.str.contains(q, regex=False)]
        if decision_filter != "All decisions":
            df = df[df.status == decision_filter]
        total = len(df)
        approved = int((df.status == "APPROVED").sum())
        pending = int((df.status == "NEEDS REVIEW").sum())
        rejected = int((df.status == "REJECTED").sum())
        human_reviewed = int((df.review_status != "NOT REVIEWED").sum())
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total runs", total)
        k2.metric("Machine approved", approved)
        k3.metric("Needs review", pending)
        k4.metric("Duplicates rejected", rejected)
        k5.metric("Human reviewed", human_reviewed)

        if "duration_ms" in df and df["duration_ms"].notna().any():
            st.metric("Average processing time", f"{df['duration_ms'].dropna().mean():,.0f} ms")
        st.markdown("#### Decision distribution")
        dist = df["status"].value_counts().rename_axis("Decision").reset_index(name="Runs")
        st.bar_chart(dist.set_index("Decision"))
        st.markdown("#### Recent workflow runs")
        cols = ["id", "created_at", "filename", "invoice_number", "vendor_name", "po_number",
                "total_amount", "currency", "status", "review_status", "duration_ms"]
        view = df[[c for c in cols if c in df.columns]].copy()
        st.dataframe(view, use_container_width=True, hide_index=True)

        st.markdown("#### Inspect a run")
        selected = st.selectbox("Select run ID", [r["id"] for r in runs])
        row = get_run(int(selected))
        if row:
            left, right = st.columns(2)
            with left:
                st.write("**Machine decision:**", row["status"])
                st.write("**Invoice:**", row["invoice_number"] or "Missing")
                st.write("**Vendor:**", row["vendor_name"] or "Missing")
                st.write("**Review state:**", row.get("review_status", "NOT REVIEWED"))
            with right:
                st.write("**PO:**", row["po_number"] or "Missing")
                st.write("**Amount:**", f"{row['currency']} {row['total_amount']:,.2f}" if row["total_amount"] is not None else "Missing")
                st.write("**Duration:**", f"{row['duration_ms']:,.1f} ms" if row.get("duration_ms") is not None else "Not recorded")
            st.write("**Decision reasons**")
            for reason in json.loads(row["reasons_json"]):
                st.write(f"• {reason}")
            if row.get("stages_json"):
                st.write("**Execution stages**")
                for stage in json.loads(row["stages_json"]):
                    st.write(f"✓ {stage['stage']} — {stage['detail']}")
            if row["status"] in {"APPROVED", "NEEDS REVIEW"} and row.get("review_status", "NOT REVIEWED") == "NOT REVIEWED":
                st.markdown("#### Human review")
                st.warning("A reviewer can record an explicit override. This does not change the original machine decision.")
                with st.form("human_review_form"):
                    reviewer = st.text_input("Reviewer name")
                    decision = st.radio("Review decision", ["HUMAN APPROVED", "HUMAN REJECTED"], horizontal=True)
                    note = st.text_area("Reason / evidence (required)")
                    submitted = st.form_submit_button("Record human decision", type="primary")
                    if submitted:
                        if not reviewer.strip() or not note.strip():
                            st.error("Enter the reviewer name and a reason before recording the decision.")
                        else:
                            record_review(int(selected), reviewer, decision, note)
                            st.success("Human review decision recorded in the audit trail.")
                            st.rerun()
        st.download_button("Download run history CSV", view.to_csv(index=False), "invoiceiq_run_history.csv", "text/csv")

elif nav == "PO register":
    st.subheader("03 / Purchase orders")
    st.caption("Demo procurement data used for reconciliation. Replace with an authorised export in a real deployment.")
    po_df = load_purchase_orders(PO_PATH)
    search_po = st.text_input("Search purchase orders", placeholder="Search by PO number or vendor")
    if search_po.strip():
        mask = po_df.astype(str).apply(lambda col: col.str.contains(search_po.strip(), case=False, na=False)).any(axis=1)
        po_view = po_df[mask]
    else:
        po_view = po_df
    p1, p2 = st.columns(2)
    p1.metric("Registered purchase orders", len(po_df))
    amount_col = "po_amount" if "po_amount" in po_df.columns else None
    if amount_col:
        p2.metric("Total registered PO value", f"{po_df[amount_col].sum():,.2f}")
    st.dataframe(po_view, use_container_width=True, hide_index=True)
    st.download_button("Download PO register", po_df.to_csv(index=False), "purchase_orders.csv", "text/csv")

else:
    st.subheader("04 / Decision rules")
    st.markdown("""
    **APPROVED** — Required fields are present, the PO exists, vendor and currency match,
    and the invoice total is within the configured absolute tolerance of USD 5 (or equivalent currency units).

    **NEEDS REVIEW** — Required information is missing, the PO cannot be found, vendor/currency differs,
    or the amount variance exceeds tolerance. This routes the case to an AP reviewer; it is not an automatic fraud finding.

    **REJECTED** — The exact same uploaded document/text has already been processed in this local run history.

    **Human review** — A reviewer may record an explicit human decision with their name and a reason.
    The machine decision is retained unchanged for auditability.

    **Limitations:** This prototype uses synthetic PO data. It does not verify legal entity identity,
    bank ownership, tax registration, goods receipt, payment status, or real supplier legitimacy.
    The final payment decision remains with an authorised human reviewer.
    """)
    st.code("Absolute amount tolerance = 5.00 currency units\\nExact document hash match = duplicate", language="text")
