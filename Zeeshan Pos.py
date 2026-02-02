import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os

# --- Basic Config ---
st.set_page_config(page_title="Zeeshan Mobile Accessories", layout="wide")

# Files for saving data
SALES_FILE = "sales_record.csv"
LEDGER_FILE = "customer_ledger.csv"

# --- Load Data from Files ---
if 'all_sales' not in st.session_state:
    if os.path.exists(SALES_FILE):
        st.session_state.all_sales = pd.read_csv(SALES_FILE).to_dict('records')
    else:
        st.session_state.all_sales = []

if 'ledger' not in st.session_state:
    if os.path.exists(LEDGER_FILE):
        st.session_state.ledger = pd.read_csv(LEDGER_FILE).set_index('Name').to_dict('index')
    else:
        st.session_state.ledger = {"Walking Customer": {"balance": 0.0}}

if 'cart' not in st.session_state:
    st.session_state.cart = []

def save_all():
    pd.DataFrame(st.session_state.all_sales).to_csv(SALES_FILE, index=False)
    ledger_df = pd.DataFrame.from_dict(st.session_state.ledger, orient='index').reset_index().rename(columns={'index': 'Name'})
    ledger_df.to_csv(LEDGER_FILE, index=False)

# --- UI ---
st.title("📱 Zeeshan Mobile Accessories - POS")
st.write("Contact: 03296971255")

tabs = st.tabs(["🛒 Bill Banayein", "🔍 Search & Edit", "📊 Monthly Report", "💾 Backup"])

# --- TAB 1: BILLING ---
with tabs[0]:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Customer Info")
        c_list = list(st.session_state.ledger.keys())
        selected_c = st.selectbox("Customer Select Karein", ["+ Naya Customer"] + c_list)
        
        if selected_c == "+ Naya Customer":
            new_name = st.text_input("Customer Name")
            if st.button("Add Customer"):
                st.session_state.ledger[new_name] = {"balance": 0.0}
                save_all()
                st.rerun()
        else:
            old_bal = st.session_state.ledger[selected_c]['balance']
            st.info(f"Purana Udhaar: Rs. {old_bal}")

    with c2:
        st.subheader("Items Add Karein")
        it_name = st.text_input("Item Ka Naam")
        col_q, col_p = st.columns(2)
        it_qty = col_q.number_input("Quantity", min_value=1, step=1)
        it_prc = col_p.number_input("Price", min_value=0)
        
        if st.button("Add to List"):
            st.session_state.cart.append({"Item": it_name, "Qty": it_qty, "Price": it_prc, "Total": it_qty * it_prc})

    if st.session_state.cart:
        df_cart = pd.DataFrame(st.session_state.cart)
        st.table(df_cart)
        total_bill = df_cart['Total'].sum()
        paid = st.number_input("Kitne Paise Diye?", min_value=0)
        
        if st.button("✅ Bill Final Karein"):
            inv_id = f"ZM-{datetime.now().strftime('%H%M%S')}"
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Save to history
            for item in st.session_state.cart:
                rec = item.copy()
                rec.update({"BillID": inv_id, "Customer": selected_c, "Date": current_date})
                st.session_state.all_sales.append(rec)
            
            # Update Ledger
            new_bal = (total_bill + old_bal) - paid
            st.session_state.ledger[selected_c]['balance'] = new_bal
            save_all()
            
            st.success(f"Bill Saved! Naya Balance: {new_bal}")
            st.session_state.cart = []
            st.rerun()

# --- TAB 2: SEARCH & EDIT ---
with tabs[1]:
    st.subheader("Purany Bills Ki Talash")
    if st.session_state.all_sales:
        df_history = pd.DataFrame(st.session_state.all_sales)
        search = st.text_input("Customer ka naam ya Bill ID likhein")
        res = df_history[df_history['Customer'].str.contains(search, case=False) | df_history['BillID'].str.contains(search, case=False)]
        st.dataframe(res)
    else:
        st.write("Abhi koi sale nahi hui.")

# --- TAB 3: MONTHLY REPORT ---
with tabs[2]:
    st.subheader("Mahany Ki Report")
    if st.session_state.all_sales:
        df_rep = pd.DataFrame(st.session_state.all_sales)
        df_rep['Date'] = pd.to_datetime(df_rep['Date'])
        df_rep['Month'] = df_rep['Date'].dt.strftime('%B %Y')
        
        sel_m = st.selectbox("Mahana Select Karein", df_rep['Month'].unique())
        m_data = df_rep[df_rep['Month'] == sel_m]
        summary = m_data.groupby('Item').agg({'Qty': 'sum', 'Total': 'sum'}).reset_index()
        st.table(summary)
        st.metric("Total Sale", f"Rs. {summary['Total'].sum()}")

# --- TAB 4: BACKUP ---
with tabs[3]:
    st.subheader("Data Backup & Ledger")
    led_df = pd.DataFrame.from_dict(st.session_state.ledger, orient='index').reset_index()
    st.dataframe(led_df)
    
    st.divider()
    if st.session_state.all_sales:
        csv = pd.DataFrame(st.session_state.all_sales).to_csv(index=False).encode('utf-8')
        st.download_button("📥 Poori Sales Download Karein (CSV)", csv, "sales_backup.csv", "text/csv")
