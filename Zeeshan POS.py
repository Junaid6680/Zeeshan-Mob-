import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import sqlite3

# Page Configuration
st.set_page_config(page_title="Zeeshan Mobile POS", layout="wide", page_icon="📱")

# ================= DATABASE SETUP =================
def get_connection():
    conn = sqlite3.connect("pos.db", check_same_thread=False)
    return conn

conn = get_connection()
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS customers(name TEXT PRIMARY KEY, phone TEXT, balance REAL)")
c.execute("CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, customer TEXT, total REAL, paid REAL)")
conn.commit()

# ================= SESSION STATE =================
if "cart" not in st.session_state:
    st.session_state.cart = []

# ================= PDF GENERATION FUNCTION =================
def create_pdf(bill_id, customer, phone, items, total, paid):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 10, "ZEESHAN MOBILE ACCESSORIES", ln=True, align="C")
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, "Hall Road Lahore | Contact: 03296971255", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 7, f"Bill ID: {bill_id}", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 7, f"Customer: {customer}", ln=True)
    pdf.cell(0, 7, f"Phone: {phone}", ln=True)
    pdf.cell(0, 7, f"Date: {datetime.now().strftime('%d-%m-%Y %H:%M')}", ln=True)
    pdf.ln(5)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(80, 8, "Item Description", border=1, fill=True)
    pdf.cell(25, 8, "Qty", border=1, fill=True, align="C")
    pdf.cell(40, 8, "Price", border=1, fill=True, align="C")
    pdf.cell(45, 8, "Total", border=1, fill=True, align="C", ln=True)
    pdf.set_font("Arial", size=11)
    for i in items:
        pdf.cell(80, 8, str(i["item"]), border=1)
        pdf.cell(25, 8, str(i["qty"]), border=1, align="C")
        pdf.cell(40, 8, str(i["price"]), border=1, align="C")
        pdf.cell(45, 8, str(i["qty"] * i["price"]), border=1, align="C", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, f"Grand Total: Rs. {total}", ln=True, align="R")
    pdf.cell(0, 8, f"Amount Paid: Rs. {paid}", ln=True, align="R")
    pdf.cell(0, 8, f"Balance: Rs. {total - paid}", ln=True, align="R")
    return bytes(pdf.output(dest="S"))

# ================= UI LAYOUT =================
st.title("🛒 Zeeshan Mobile Accessories POS")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📦 Billing Section")
    with st.form("billing_form", clear_on_submit=True):
        it_name = st.text_input("Item Name")
        it_qty = st.number_input("Quantity", min_value=1, step=1)
        it_price = st.number_input("Price (Per Unit)", min_value=0.0, step=10.0)
        submitted = st.form_submit_button("➕ Add Item to Cart")
        if submitted and it_name:
            st.session_state.cart.append({"item": it_name, "qty": it_qty, "price": it_price})
            st.toast(f"Added {it_name}")

with col2:
    st.subheader("🧾 Cart Items")
    if st.session_state.cart:
        df_cart = pd.DataFrame(st.session_state.cart)
        df_cart["Subtotal"] = df_cart["qty"] * df_cart["price"]
        st.dataframe(df_cart, use_container_width=True)
        total_bill = df_cart["Subtotal"].sum()
        if st.button("🗑️ Clear All Items"):
            st.session_state.cart = []
            st.rerun()
    else:
        st.info("Cart is empty.")
        total_bill = 0.0

st.divider()

# ================= CUSTOMER & PAYMENT =================
c1, c2 = st.columns(2)
with c1:
    st.subheader("👤 Customer Info")
    cust_data = pd.read_sql("SELECT * FROM customers", conn)
    names_list = ["Walk-in"] + cust_data["name"].tolist()
    final_cust = st.selectbox("Select Customer", names_list)
    final_phone = ""
    if final_cust != "Walk-in":
        final_phone = cust_data[cust_data.name == final_cust].iloc[0]["phone"]
    with st.expander("➕ Add New Customer"):
        n_name = st.text_input("Customer Name")
        n_phone = st.text_input("Phone Number")
        if st.button("Save Customer"):
            if n_name:
                try:
                    c.execute("INSERT INTO customers VALUES (?,?,?)", (n_name, n_phone, 0.0))
                    conn.commit()
                    st.rerun()
                except: st.error("Exists!")

with c2:
    st.subheader("💰 Payment Details")
    st.markdown(f"### Total Bill: **Rs. {total_bill}**")
    amt_paid = st.number_input("Paid Amount", min_value=0.0, value=float(total_bill))
    if st.button("✅ Generate & Save Bill"):
        if st.session_state.cart:
            b_id = f"BILL-{datetime.now().strftime('%y%m%d%H%M%S')}"
            c.execute("INSERT INTO sales(date, customer, total, paid) VALUES (?,?,?,?)",
                      (datetime.now().strftime('%Y-%m-%d'), final_cust, total_bill, amt_paid))
            conn.commit()
            pdf_bytes = create_pdf(b_id, final_cust, final_phone, st.session_state.cart, total_bill, amt_paid)
            st.download_button(label="📥 Download Receipt (PDF)", data=pdf_bytes, file_name=f"{b_id}.pdf", mime="application/pdf")
            st.success("Saved!")

# ================= SALES HISTORY =================
st.divider()
st.subheader("📊 Sales History")
history = pd.read_sql("SELECT * FROM sales ORDER BY id DESC", conn)
st.dataframe(history, use_container_width=True)

# ================= BACKUP SECTION =================
st.divider()
st.subheader("💾 System Backup")
col_b1, col_b2 = st.columns(2)

with col_b1:
    # Sales Backup
    if not history.empty:
        csv_sales = history.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Sales Backup (CSV)",
            data=csv_sales,
            file_name=f"sales_backup_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime='text/csv',
        )

with col_b2:
    # Customer Backup
    if not cust_data.empty:
        csv_cust = cust_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Customer List (CSV)",
            data=csv_cust,
            file_name=f"customers_backup_{datetime.now().strftime('%Y-%m-%d')}.csv",
            mime='text/csv',
        )

st.info("Backup tip: Hafte mein ek baar CSV files download kar ke apne Google Drive ya email par save kar liya karein.")
