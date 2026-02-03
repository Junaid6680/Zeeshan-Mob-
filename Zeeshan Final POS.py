import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import sqlite3

# Page Configuration
st.set_page_config(page_title="Zeeshan Mobile POS", layout="wide")

# ================= DATABASE SETUP =================
def get_connection():
    conn = sqlite3.connect("pos.db", check_same_thread=False)
    return conn

conn = get_connection()
c = conn.cursor()

# Tables banana
c.execute("CREATE TABLE IF NOT EXISTS customers(name TEXT PRIMARY KEY, phone TEXT, balance REAL)")
c.execute("CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, customer TEXT, total REAL, paid REAL)")
conn.commit()

# ================= SESSION STATE (Cart handle karne ke liye) =================
if "cart" not in st.session_state:
    st.session_state.cart = []

# ================= PDF GENERATION FUNCTION =================
def create_pdf(bill_id, customer, phone, items, total, paid):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "ZEESHAN MOBILE ACCESSORIES", ln=True, align="C")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, "Hall Road Lahore | Contact: 03296971255", ln=True, align="C")
    pdf.ln(10)

    # Bill Info
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, f"Bill ID: {bill_id}", ln=True)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 6, f"Customer: {customer}", ln=True)
    pdf.cell(0, 6, f"Phone: {phone}", ln=True)
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%d-%m-%Y %H:%M')}", ln=True)
    pdf.ln(5)

    # Table Header
    pdf.set_fill_color(200, 200, 200)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(80, 8, "Item Description", border=1, fill=True)
    pdf.cell(30, 8, "Qty", border=1, fill=True)
    pdf.cell(40, 8, "Price", border=1, fill=True)
    pdf.cell(40, 8, "Total", border=1, fill=True, ln=True)

    # Items
    pdf.set_font("Helvetica", size=11)
    for i in items:
        pdf.cell(80, 8, str(i["item"]), border=1)
        pdf.cell(30, 8, str(i["qty"]), border=1)
        pdf.cell(40, 8, str(i["price"]), border=1)
        pdf.cell(40, 8, str(i["qty"] * i["price"]), border=1, ln=True)

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Grand Total: Rs. {total}", ln=True, align="R")
    pdf.cell(0, 8, f"Amount Paid: Rs. {paid}", ln=True, align="R")
    pdf.cell(0, 8, f"Balance: Rs. {total - paid}", ln=True, align="R")
    
    return pdf.output(dest="S").encode("latin-1")

# ================= UI LAYOUT =================
st.title("🛒 Zeeshan Mobile Accessories POS")

col1, col2 = st.columns([1, 1])

# --- LEFT COLUMN: Billing ---
with col1:
    st.subheader("📦 Add to Cart")
    with st.form("item_form", clear_on_submit=True):
        item_name = st.text_input("Item Name")
        item_qty = st.number_input("Quantity", min_value=1, value=1)
        item_price = st.number_input("Price", min_value=0, value=0)
        add_btn = st.form_submit_button("➕ Add Item")
        
        if add_btn and item_name:
            st.session_state.cart.append({"item": item_name, "qty": item_qty, "price": item_price})
            st.toast(f"{item_name} added!")

# --- RIGHT COLUMN: Cart View ---
with col2:
    st.subheader("🧾 Current Bill")
    if st.session_state.cart:
        df_cart = pd.DataFrame(st.session_state.cart)
        df_cart["Total"] = df_cart["qty"] * df_cart["price"]
        st.table(df_cart)
        total_bill = df_cart["Total"].sum()
        
        if st.button("🗑️ Clear Cart"):
            st.session_state.cart = []
            st.rerun()
    else:
        st.info("Cart is empty")
        total_bill = 0

st.divider()

# ================= CUSTOMER & FINALIZING =================
c1, c2 = st.columns(2)

with c1:
    st.subheader("👤 Customer Selection")
    customers_df = pd.read_sql("SELECT * FROM customers", conn)
    cust_list = ["Walk-in"] + customers_df["name"].tolist()
    selected_cust = st.selectbox("Select Customer", cust_list)
    
    # New Customer Addition
    with st.expander("➕ Add New Customer"):
        new_name = st.text_input("Name")
        new_phone = st.text_input("Phone")
        if st.button("Save New Customer"):
            if new_name:
                try:
                    c.execute("INSERT INTO customers VALUES (?,?,?)", (new_name, new_phone, 0.0))
                    conn.commit()
                    st.success("Customer Saved!")
                    st.rerun()
                except:
                    st.error("Customer already exists!")

with c2:
    st.subheader("💰 Payment")
    st.write(f"### Total: Rs. {total_bill}")
    paid_amount = st.number_input("Paid Amount", min_value=0.0, max_value=float(total_bill + 1000000), value=float(total_bill))
    
    if st.button("✅ Confirm & Generate Bill"):
        if not st.session_state.cart:
            st.error("Cart khali hai!")
        else:
            bill_id = f"BILL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Save to Database
            c.execute("INSERT INTO sales(date, customer, total, paid) VALUES (?,?,?,?)",
                      (datetime.now().strftime('%Y-%m-%d'), selected_cust, total_bill, paid_amount))
            conn.commit()
            
            # Get Phone for PDF
            cust_phone = ""
            if selected_cust != "Walk-in":
                cust_phone = customers_df[customers_df.name == selected_cust].iloc[0]["phone"]
            
            # Create PDF
            pdf_data = create_pdf(bill_id, selected_cust, cust_phone, st.session_state.cart, total_bill, paid_amount)
            
            st.download_button(
                label="📥 Download Bill PDF",
                data=pdf_data,
                file_name=f"{bill_id}.pdf",
                mime="application/pdf"
            )
            st.success("Bill Generated Successfully!")
            st.session_state.cart = [] # Clear cart after sale

# ================= REPORTS =================
st.divider()
st.subheader("📊 Sales History")
sales_df = pd.read_sql("SELECT * FROM sales ORDER BY id DESC", conn)
st.dataframe(sales_df, use_container_width=True)
