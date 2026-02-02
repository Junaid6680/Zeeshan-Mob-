import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os

# --- Page Setup ---
st.set_page_config(page_title="Zeeshan Mobile Accessories", layout="wide")

# Database Files
SALES_DB = "sales_history.csv"
LEDGER_DB = "customer_ledger.csv"

# --- Data Persistence ---
if 'all_sales' not in st.session_state:
    if os.path.exists(SALES_DB):
        st.session_state.all_sales = pd.read_csv(SALES_DB).to_dict('records')
    else:
        st.session_state.all_sales = []

if 'ledger' not in st.session_state:
    if os.path.exists(LEDGER_DB):
        st.session_state.ledger = pd.read_csv(LEDGER_DB).set_index('Name').to_dict('index')
    else:
        st.session_state.ledger = {"Walking Customer": {"phone": "-", "balance": 0.0}}

if 'cart' not in st.session_state:
    st.session_state.cart = []

def save_to_disk():
    pd.DataFrame(st.session_state.all_sales).to_csv(SALES_DB, index=False)
    ledger_df = pd.DataFrame.from_dict(st.session_state.ledger, orient='index').reset_index().rename(columns={'index': 'Name'})
    ledger_df.to_csv(LEDGER_DB, index=False)

# --- UI Layout ---
st.title("📱 Zeeshan Mobile Accessories - POS System")
st.write("Contact: 03296971255")

tabs = st.tabs(["🛒 Bill Banayein", "🔍 Search & History", "📊 Monthly Reports", "💾 Ledger & Backup"])

# --- TAB 1: BILLING ---
with tabs[0]:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Customer Details")
        c_list = list(st.session_state.ledger.keys())
        selected_c = st.selectbox("Customer Chunain", ["
