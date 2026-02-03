import streamlit as st
import pandas as pd
from fpdf import FPDF
import time

# --- Page Config ---
st.set_page_config(page_title="Zeeshan Mobile POS", layout="wide")

# --- CSS for Watermark (Screen Display) ---
st.markdown("""
    <style>
    .watermark {
        position: fixed; top: 50%; left: 50%;
        transform: translate(-50%, -50%) rotate(-45deg);
        opacity: 0.05; font-size: 80px; color: gray;
        z-index: -1; pointer-events: none;
    }
    </style>
    <div class="watermark">ZEESHAN MOBILE ACCESSORIES</div>
    """, unsafe_allow_html=True)

# --- Session State Data ---
if 'customer_db' not in st.session_state:
    st.session_state.customer_db = {"Walking Customer": {"phone": "-", "balance": 0.0}}
if 'temp_items' not in st.session_state:
    st.session_state.temp_items = []
if 'sales_history' not in st.session_state:
    st.session_state.sales_history = pd.DataFrame(columns=["Bill No", "Date", "Customer", "Total", "Paid"])
if 'bill_counter' not in st.session_state:
    st.session_state.bill_counter = 1

# --- PDF Function (FIXED ERROR LINE) ---
def create_pdf(bill_no, cust_name, phone, items, bill_total, old_bal, paid_amt, is_only_payment=False):
    pdf = FPDF()
    pdf.add_page()
    
    # 1. Watermark inside PDF
    pdf.set_font("Arial", 'B', 50)
    pdf.set_text_color(240, 240, 240) 
    pdf.text(35, 150, "ZEESHAN MOBILE")
    
    # Header
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(190, 10, "ZEESHAN MOBILE ACCESSORIES", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(190, 7, "Contact: 03296971255", ln=True, align='C') 
    pdf.ln(5)
    
    # Bill Info
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(95, 8, f"Bill No: {bill_no}")
    pdf.cell(95, 8, f"Date: {pd.Timestamp.now().strftime('%d-%b-%Y')}", ln=True, align='R')
    pdf.cell(95, 8, f"Customer: {cust_name}")
    pdf.cell(95, 8, f"Cust Phone: {phone}", ln=True, align='R') 
    pdf.ln(10)
    
    if not is_only_payment:
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(80, 10, "Item Name", 1, 0, 'C', True)
        pdf.cell(30, 10, "Qty", 1, 0, 'C', True)
        pdf.cell(40, 10, "Unit Price", 1, 0, 'C', True)
        pdf.cell(40, 10, "Total", 1, 1, 'C', True)
        
        pdf.set_font("Arial", '', 10)
        for item in items:
            pdf.cell(80, 10, f" {item['Item']}", 1)
            pdf.cell(30, 10, str(item['Qty']), 1, 0, 'C')
            pdf.cell(40, 10, str(item['Price']), 1, 0, 'C')
            pdf.cell(40, 10, str(item['Total']), 1, 1, 'C')
        pdf.ln(5)

    # Summary
    new_bal = (bill_total + old_bal) - paid_amt
    pdf.set_font("Arial", 'B', 10)
    if not is_only_payment:
        pdf.cell(150, 8, "Current Bill:", 0, 0, 'R'); pdf.cell(40, 8, f"Rs. {bill_total}", 1, 1, 'C')
    
    pdf.cell(150, 8, "Previous Udhaar:", 0, 0, 'R'); pdf.cell(40, 8, f"Rs. {old_bal}", 1, 1, 'C')
    pdf.set_fill_color(200, 255, 200)
    pdf.cell(150, 8, "Amount Received:", 0, 0, 'R'); pdf.cell(40, 8, f"Rs. {paid_amt}", 1, 1, 'C', True)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(150, 10, "Remaining Balance:", 0, 0, 'R'); pdf.cell(40, 10, f"Rs. {new_bal}", 1, 1, 'C')
    
    # FIXED LINE: Added latin-1 encoding correctly
    return pdf.output(dest='S').encode('latin-1')

# --- UI Interface ---
st.title("🛒 Zeeshan Mobile Accessories POS")

col_main, col_sidebar = st.columns([2, 1])

with col_sidebar:
    st.header("👤 Customer & Payment")
    c_list = sorted(list(st.session_state.customer_db.keys()))
    sel_cust = st.selectbox("Select Customer", c_list)
    c_data = st.session_state.customer_db[sel_cust]
    st.info(f"📌 **Balance: Rs. {c_data['balance']}**")
    
    st.divider()
    st.subheader("💸 Quick Payment")
    pay_val = st.number_input("Received Amount", min_value=0.0, key="quick_p")
    if st.button("Confirm Cash Receive"):
        if pay_val > 0:
            b_id = f"PAY-{st.session_state.bill_counter}"
            old_b = c_data['balance']
            st.session_state.customer_db[sel_cust]['balance'] -= pay_val
            
            new_e = pd.DataFrame([[b_id, pd.Timestamp.now(), sel_cust, 0, pay_val]], columns=["Bill No", "Date", "Customer", "Total", "Paid"])
            st.session_state.sales_history = pd.concat([st.session_state.sales_history, new_e], ignore_index=True)
            
            pdf_p = create_pdf(b_id, sel_cust, c_data['phone'], [], 0, old_b, pay_val, True)
            st.download_button("📥 Download Receipt", pdf_p, f"Receipt_{sel_cust}.pdf", "application/pdf")
            st.session_state.bill_counter += 1
            st.rerun()

    with st.expander("Add New Customer"):
        n_name = st.text_input("Full Name")
        n_phone = st.text_input("Phone Number")
        if st.button("Save Customer"):
            if n_name:
                st.session_state.customer_db[n_name] = {"phone": n_phone, "balance": 0.0}
                st.rerun()

with col_main:
    st.header("📦 Billing Section")
    c1, c2, c3 = st.columns([3, 1, 1])
    it_name = c1.text_input("Item")
    it_qty = c2.number_input("Qty", min_value=1, value=1)
    it_price = c3.number_input("Price", min_value=0)
    
    if st.button("➕ Add Item"):
        if it_name:
            st.session_state.temp_items.append({"Item": it_name, "Qty": it_qty, "Price": it_price, "Total": it_qty * it_price})
    
    if st.session_state.temp_items:
        df_t = pd.DataFrame(st.session_state.temp_items)
        st.table(df_t)
        t_bill = df_t['Total'].sum()
        st.metric("Total Bill", f"Rs. {t_bill}")
        p_today = st.number_input("Paid Amount", min_value=0.0)
        
        if st.button("✅ Save & Print Bill"):
            b_id = f"ZMA-{st.session_state.bill_counter}"
            old_b = c_data['balance']
            st.session_state.customer_db[sel_cust]['balance'] = (t_bill + old_b) - p_today
            
            new_s = pd.DataFrame([[b_id, pd.Timestamp.now(), sel_cust, t_bill, p_today]], columns=["Bill No", "Date", "Customer", "Total", "Paid"])
            st.session_state.sales_history = pd.concat([st.session_state.sales_history, new_s], ignore_index=True)
            
            pdf_d = create_pdf(b_id, sel_cust, c_data['phone'], st.session_state.temp_items, t_bill, old_b, p_today)
            st.download_button(f"📥 DOWNLOAD PDF BILL ({b_id})", pdf_d, f"Bill_{b_id}.pdf", "application/pdf")
            
            st.session_state.temp_items = []
            st.session_state.bill_counter += 1
            st.success("Bill Saved!")

st.divider()
st.header("📒 Ledger & Search")
s_val = st.text_input("🔍 Search Name")
l_df = pd.DataFrame.from_dict(st.session_state.customer_db, orient='index').reset_index()
l_df.columns = ["Customer", "Phone", "Balance"]
if s_val:
    l_df = l_df[l_df["Customer"].str.contains(s_val, case=False)]
st.dataframe(l_df, use_container_width=True)
st.download_button("💾 Backup Ledger (CSV)", l_df.to_csv(index=False).encode('utf-8'), "Zeeshan_Backup.csv", "text/csv")

# --- REPORTS ---
st.divider()
st.header("📊 Sales Reports")
if not st.session_state.sales_history.empty:
    h = st.session_state.sales_history
    h['Date'] = pd.to_datetime(h['Date'])
    now = pd.Timestamp.now()
    d_s = h[h['Date'].dt.date == now.date()]['Total'].sum()
    w_s = h[h['Date'] > (now - pd.Timedelta(days=7))]['Total'].sum()
    m_s = h[h['Date'] > (now - pd.Timedelta(days=30))]['Total'].sum()
    
    r1, r2, r3 = st.columns(3)
    r1.metric("Today Sale", f"Rs. {d_s}")
    r2.metric("Weekly Sale", f"Rs. {w_s}")
    r3.metric("Monthly Sale", f"Rs. {m_s}")
