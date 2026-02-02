import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os

# --- Page Config ---
st.set_page_config(page_title="Zeeshan Mobile - Advanced POS", layout="wide")

# --- File Names for Backup/Storage ---
BILL_FILE = "bills_data.csv"
LEDGER_FILE = "ledger_data.csv"

# Load or Initialize Data
if os.path.exists(BILL_FILE):
    st.session_state.all_bills = pd.read_csv(BILL_FILE).to_dict('records')
else:
    st.session_state.all_bills = []

if os.path.exists(LEDGER_FILE):
    st.session_state.customer_db = pd.read_csv(LEDGER_FILE, index_index=True).set_index('Name').to_dict('index')
else:
    st.session_state.customer_db = {"Walking Customer": {"phone": "-", "balance": 0.0}}

if 'cart' not in st.session_state:
    st.session_state.cart = []

# --- Helper Functions ---
def save_data():
    pd.DataFrame(st.session_state.all_bills).to_csv(BILL_FILE, index=False)
    ledger_df = pd.DataFrame.from_dict(st.session_state.customer_db, orient='index').reset_index().rename(columns={'index': 'Name'})
    ledger_df.to_csv(LEDGER_FILE, index=False)

def create_pdf(name, items, total, old_bal, paid):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "ZEESHAN MOBILE ACCESSORIES", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 5, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(100, 10, f"Customer: {name}")
    pdf.ln(10)
    # Table Header
    pdf.cell(80, 8, "Item", 1); pdf.cell(30, 8, "Qty", 1); pdf.cell(40, 8, "Price", 1); pdf.cell(40, 8, "Total", 1, ln=True)
    for i in items:
        pdf.cell(80, 8, str(i['Item']), 1); pdf.cell(30, 8, str(i['Qty']), 1); pdf.cell(40, 8, str(i['Price']), 1); pdf.cell(40, 8, str(i['Total']), 1, ln=True)
    pdf.ln(5)
    pdf.cell(190, 8, f"Grand Total (inc. old bal): {total + old_bal}", ln=True)
    pdf.cell(190, 8, f"Paid: {paid}", ln=True)
    pdf.cell(190, 8, f"New Balance: {(total + old_bal) - paid}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- UI ---
st.title("📱 Zeeshan Mobile Advanced POS")

tabs = st.tabs(["🛒 Billing", "🔍 Search & Edit", "📊 Monthly Reports", "💾 Backup & Ledger"])

# --- TAB 1: BILLING ---
with tabs[0]:
    c1, c2 = st.columns([1, 2])
    with c1:
        cust_name = st.selectbox("Select Customer", list(st.session_state.customer_db.keys()))
        curr_bal = st.session_state.customer_db[cust_name]['balance']
        st.info(f"Old Balance: Rs. {curr_bal}")
        
    with c2:
        it_name = st.text_input("Item Name")
        ic1, ic2 = st.columns(2)
        it_qty = ic1.number_input("Qty", min_value=1)
        it_prc = ic2.number_input("Price", min_value=0)
        if st.button("Add to Bill"):
            st.session_state.cart.append({"Item": it_name, "Qty": it_qty, "Price": it_prc, "Total": it_qty*it_prc, "Date": datetime.now().strftime("%Y-%m-%d")})

    if st.session_state.cart:
        df_cart = pd.DataFrame(st.session_state.cart)
        st.table(df_cart)
        total_bill = df_cart['Total'].sum()
        paid_now = st.number_input("Amount Paid", min_value=0)
        
        if st.button("Finalize Bill"):
            bill_id = f"INV-{datetime.now().strftime('%H%M%S')}"
            for item in st.session_state.cart:
                item['BillID'] = bill_id
                item['Customer'] = cust_name
                st.session_state.all_bills.append(item)
            
            new_bal = (total_bill + curr_bal) - paid_now
            st.session_state.customer_db[cust_name]['balance'] = new_bal
            save_data()
            st.success(f"Bill Saved! New Balance: {new_bal}")
            st.session_state.cart = []
            st.rerun()

# --- TAB 2: SEARCH & EDIT ---
with tabs[1]:
    st.subheader("Search & Update Bills")
    df_all = pd.DataFrame(st.session_state.all_bills)
    if not df_all.empty:
        search_id = st.text_input("Enter Bill ID or Customer Name to Edit")
        filtered = df_all[df_all['BillID'].str.contains(search_id, case=False) | df_all['Customer'].str.contains(search_id, case=False)]
        st.write(filtered)
        
        if not filtered.empty:
            st.warning("Editing here will update the bill records. Note: Manually update ledger if amount changes.")
            if st.button("Delete Selected Bill Records"):
                st.session_state.all_bills = [b for b in st.session_state.all_bills if b['BillID'] not in filtered['BillID'].values]
                save_data()
                st.rerun()

# --- TAB 3: MONTHLY REPORTS ---
with tabs[2]:
    st.subheader("Monthly Item Sales Report")
    if st.session_state.all_bills:
        df_report = pd.DataFrame(st.session_state.all_bills)
        df_report['Date'] = pd.to_datetime(df_report['Date'])
        df_report['Month'] = df_report['Date'].dt.strftime('%Y-%m')
        
        selected_month = st.selectbox("Select Month", df_report['Month'].unique())
        month_data = df_report[df_report['Month'] == selected_month]
        
        # Summary by Item
        summary = month_data.groupby('Item').agg({'Qty': 'sum', 'Total': 'sum'}).reset_index()
        st.write(f"### Sales for {selected_month}")
        st.table(summary)
        st.metric("Total Monthly Revenue", f"Rs. {summary['Total'].sum()}")

# --- TAB 4: BACKUP & LEDGER ---
with tabs[3]:
    st.subheader("Customer Ledger")
    led_df = pd.DataFrame.from_dict(st.session_state.customer_db, orient='index').reset_index()
    st.dataframe(led_df)
    
    st.divider()
    st.subheader("System Backup")
    c_b1, c_b2 = st.columns(2)
    with c_b1:
        if st.session_state.all_bills:
            csv_bills = pd.DataFrame(st.session_state.all_bills).to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Bills Backup (CSV)", csv_bills, "bills_backup.csv", "text/csv")
    with c_b2:
        csv_ledger = pd.DataFrame(st.session_state.customer_db).to_csv().encode('utf-8')
        st.download_button("📥 Download Ledger Backup (CSV)", csv_ledger, "ledger_backup.csv", "text/csv")

    if st.button("Add New Customer to System"):
        new_c = st.text_input("New Customer Name")
        if st.button("Confirm Add"):
            st.session_state.customer_db[new_c] = {"phone": "-", "balance": 0.0}
            save_data()
            st.success("Added!")
