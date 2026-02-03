import streamlit as st import pandas as pd from fpdf import FPDF from datetime import datetime import sqlite3 from io import BytesIO

st.set_page_config(page_title="Zeeshan Mobile Accessories POS", layout="wide")

================= DATABASE =================

conn = sqlite3.connect("pos.db", check_same_thread=False) c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS customers(name TEXT PRIMARY KEY, phone TEXT, balance REAL)") c.execute("CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, customer TEXT, total REAL, paid REAL)") conn.commit()

================= SESSION STATE =================

if "cart" not in st.session_state: st.session_state.cart = []

================= PDF FUNCTION =================

def create_pdf(bill_id, customer, phone, items, total, paid): pdf = FPDF() pdf.add_page()

pdf.set_font("Helvetica", "B", 16)
pdf.cell(0, 10, "ZEESHAN MOBILE ACCESSORIES", ln=True, align="C")
pdf.set_font("Helvetica", size=10)
pdf.cell(0, 6, "Hall Road Lahore", ln=True, align="C")
pdf.cell(0, 6, "Contact: 03296971255", ln=True, align="C")
pdf.ln(5)

pdf.set_font("Helvetica", size=11)
pdf.cell(0, 6, f"Bill ID: {bill_id}", ln=True)
pdf.cell(0, 6, f"Customer: {customer}", ln=True)
pdf.cell(0, 6, f"Phone: {phone}", ln=True)
pdf.cell(0, 6, f"Date: {datetime.now().strftime('%d-%m-%Y %H:%M')}", ln=True)
pdf.ln(5)

pdf.set_font("Helvetica", "B", 11)
pdf.cell(80, 8, "Item")
pdf.cell(30, 8, "Qty")
pdf.cell(40, 8, "Price")
pdf.cell(40, 8, "Total", ln=True)

pdf.set_font("Helvetica", size=11)
for i in items:
    pdf.cell(80, 8, i["item"])
    pdf.cell(30, 8, str(i["qty"]))
    pdf.cell(40, 8, str(i["price"]))
    pdf.cell(40, 8, str(i["qty"] * i["price"]), ln=True)

pdf.ln(5)
pdf.cell(0, 8, f"Total Bill: Rs. {total}", ln=True)
pdf.cell(0, 8, f"Paid: Rs. {paid}", ln=True)

pdf_bytes = pdf.output(dest="S").encode("latin-1")
return pdf_bytes

================= UI =================

st.title("🛒 Zeeshan Mobile Accessories POS")

col1, col2 = st.columns(2)

with col1: st.subheader("📦 Billing Section") item = st.text_input("Item Name") qty = st.number_input("Qty", 1, 10000, 1) price = st.number_input("Price", 1, 100000, 1)

if st.button("➕ Add Item"):
    st.session_state.cart.append({"item": item, "qty": qty, "price": price})

with col2: st.subheader("🧾 Cart") if st.session_state.cart: df = pd.DataFrame(st.session_state.cart) df["Total"] = df.qty * df.price st.dataframe(df) total_bill = df["Total"].sum() else: total_bill = 0

st.markdown(f"### 💰 Total Bill: Rs. {total_bill}") paid = st.number_input("Paid Amount", 0.0, float(total_bill))

================= CUSTOMER =================

st.subheader("👤 Customer") customers = pd.read_sql("SELECT * FROM customers", conn)

cust_name = st.selectbox("Select Customer", customers["name"].tolist() if not customers.empty else [])

phone = "" if cust_name: phone = customers[customers.name == cust_name].iloc[0]["phone"]

st.subheader("➕ Add New Customer") new_name = st.text_input("Customer Name") new_phone = st.text_input("Phone Number")

if st.button("Save Customer") and new_name: c.execute("INSERT OR IGNORE INTO customers VALUES (?,?,?)", (new_name, new_phone, 0)) conn.commit() st.success("Customer added")

================= FINALIZE BILL =================

if st.button("✅ Generate Bill"): bill_id = f"BILL-{datetime.now().strftime('%Y%m%d%H%M%S')}" c.execute("INSERT INTO sales(date, customer, total, paid) VALUES (?,?,?,?)", (datetime.now().strftime('%Y-%m-%d'), cust_name, total_bill, paid)) conn.commit()

pdf_bytes = create_pdf(bill_id, cust_name, phone, st.session_state.cart, total_bill, paid)

st.download_button(
    label="📥 Download Bill PDF",
    data=pdf_bytes,
    file_name=f"{bill_id}.pdf",
    mime="application/pdf"
)

st.success("Bill generated successfully")
st.session_state.cart = []

================= REPORTS =================

st.divider() st.subheader("📊 Sales Report") report = pd.read_sql("SELECT * FROM sales", conn) st.dataframe(report)
