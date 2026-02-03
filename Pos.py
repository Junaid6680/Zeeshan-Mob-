import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, timedelta
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
    
    # Watermark
    pdf.set_font('Arial', 'B', 40)
    pdf.set_text_color(240, 240, 240) 
    with pdf.rotation(45, 105, 148.5):
        pdf.text(20, 155, "ZEESHAN MOBILE ACCESSORIES")
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 24) 
    pdf.cell(0, 15, "ZEESHAN MOBILE ACCESSORIES", ln=True, align="C")
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 5, "Headphones | Chargers | Data Cables | Speakers", ln=True, align="C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Contact: 03296971255", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", "B", 11)
    curr_date = datetime.now().strftime('%d-%m-%Y %H:%M')
    
    pdf.cell(95, 7, f"Customer: {customer}", ln=0) 
    pdf.cell(95, 7, f"Bill No: {bill_id}", ln=1, align="R") 
    
    pdf.set_font("Arial", size=11)
    pdf.cell(95, 7, f"Phone: {phone}", ln=0) 
    pdf.cell(95, 7, f"Date: {curr_date}", ln=1, align="R") 
    pdf.ln(10)

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
    pdf.cell(110, 8, "") 
    pdf.cell(40, 8, "Grand Total:", border=1)
    pdf.cell(40, 8, f"Rs. {total}", border=1, ln=True, align="C")
    pdf.cell(110, 8, "")
    pdf.cell(40, 8, "Amount Paid:", border=1)
    pdf.cell(40, 8, f"Rs. {paid}", border=1, ln=True, align="C")
    pdf.cell(110, 8, "")
    pdf.cell(40, 8, "Balance:", border=1)
    pdf.cell(40, 8, f"Rs. {total - paid}", border=1, ln=True, align="C")
    
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
    selected_cust = st.selectbox("Select Customer", names_list)
    selected_phone = ""
    if selected_cust != "Walk-in":
        selected_phone = cust_data[cust_data.name == selected_cust].iloc[0]["phone"]
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
            res = c.execute("SELECT MAX(id) FROM sales").fetchone()
            next_bill_id = (res[0] + 1) if res[0] else 1
            c.execute("INSERT INTO sales(date, customer, total, paid) VALUES (?,?,?,?)",
                      (datetime.now().strftime('%Y-%m-%d'), selected_cust, total_bill, amt_paid))
            conn.commit()
            pdf_bytes = create_pdf(next_bill_id, selected_cust, selected_phone, st.session_state.cart, total_bill, amt_paid)
            st.download_button(label="📥 Download Receipt (PDF)", data=pdf_bytes, file_name=f"Bill_{next_bill_id}.pdf", mime="application/pdf")
            st.success(f"Saved! Bill No: {next_bill_id}")

# ================= ANALYTICS =================
st.divider()
st.subheader("📊 Sales Analytics Report")
today = datetime.now().strftime('%Y-%m-%d')
this_month = datetime.now().strftime('%Y-%m')
this_year = datetime.now().strftime('%Y')
last_7_days = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

daily_sale = pd.read_sql(f"SELECT SUM(total) as s FROM sales WHERE date = '{today}'", conn).fillna(0).iloc[0]['s']
weekly_sale = pd.read_sql(f"SELECT SUM(total) as s FROM sales WHERE date >= '{last_7_days}'", conn).fillna(0).iloc[0]['s']
monthly_sale = pd.read_sql(f"SELECT SUM(total) as s FROM sales WHERE date LIKE '{this_month}%'", conn).fillna(0).iloc[0]['s']
yearly_sale = pd.read_sql(f"SELECT SUM(total) as s FROM sales WHERE date LIKE '{this_year}%'", conn).fillna(0).iloc[0]['s']

m1, m2, m3, m4 = st.columns(4)
m1.metric("Today", f"Rs. {daily_sale}")
m2.metric("Weekly", f"Rs. {weekly_sale}")
m3.metric("Monthly", f"Rs. {monthly_sale}")
m4.metric("Yearly", f"Rs. {yearly_sale}")

# ================= PAYMENT RECEIVING (NEW) =================
st.divider()
st.subheader("💸 Receive Old Payment")
with st.expander("Record Cash Received from Customer"):
    # Sirf un customers ki list jin ka balance 0 se zyada hai
    bal_cust_query = "SELECT DISTINCT customer FROM sales GROUP BY customer HAVING SUM(total - paid) > 0 AND customer != 'Walk-in'"
    bal_cust_list = pd.read_sql(bal_cust_query, conn)['customer'].tolist()
    
    rcv_col1, rcv_col2 = st.columns(2)
    with rcv_col1:
        pay_cust = st.selectbox("Select Debtor Customer", bal_cust_list)
    with rcv_col2:
        rcv_amount = st.number_input("Amount Received", min_value=0.0, step=100.0)
    
    if st.button("Submit Payment"):
        if pay_cust and rcv_amount > 0:
            # Payment record karne ke liye hum 'sales' table mein 0 total bill wali entry daalte hain sirf 'paid' amount ke saath
            c.execute("INSERT INTO sales(date, customer, total, paid) VALUES (?,?,?,?)",
                      (datetime.now().strftime('%Y-%m-%d'), pay_cust, 0.0, rcv_amount))
            conn.commit()
            st.success(f"Received Rs. {rcv_amount} from {pay_cust}!")
            st.rerun()

# ================= CUSTOMER LEDGER =================
st.subheader("📒 Customer Ledger (Total Dues)")
ledger_query = """
SELECT customer, 
       SUM(total) as Total_Bill, 
       SUM(paid) as Total_Paid, 
       SUM(total - paid) as Remaining_Balance 
FROM sales 
WHERE customer != 'Walk-in'
GROUP BY customer
HAVING Remaining_Balance > 0
"""
ledger_df = pd.read_sql(ledger_query, conn)
st.dataframe(ledger_df, use_container_width=True)

# ================= RECENT HISTORY =================
st.subheader("📜 Recent Sales History")
history = pd.read_sql("SELECT id AS Bill_No, date, customer, total, (total - paid) AS balance FROM sales ORDER BY id DESC", conn)
st.dataframe(history, use_container_width=True)

# ================= BACKUP SECTION =================
st.divider()
st.subheader("💾 System Backup")
col_b1, col_b2, col_b3 = st.columns(3)

with col_b1:
    if not history.empty:
        csv_sales = history.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Sales Backup (CSV)", data=csv_sales, file_name=f"sales_backup.csv", mime='text/csv')

with col_b2:
    if not ledger_df.empty:
        csv_ledger = ledger_df.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Ledger Backup (CSV)", data=csv_ledger, file_name=f"ledger_backup.csv", mime='text/csv')

with col_b3:
    if not cust_data.empty:
        csv_cust = cust_data.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Customer List (CSV)", data=csv_cust, file_name=f"customers_backup.csv", mime='text/csv')
