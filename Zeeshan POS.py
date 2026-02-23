import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime, timedelta
import sqlite3
import json

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Zeeshan Mobile POS", layout="wide", page_icon="📱")

# ── Database ──────────────────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    conn = sqlite3.connect("pos.db", check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

conn = get_connection()
c = conn.cursor()
c.executescript("""
    CREATE TABLE IF NOT EXISTS customers(
        name  TEXT PRIMARY KEY,
        phone TEXT,
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
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id  INTEGER,
        item     TEXT,
        qty      INTEGER,
        price    REAL,
        FOREIGN KEY(sale_id) REFERENCES sales(id)
    );
""")
conn.commit()

# ── Session State ─────────────────────────────────────────────────────────────
if "cart" not in st.session_state:
    st.session_state.cart = []
if "edit_cart" not in st.session_state:
    st.session_state.edit_cart = []

# ── Helpers ───────────────────────────────────────────────────────────────────
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

# ── PDF ───────────────────────────────────────────────────────────────────────
def create_pdf(bill_id, customer, phone, items, total, paid):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.set_font("Arial", "B", 40)
        pdf.set_text_color(240, 240, 240)
        with pdf.rotation(45, 105, 148.5):
            pdf.text(20, 155, "ZEESHAN MOBILE ACCESSORIES")
    except Exception:
        pass

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 22)
    pdf.cell(0, 14, "ZEESHAN MOBILE ACCESSORIES", ln=True, align="C")
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 5, "Headphones | Chargers | Data Cables | Speakers", ln=True, align="C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Contact: 03296971255", ln=True, align="C")
    pdf.ln(8)

    curr_date = datetime.now().strftime("%d-%m-%Y %H:%M")
    pdf.set_font("Arial", "B", 11)
    pdf.cell(95, 7, f"Customer : {customer}")
    pdf.cell(95, 7, f"Bill No  : {bill_id}", ln=True, align="R")
    pdf.set_font("Arial", size=11)
    pdf.cell(95, 7, f"Phone    : {phone}")
    pdf.cell(95, 7, f"Date     : {curr_date}", ln=True, align="R")
    pdf.ln(8)

    pdf.set_fill_color(220, 220, 220)
    pdf.set_font("Arial", "B", 11)
    for label, w, align in [
        ("Item Description", 80, "L"),
        ("Qty",              25, "C"),
        ("Price",            40, "C"),
        ("Total",            45, "C"),
    ]:
        pdf.cell(w, 8, label, border=1, fill=True, align=align)
    pdf.ln()

    pdf.set_font("Arial", size=11)
    for row in items:
        sub = row["qty"] * row["price"]
        pdf.cell(80, 8, str(row["item"]),  border=1)
        pdf.cell(25, 8, str(row["qty"]),   border=1, align="C")
        pdf.cell(40, 8, str(row["price"]), border=1, align="C")
        pdf.cell(45, 8, str(sub),          border=1, align="C", ln=True)

    pdf.ln(4)
    pdf.set_font("Arial", "B", 12)
    for label, value in [
        ("Grand Total :", total),
        ("Amount Paid :", paid),
        ("Balance     :", total - paid),
    ]:
        pdf.cell(110, 8, "")
        pdf.cell(42, 8, label, border=1)
        pdf.cell(38, 8, f"Rs. {value:,.0f}", border=1, align="C", ln=True)

    return bytes(pdf.output(dest="S"))

# ═══════════════════════════════════════════════════════════════════════════════
#  UI
# ═══════════════════════════════════════════════════════════════════════════════
st.title("🛒 Zeeshan Mobile Accessories — POS")

tab_billing, tab_edit, tab_analytics, tab_recovery, tab_backup = st.tabs([
    "🧾 New Bill",
    "✏️ Edit Bill",
    "📊 Analytics",
    "💸 Recovery",
    "💾 Backup"
])

# ════════════════════════════════════════════════════════════
# TAB 1 — NEW BILL
# ════════════════════════════════════════════════════════════
with tab_billing:
    col1, col2 = st.columns([1, 1.3])

    with col1:
        st.subheader("📦 Add Item")
        with st.form("billing_form", clear_on_submit=True):
            it_name  = st.text_input("Item Name")
            it_qty   = st.number_input("Quantity",        min_value=1,   step=1)
            it_price = st.number_input("Price (Per Unit)", min_value=0.0, step=10.0)
            if st.form_submit_button("➕ Add to Cart"):
                if it_name.strip():
                    st.session_state.cart.append(
                        {"item": it_name.strip(), "qty": int(it_qty), "price": float(it_price)}
                    )
                    st.toast(f"✅ Added: {it_name}")
                else:
                    st.warning("Item name likhein.")

    with col2:
        st.subheader("🧾 Cart")
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            df_cart["Subtotal"] = df_cart["qty"] * df_cart["price"]
            st.dataframe(df_cart, use_container_width=True, hide_index=True)
            total_bill = float(df_cart["Subtotal"].sum())
            st.markdown(f"### 🧮 Total: **Rs. {total_bill:,.0f}**")

            del_idx = st.selectbox(
                "Item hatayen (row number)",
                options=range(len(st.session_state.cart)),
                format_func=lambda i: f"{i+1}. {st.session_state.cart[i]['item']}"
            )
            col_del, col_clr = st.columns(2)
            if col_del.button("🗑️ Remove Selected"):
                st.session_state.cart.pop(del_idx)
                st.rerun()
            if col_clr.button("❌ Clear All"):
                st.session_state.cart = []
                st.rerun()
        else:
            st.info("Cart khali hai.")
            total_bill = 0.0

    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("👤 Customer")
        cust_data     = pd.read_sql("SELECT * FROM customers ORDER BY name", conn)
        names_list    = ["Walk-in"] + cust_data["name"].tolist()
        selected_cust = st.selectbox("Customer Chunein", names_list)
        selected_phone = ""
        if selected_cust != "Walk-in" and not cust_data.empty:
            row = cust_data[cust_data.name == selected_cust]
            if not row.empty:
                selected_phone = row.iloc[0]["phone"]

        with st.expander("➕ Naya Customer Register"):
            n_name  = st.text_input("Pura Naam")
            n_phone = st.text_input("Phone Number")
            if st.button("💾 Save Customer"):
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
        st.subheader("💰 Payment")
        amt_paid  = st.number_input("Paid Amount (Rs.)", min_value=0.0,
                                    value=float(total_bill), step=10.0)
        remaining = total_bill - amt_paid
        if remaining > 0:
            st.error(f"⚠️ Baqi: Rs. {remaining:,.0f}")
        elif remaining < 0:
            st.warning(f"💸 Wapas karen: Rs. {abs(remaining):,.0f}")
        else:
            st.success("✅ Pura payment ho gaya")

        if st.button("✅ Bill Banao & Save Karo", use_container_width=True):
            if not st.session_state.cart:
                st.error("Cart khali hai — pehle items add karein.")
            else:
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
                    label=f"📥 Receipt Download — Bill #{new_bill_id}",
                    data=pdf_bytes,
                    file_name=f"Bill_{new_bill_id}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.success(f"Bill #{new_bill_id} save ho gaya!")
                st.session_state.cart = []
                st.rerun()

# ════════════════════════════════════════════════════════════
# TAB 2 — EDIT BILL
# ════════════════════════════════════════════════════════════
with tab_edit:
    st.subheader("✏️ Purana Bill Edit Karein")
    st.info("Bill number chunein, items edit karein, phir save karein. Naya PDF bhi download kar saktay hain.")

    history_df = get_history()

    if history_df.empty:
        st.warning("Abhi koi bill nahi hai.")
    else:
        bill_options = {
            f"Bill #{row['Bill_No']} — {row['customer']} — {row['date']} — Rs.{row['total']:,.0f}": row['Bill_No']
            for _, row in history_df.iterrows()
        }
        selected_label   = st.selectbox("Bill Chunein", list(bill_options.keys()))
        selected_bill_id = bill_options[selected_label]

        bill_row = history_df[history_df["Bill_No"] == selected_bill_id].iloc[0]

        ecol1, ecol2, ecol3 = st.columns(3)
        ecol1.metric("Customer", bill_row["customer"])
        ecol2.metric("Total",    f"Rs. {bill_row['total']:,.0f}")
        ecol3.metric("Paid",     f"Rs. {bill_row['paid']:,.0f}")

        st.divider()

        if st.button("📂 Is Bill ke Items Load Karo", key=f"load_{selected_bill_id}"):
            fetched = get_bill_items(selected_bill_id)
            if fetched:
                st.session_state.edit_cart = fetched
            else:
                st.session_state.edit_cart = []
                st.warning("Is bill ke items record mein nahi hain (purana bill). Naye items manually add karein.")

        if st.session_state.edit_cart:
            st.markdown("### 📝 Items Edit Karein")
            st.caption("Har row mein item ka naam, qty aur price change kar saktay hain.")

            hcols = st.columns([3, 1.2, 1.5, 0.7])
            hcols[0].caption("Item Naam")
            hcols[1].caption("Qty")
            hcols[2].caption("Price (Rs.)")
            hcols[3].caption("Hatao")

            updated_items = []
            for idx, item in enumerate(st.session_state.edit_cart):
                cols = st.columns([3, 1.2, 1.5, 0.7])
                new_name  = cols[0].text_input("Item",  value=item["item"],        key=f"e_name_{idx}",  label_visibility="collapsed", placeholder="Item naam")
                new_qty   = cols[1].number_input("Qty", value=item["qty"],         key=f"e_qty_{idx}",   min_value=1, step=1, label_visibility="collapsed")
                new_price = cols[2].number_input("Price", value=float(item["price"]), key=f"e_price_{idx}", min_value=0.0, step=10.0, label_visibility="collapsed")
                remove    = cols[3].checkbox("❌", key=f"e_del_{idx}", help="Yeh item hatao")

                if not remove:
                    updated_items.append({
                        "item":  new_name.strip() if new_name.strip() else item["item"],
                        "qty":   int(new_qty),
                        "price": float(new_price)
                    })

            st.divider()
            st.markdown("#### ➕ Naya Item Is Bill Mein Jodein")
            with st.form("add_to_edit_bill", clear_on_submit=True):
                na_cols = st.columns([3, 1.5, 2, 1.5])
                new_it_name  = na_cols[0].text_input("Item Naam", placeholder="e.g. Data Cable")
                new_it_qty   = na_cols[1].number_input("Qty",   min_value=1,   step=1,    value=1)
                new_it_price = na_cols[2].number_input("Price", min_value=0.0, step=10.0, value=0.0)
                if na_cols[3].form_submit_button("➕ Add"):
                    if new_it_name.strip():
                        st.session_state.edit_cart.append({
                            "item":  new_it_name.strip(),
                            "qty":   int(new_it_qty),
                            "price": float(new_it_price)
                        })
                        st.rerun()
                    else:
                        st.warning("Item ka naam likhein.")

            st.divider()
            new_total = sum(i["qty"] * i["price"] for i in updated_items)
            st.markdown(f"### 🧮 Naya Total: **Rs. {new_total:,.0f}**")

            ep1, ep2 = st.columns(2)
            new_paid      = ep1.number_input("Naya Paid Amount (Rs.)", min_value=0.0, value=float(bill_row["paid"]), step=10.0)
            new_remaining = new_total - new_paid
            if new_remaining > 0:
                ep2.error(f"⚠️ Baqi: Rs. {new_remaining:,.0f}")
            elif new_remaining < 0:
                ep2.warning(f"💸 Wapas: Rs. {abs(new_remaining):,.0f}")
            else:
                ep2.success("✅ Pura paid")

            sv1, sv2 = st.columns(2)
            if sv1.button("💾 Bill Save Karo (Update)", use_container_width=True):
                if not updated_items:
                    st.error("Kam az kam ek item hona chahiye.")
                else:
                    c.execute("UPDATE sales SET total=?, paid=? WHERE id=?",
                              (new_total, new_paid, selected_bill_id))
                    conn.commit()
                    save_sale_items(selected_bill_id, updated_items)
                    st.success(f"✅ Bill #{selected_bill_id} update ho gaya!")
                    st.session_state.edit_cart = []
                    st.rerun()

            if sv2.button("📥 Updated PDF Banao", use_container_width=True):
                if not updated_items:
                    st.error("Kam az kam ek item hona chahiye.")
                else:
                    cust_df    = pd.read_sql("SELECT * FROM customers", conn)
                    edit_phone = ""
                    cust_name  = bill_row["customer"]
                    if cust_name != "Walk-in" and not cust_df.empty:
                        r = cust_df[cust_df.name == cust_name]
                        if not r.empty:
                            edit_phone = r.iloc[0]["phone"]

                    pdf_bytes = create_pdf(
                        selected_bill_id, cust_name, edit_phone,
                        updated_items, new_total, new_paid
                    )
                    st.download_button(
                        label=f"📄 Download Bill #{selected_bill_id} PDF",
                        data=pdf_bytes,
                        file_name=f"Bill_{selected_bill_id}_edited.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
        else:
            st.info("Upar 'Items Load Karo' button dabayein.")

        st.divider()
        st.subheader("📜 Tamam Bills")
        search = st.text_input("🔍 Customer name se dhundhein", placeholder="e.g. Ahmed")
        disp   = history_df.copy()
        if search:
            disp = disp[disp["customer"].str.contains(search, case=False, na=False)]
        st.dataframe(disp, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════
# TAB 3 — ANALYTICS
# ════════════════════════════════════════════════════════════
with tab_analytics:
    st.subheader("📊 Sales Analytics")

    today       = datetime.now().strftime("%Y-%m-%d")
    this_month  = datetime.now().strftime("%Y-%m")
    this_year   = datetime.now().strftime("%Y")
    last_7_days = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    def safe_sum(query, params=()):
        row = pd.read_sql(query, conn, params=params).iloc[0, 0]
        return float(row) if row else 0.0

    daily   = safe_sum("SELECT SUM(total) FROM sales WHERE date = ?",    (today,))
    weekly  = safe_sum("SELECT SUM(total) FROM sales WHERE date >= ?",   (last_7_days,))
    monthly = safe_sum("SELECT SUM(total) FROM sales WHERE date LIKE ?", (f"{this_month}%",))
    yearly  = safe_sum("SELECT SUM(total) FROM sales WHERE date LIKE ?", (f"{this_year}%",))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📅 Aaj",      f"Rs. {daily:,.0f}")
    m2.metric("📆 Hafta",    f"Rs. {weekly:,.0f}")
    m3.metric("🗓️ Mahina",  f"Rs. {monthly:,.0f}")
    m4.metric("📈 Saal",     f"Rs. {yearly:,.0f}")

    st.divider()
    st.subheader("📒 Customer Ledger (Baqi Dues)")
    ledger_df = get_ledger()
    dues = ledger_df[ledger_df["Remaining_Balance"] > 0] if not ledger_df.empty else ledger_df
    st.dataframe(dues, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════
# TAB 4 — RECOVERY
# ════════════════════════════════════════════════════════════
with tab_recovery:
    st.subheader("💸 Purana Udhaar Wapsi (Recovery)")
    ledger_df2       = get_ledger()
    debtor_customers = (
        ledger_df2[ledger_df2["Remaining_Balance"] > 0]["customer"].tolist()
        if not ledger_df2.empty else []
    )

    if debtor_customers:
        pay_cust    = st.selectbox("Customer Chunein", debtor_customers)
        current_bal = float(
            ledger_df2[ledger_df2["customer"] == pay_cust]["Remaining_Balance"].values[0]
        )
        st.info(f"**{pay_cust}** ka baqi balance: Rs. {current_bal:,.0f}")
        rcv_amount = st.number_input(
            "Received Amount (Rs.)", min_value=0.0,
            max_value=current_bal, step=10.0
        )
        if st.button("✅ Recovery Submit"):
            if rcv_amount > 0:
                c.execute(
                    "INSERT INTO sales(date, customer, total, paid) VALUES (?,?,?,?)",
                    (datetime.now().strftime("%Y-%m-%d"), pay_cust, 0.0, rcv_amount)
                )
                conn.commit()
                st.success(f"Rs. {rcv_amount:,.0f} {pay_cust} se recover ho gaya!")
                st.rerun()
            else:
                st.warning("Amount zero nahi honi chahiye.")
    else:
        st.success("🎉 Koi baqi balance nahi hai!")

# ════════════════════════════════════════════════════════════
# TAB 5 — BACKUP
# ════════════════════════════════════════════════════════════
with tab_backup:
    st.subheader("💾 Data Backup")
    full_history = get_history()
    ledger_full  = get_ledger()
    cust_data_b  = pd.read_sql("SELECT * FROM customers ORDER BY name", conn)

    b1, b2, b3 = st.columns(3)
    with b1:
        if not full_history.empty:
            st.download_button(
                "📥 Sales CSV", full_history.to_csv(index=False).encode(),
                "sales_backup.csv", "text/csv", use_container_width=True
            )
    with b2:
        if not ledger_full.empty:
            st.download_button(
                "📥 Ledger CSV", ledger_full.to_csv(index=False).encode(),
                "ledger_backup.csv", "text/csv", use_container_width=True
            )
    with b3:
        if not cust_data_b.empty:
            st.download_button(
                "📥 Customers CSV", cust_data_b.to_csv(index=False).encode(),
                "customers_backup.csv", "text/csv", use_container_width=True
            )
