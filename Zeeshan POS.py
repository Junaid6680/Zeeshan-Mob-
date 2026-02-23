import streamlit as st
import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from datetime import datetime, timedelta
import sqlite3

# \u2500\u2500 Page Config \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
st.set_page_config(page_title="Zeeshan Mobile POS", layout="wide", page_icon="\ud83d\udcf1")

# \u2500\u2500 Database \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
@st.cache_resource
def get_connection():
    conn = sqlite3.connect("pos.db", check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

conn = get_connection()
c = conn.cursor()
c.executescript("""
    CREATE TABLE IF NOT EXISTS customers(
        name    TEXT PRIMARY KEY,
        phone   TEXT,
        balance REAL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS sales(
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        date     TEXT,
        customer TEXT,
        total    REAL,
        paid     REAL
    );
    CREATE TABLE IF NOT EXISTS sale_items(
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER,
        item    TEXT,
        qty     INTEGER,
        price   REAL,
        FOREIGN KEY(sale_id) REFERENCES sales(id)
    );
""")
conn.commit()

# \u2500\u2500 Session State \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
if "cart" not in st.session_state:
    st.session_state.cart = []
if "edit_cart" not in st.session_state:
    st.session_state.edit_cart = []

# \u2500\u2500 DB Helpers \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
def get_ledger():
    return pd.read_sql("""
        SELECT customer,
               SUM(total)        AS Total_Bill,
               SUM(paid)         AS Total_Paid,
               SUM(total - paid) AS Remaining_Balance
        FROM   sales
        WHERE  customer != 'Walk-in'
        GROUP  BY customer
    """, conn)

def get_history():
    return pd.read_sql("""
        SELECT id AS Bill_No, date, customer,
               total, paid, (total - paid) AS Balance
        FROM   sales ORDER BY id DESC
    """, conn)

def get_bill_items(sale_id):
    rows = c.execute(
        "SELECT id, item, qty, price FROM sale_items WHERE sale_id=?", (sale_id,)
    ).fetchall()
    return [{"row_id": r[0], "item": r[1], "qty": r[2], "price": r[3]} for r in rows]

def save_sale_items(sale_id, items):
    c.execute("DELETE FROM sale_items WHERE sale_id=?", (sale_id,))
    for i in items:
        c.execute(
            "INSERT INTO sale_items(sale_id, item, qty, price) VALUES (?,?,?,?)",
            (sale_id, i["item"], i["qty"], i["price"])
        )
    conn.commit()

# \u2500\u2500 PDF \u2014 fpdf2 syntax (new_x / new_y) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
def create_pdf(bill_id, customer, phone, items, total, paid):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # \u2500\u2500 Header \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "ZEESHAN MOBILE ACCESSORIES",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, "Headphones | Chargers | Data Cables | Speakers",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Contact: 03296971255",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y() + 3, 200, pdf.get_y() + 3)
    pdf.ln(8)

    # \u2500\u2500 Bill Info \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    curr_date = datetime.now().strftime("%d-%m-%Y %H:%M")
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(95, 7, f"Customer : {customer}")
    pdf.cell(95, 7, f"Bill No  : {bill_id}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 7, f"Phone    : {phone}")
    pdf.cell(95, 7, f"Date     : {curr_date}",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
    pdf.ln(5)

    # \u2500\u2500 Table Header \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    col_w = [85, 25, 40, 40]
    pdf.set_fill_color(40, 40, 40)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(col_w[0], 9, "Item Description", border=1, fill=True, align="C")
    pdf.cell(col_w[1], 9, "Qty",              border=1, fill=True, align="C")
    pdf.cell(col_w[2], 9, "Unit Price",       border=1, fill=True, align="C")
    pdf.cell(col_w[3], 9, "Amount",           border=1, fill=True, align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # \u2500\u2500 Table Rows \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    fill = False
    for row in items:
        subtotal = row["qty"] * row["price"]
        bg = (245, 245, 245) if fill else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.cell(col_w[0], 8, str(row["item"]),           border=1, fill=True)
        pdf.cell(col_w[1], 8, str(row["qty"]),            border=1, fill=True, align="C")
        pdf.cell(col_w[2], 8, f"Rs.{row['price']:,.0f}",  border=1, fill=True, align="R")
        pdf.cell(col_w[3], 8, f"Rs.{subtotal:,.0f}",      border=1, fill=True, align="R",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        fill = not fill

    pdf.ln(5)

    # \u2500\u2500 Totals \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    balance = total - paid
    pdf.set_font("Helvetica", "B", 10)

    rows_summary = [
        ("Grand Total :", total,   False),
        ("Paid        :", paid,    False),
        ("Balance     :", balance, balance > 0),
    ]
    for label, value, is_red in rows_summary:
        if is_red:
            pdf.set_fill_color(190, 30, 30)
            pdf.set_text_color(255, 255, 255)
        else:
            pdf.set_fill_color(220, 220, 220)
            pdf.set_text_color(0, 0, 0)
        pdf.cell(150, 8, "")
        pdf.cell(28, 8, label,              border=1, fill=True, align="L")
        pdf.cell(12, 8, f"Rs.{value:,.0f}", border=1, fill=True, align="R",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_text_color(0, 0, 0)

    # \u2500\u2500 Footer \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    pdf.ln(10)
    pdf.set_draw_color(180, 180, 180)
    pdf.set_line_width(0.3)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, "Thank you for shopping with us!",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.cell(0, 6, "Zeeshan Mobile Accessories  |  03296971255",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

    # \u2500\u2500 Return bytes (fpdf2 style) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    return bytes(pdf.output())


# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  MAIN UI
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
st.title("\ud83d\uded2 Zeeshan Mobile Accessories \u2014 POS")

tab_billing, tab_edit, tab_analytics, tab_recovery, tab_backup = st.tabs([
    "\ud83e\uddfe New Bill",
    "\u270f\ufe0f Edit Bill",
    "\ud83d\udcca Analytics",
    "\ud83d\udcb8 Recovery",
    "\ud83d\udcbe Backup",
])

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# TAB 1 \u2014 NEW BILL
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
with tab_billing:
    col1, col2 = st.columns([1, 1.3])

    with col1:
        st.subheader("\ud83d\udce6 Add Item")
        with st.form("billing_form", clear_on_submit=True):
            it_name  = st.text_input("Item Name")
            it_qty   = st.number_input("Quantity",         min_value=1,   step=1)
            it_price = st.number_input("Price (Per Unit)", min_value=0.0, step=10.0)
            if st.form_submit_button("\u2795 Add to Cart"):
                if it_name.strip():
                    st.session_state.cart.append(
                        {"item": it_name.strip(), "qty": int(it_qty), "price": float(it_price)}
                    )
                    st.toast(f"\u2705 Added: {it_name}")
                else:
                    st.warning("Item name likhein.")

    with col2:
        st.subheader("\ud83e\uddfe Cart")
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            df_cart["Subtotal"] = df_cart["qty"] * df_cart["price"]
            st.dataframe(df_cart, use_container_width=True, hide_index=True)
            total_bill = float(df_cart["Subtotal"].sum())
            st.markdown(f"### \ud83e\uddee Total: **Rs. {total_bill:,.0f}**")

            del_idx = st.selectbox(
                "Item hatayen",
                options=range(len(st.session_state.cart)),
                format_func=lambda i: f"{i+1}. {st.session_state.cart[i]['item']}"
            )
            col_del, col_clr = st.columns(2)
            if col_del.button("\ud83d\uddd1\ufe0f Remove Selected"):
                st.session_state.cart.pop(del_idx)
                st.rerun()
            if col_clr.button("\u274c Clear All"):
                st.session_state.cart = []
                st.rerun()
        else:
            st.info("Cart khali hai.")
            total_bill = 0.0

    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("\ud83d\udc64 Customer")
        cust_data      = pd.read_sql("SELECT * FROM customers ORDER BY name", conn)
        names_list     = ["Walk-in"] + cust_data["name"].tolist()
        selected_cust  = st.selectbox("Customer Chunein", names_list)
        selected_phone = ""
        if selected_cust != "Walk-in" and not cust_data.empty:
            row = cust_data[cust_data.name == selected_cust]
            if not row.empty:
                selected_phone = row.iloc[0]["phone"]

        with st.expander("\u2795 Naya Customer Register"):
            n_name  = st.text_input("Pura Naam")
            n_phone = st.text_input("Phone Number")
            if st.button("\ud83d\udcbe Save Customer"):
                if n_name.strip():
                    try:
                        c.execute("INSERT INTO customers VALUES (?,?,?)",
                                  (n_name.strip(), n_phone.strip(), 0.0))
                        conn.commit()
                        st.success(f"'{n_name}' add ho gaya!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Yeh naam pehle se mojood hai.")
                else:
                    st.warning("Naam khali nahi ho sakta.")

    with c2:
        st.subheader("\ud83d\udcb0 Payment")
        amt_paid  = st.number_input("Paid Amount (Rs.)", min_value=0.0,
                                    value=float(total_bill), step=10.0)
        remaining = total_bill - amt_paid
        if remaining > 0:
            st.error(f"\u26a0\ufe0f Baqi: Rs. {remaining:,.0f}")
        elif remaining < 0:
            st.warning(f"\ud83d\udcb8 Wapas karen: Rs. {abs(remaining):,.0f}")
        else:
            st.success("\u2705 Pura payment ho gaya")

        if st.button("\u2705 Bill Banao & Save Karo", use_container_width=True):
            if not st.session_state.cart:
                st.error("Cart khali hai \u2014 pehle items add karein.")
            else:
                try:
                    c.execute(
                        "INSERT INTO sales(date, customer, total, paid) VALUES (?,?,?,?)",
                        (datetime.now().strftime("%Y-%m-%d"), selected_cust, total_bill, amt_paid)
                    )
                    conn.commit()
                    new_bill_id = c.lastrowid
                    save_sale_items(new_bill_id, st.session_state.cart)

                    pdf_bytes = create_pdf(
                        new_bill_id, selected_cust, selected_phone,
                        st.session_state.cart, total_bill, amt_paid
                    )
                    st.download_button(
                        label=f"\ud83d\udce5 Receipt Download \u2014 Bill #{new_bill_id}",
                        data=pdf_bytes,
                        file_name=f"Bill_{new_bill_id}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
                    st.success(f"\u2705 Bill #{new_bill_id} save ho gaya!")
                    st.session_state.cart = []
                    st.rerun()
                except Exception as e:
                    st.error(f"\u274c PDF Error: {e}")

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# TAB 2 \u2014 EDIT BILL
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
with tab_edit:
    st.subheader("\u270f\ufe0f Purana Bill Edit Karein")
    st.info("Bill chunein \u2192 Items load karein \u2192 Edit karein \u2192 Save karein")

    history_df = get_history()

    if history_df.empty:
        st.warning("Abhi koi bill nahi hai.")
    else:
        bill_options = {
            f"Bill #{row['Bill_No']} \u2014 {row['customer']} \u2014 {row['date']} \u2014 Rs.{row['total']:,.0f}": row['Bill_No']
            for _, row in history_df.iterrows()
        }
        selected_label   = st.selectbox("Bill Chunein", list(bill_options.keys()))
        selected_bill_id = bill_options[selected_label]
        bill_row         = history_df[history_df["Bill_No"] == selected_bill_id].iloc[0]

        ecol1, ecol2, ecol3 = st.columns(3)
        ecol1.metric("Customer", bill_row["customer"])
        ecol2.metric("Total",    f"Rs. {bill_row['total']:,.0f}")
        ecol3.metric("Paid",     f"Rs. {bill_row['paid']:,.0f}")

        st.divider()

        if st.button("\ud83d\udcc2 Is Bill ke Items Load Karo"):
            fetched = get_bill_items(selected_bill_id)
            if fetched:
                st.session_state.edit_cart = fetched
            else:
                st.session_state.edit_cart = []
