import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os

# --- Page Settings ---
st.set_page_config(page_title="Zeeshan Mobile - Pro POS", layout="wide")

# --- Database Files ---
BILL_DATA = "all_sales.csv"
CUST_DATA = "customers_ledger.csv"

# --- Load Data ---
if 'all_bills' not in st.session_state:
    if os.path.exists(BILL_DATA):
        st.session_state.all_bills = pd.read_csv(BILL_DATA).to_dict('records')
    else:
        st.session_state.all_bills = []

if 'customer_db' not in st.session_state:
    if os.path.exists(CUST_DATA):
        st.session_state.customer_db = pd.read_csv(CUST_DATA).set_index('Name').to_dict('index')
    else:
        st.session_state.customer_db = {"Walking Customer": {"phone": "-", "balance": 0.0}}

if 'cart' not in st.session_state:
    st.session_state.cart = []

# --- Functions ---
def save_to_files():
    pd.DataFrame(st.session_state.all_bills).to_csv(BILL_DATA, index=False)
    ledger_df = pd.DataFrame.from_dict(st.session_state.customer_db, orient='index').reset_index().rename(columns={'index': 'Name'})
    ledger_df.to_csv(CUST_DATA, index=False)

def create_pdf(name, items, total, old_bal, paid, bill_id):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(190, 10, "ZEESHAN MOBILE ACCESSORIES", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 5, f"Bill ID: {bill_id} | Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, f"Customer: {name}")
    pdf.ln(10)
    # Table Header
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(70, 8, " Item", 1, 0, 'L', True); pdf.cell(30, 8, "Qty", 1, 0, 'C', True)
    pdf.cell(45, 8, "Price", 1, 0, 'C', True); pdf.cell(45, 8, "Total", 1, 1, 'C', True)
    # Rows
    pdf.set_font("Arial", '', 10)
    for i in items:
        pdf.cell(70, 8, f" {i['Item']}", 1); pdf.cell(30, 8, str(i['Qty']), 1, 0, 'C')
        pdf.cell(45, 8, str(i['Price']), 1, 0, 'C'); pdf.cell(45, 8, str(i['Total']), 1, 1, 'C')
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(145, 8, "Bill Total:", 0, 0, 'R'); pdf.cell(45, 8, f"Rs. {total}", 1, 1, 'C')
    pdf.cell(145, 8, "Old Balance:", 0, 0, 'R'); pdf.cell(45, 8, f"Rs. {old_bal}", 1, 1, 'C')
    pdf.cell(145, 8, "Paid:", 0, 0, 'R'); pdf.cell(45, 8, f"Rs. {paid}", 1, 1, 'C')
    pdf.set_text_color(255, 0, 0)
    pdf.cell(145, 8, "Remaining Ledger:", 0, 0, 'R'); pdf.cell(45, 8, f"Rs. {(total+old_bal)-paid}", 1, 1, 'C')
    return pdf.output(dest='S').encode('latin-1')

# --- MAIN UI ---
st.title("📱 Zeeshan Mobile Pro POS")

t1, t2, t3, t4 = st.tabs(["🛒 Billing", "🔍 Search & Edit", "📊 Monthly Sales", "💾 Ledger & Backup"])

# --- TAB 1: BILLING ---
with t1:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Customer")
        cust_list = list(st.session_state.customer_db.keys())
        selected_cust = st.selectbox("Search/Select Customer", ["+ Add New"] + cust_list)
        
        if selected_cust == "+ Add New":
            new_n = st.text_input("New Name")
            new_p = st.text_input("New Phone")
            if st.button("Save New Customer"):
                st.session_state.customer_db[new_n] = {"phone": new_p, "balance": 0.0}
                save_to_files()
                st.rerun()
        else:
            curr_bal = st.session_state.customer_db[selected_cust]['balance']
            st.info(f"Old Balance: Rs. {curr_bal}")
            
    with c2:
        st.subheader("Items")
        it_name = st.text_input("Item Description")
        col_q, col_p = st.columns(2)
        it_qty = col_q.number_input("Qty", min_value=1, step=1)
        it_prc = col_p.number_input("Price", min_value=0)
        if st.button("➕ Add to Bill"):
            st.session_state.cart.append({"Item": it_name, "Qty": it_qty, "Price": it_prc, "Total": it_qty*it_prc})

    if st.session_state.cart:
        df_cart = pd.DataFrame(st.session_state.cart)
        st.table(df_cart)
        total_b = df_cart['Total'].sum()
        paid_b = st.number_input("Amount Paid Now", min_value=0)
        
        if st.button("✅ Finalize Bill"):
            b_id = f"INV-{datetime.now().strftime('%H%M%S')}"
            date_s = datetime.now().strftime("%Y-%m-%d")
            # Save items to all_sales
            for item in st.session_state.cart:
                item_record = item.copy()
                item_record.update({"BillID": b_id, "Customer": selected_cust, "Date": date_s})
                st.session_state.all_bills.append(item_record)
            
            # Update Ledger
            new_b = (total_b + curr_bal) - paid_b
            st.session_state.customer_db[selected_cust]['balance'] = new_b
            save_to_files()
            
            # PDF Download
            pdf_b = create_pdf(selected_cust, st.session_state.cart, total_b, curr_bal, paid_b, b_id)
            st.download_button("📥 Download Bill PDF", pdf_b, f"Bill_{selected_cust}.pdf", "application/pdf")
            
            st.session_state.cart = []
            st.success("Bill Saved & Ledger Updated!")

# --- TAB 2: SEARCH & EDIT ---
with t2:
    st.subheader("Search Bills")
    df_history = pd.DataFrame(st.session_state.all_bills)
    if not df_history.empty:
        s_query = st.text_input("Enter Customer Name or Bill ID to search")
        res = df_history[df_history['Customer'].str.contains(s_query, case=False) | df_history['BillID'].str.contains(s_query, case=False)]
        st.dataframe(res, use_container_width=True)
        
        if st.button("Clear History (Reset All Sales)"):
            if st.checkbox("I am sure I want to delete all sales history"):
                st.session_state.all_bills = []
                save_to_files()
                st.rerun()

# --- TAB 3: MONTHLY SALES ---
with t3:
    st.subheader("Monthly Item-wise Report")
    if not df_history.empty:
        df_history['Date'] = pd.to_datetime(df_history['Date'])
        df_history['Month'] = df_history['Date'].dt.strftime('%B %Y')
        sel_month = st.selectbox("Select Month", df_history['Month'].unique())
        
        m_data = df_history[df_history['Month'] == sel_month]
        summary = m_data.groupby('Item').agg({'Qty': 'sum', 'Total': 'sum'}).reset_index()
        st.table(summary)
        st.metric("Total Sale of Month", f"Rs. {summary['Total'].sum()}")

# --- TAB 4: BACKUP ---
with t4:
    st.subheader("Full Ledger (Udhaar Record)")
    full_ledger = pd.DataFrame.from_dict(st.session_state.customer_db, orient='index').reset_index()
    st.dataframe(full_ledger)
    
    st.divider()
    st.subheader("Download Data Backup")
    c_b1, c_b2 = st.columns(2)
    sales_csv = pd.DataFrame(st.session_state.all_bills).to_csv(index=False).encode('utf-8')
    c_b1.download_button("📥 Download All Sales (CSV)", sales_csv, "sales_backup.csv", "text/csv")
    
    led_csv = full_ledger.to_csv(index=False).encode('utf-8')
    c_b2.download_button("📥 Download Ledger (CSV)", led_csv, "ledger_backup.csv", "text/csv")
