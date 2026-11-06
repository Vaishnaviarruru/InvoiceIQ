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
/* Compact, readable metric cards across Process, Activity and PO pages */
[data-testid="stMetric"] {
  background:var(--surface);
  border:1px solid var(--line);
  border-radius:7px;
  padding:12px 14px;
  box-shadow:none;
  min-width:0;
}
[data-testid="stMetricLabel"] {
  color:var(--muted);
  font-size:.72rem;
  text-transform:uppercase;
  letter-spacing:.055em;
  font-weight:600;
}
[data-testid="stMetricValue"] {
  color:var(--ink);
  font-size:1.35rem !important;
  line-height:1.25 !important;
  font-weight:600 !important;
  letter-spacing:-.025em !important;
  overflow-wrap:anywhere;
  word-break:break-word;
}
[data-testid="stMetricValue"] > div {
  font-size:inherit !important;
  font-weight:inherit !important;
  line-height:inherit !important;
  white-space:normal !important;
  overflow-wrap:anywhere;
}
[data-testid="stMetricDelta"] {font-size:.78rem !important;}

/* Keep tables and form controls visually consistent and less heavy */
[data-testid="stDataFrame"], [data-testid="stTable"] {font-size:.88rem;}
[data-testid="stDataFrame"] [role="columnheader"] {font-weight:600 !important;}
.stMarkdown p, .stMarkdown li {font-size:.94rem;}
.stTextInput label, .stSelectbox label, .stTextArea label, .stRadio label {font-size:.9rem;}
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
