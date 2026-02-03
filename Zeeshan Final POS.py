import streamlit as st
import pandas as pd
from fpdf import FPDF

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Zeeshan Mobile POS", layout="wide")

# ---------------- SCREEN WATERMARK ----------------
st.markdown("""
<style>
.watermark {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%) rotate(-35deg);
    font-size: 90px;
    color: #000;
    opacity: 0.04;
    z-index: 0;
    pointer-events: none;
}
</style>
<div class="watermark">ZEESHAN MOBILE ACCESSORIES</div>
""", unsafe_allow_html=True)

# ---------------- SESSION STATE ----------------
if "customer_db" not in st.session_state:
    st.session_state.customer_db = {
        "Walking Customer": {"phone": "-", "balance": 0.0}
    }

if "temp_items" not in st.session_state:
    st.session_state.temp_items = []

if "sales_history" not in st.session_state:
    st.session_state.sales_history = pd.DataFrame(
        columns=["Bill No", "Date", "Customer", "Total", "Paid"]
    )

if "bill_counter" not in st.session_state:
    st.session_state.bill_counter = 1

# ---------------- PDF FUNCTION ----------------
def create_pdf(bill_no, cust_name, phone, items, bill_total, old_bal, paid_amt, only_payment=False):
    pdf = FPDF()
    pdf.add_page()

    # PDF WATERMARK
    pdf.set_font("Arial", "B", 45)
    pdf.set_text_color(230, 230, 230)
    pdf.text(20, 160, "ZEESHAN MOBILE")

    pdf.set_text_color(0, 0, 0)

    # HEADER
    pdf.set_font("Arial", "B", 18)
    pdf.cell(190, 10, "ZEESHAN MOBILE ACCESSORIES", ln=True, align="C")

    pdf.set_font("Arial", "", 12)
    pdf.cell(190, 7, "Contact: 03296971255", ln=True, align="C")
    pdf.ln(5)

    # BILL INFO
    pdf.set_font("Arial", "B", 11)
    pdf.cell(95, 8, f"Bill No: {bill_no}")
    pdf.cell(95, 8, pd.Timestamp.now().strftime("Date: %d-%b-%Y"), ln=True, align="R")

    pdf.cell(95, 8, f"Customer: {cust_name}")
    pdf.cell(95, 8, f"Phone: {phone}", ln=True, align="R")
    pdf.ln(8)

    # ITEMS
    if not only_payment:
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(80, 10, "Item", 1, 0, "L", True)
        pdf.cell(25, 10, "Qty", 1, 0, "C", True)
        pdf.cell(40, 10, "Price", 1, 0, "C", True)
        pdf.cell(45, 10, "Total", 1, 1, "C", True)

        pdf.set_font("Arial", "", 10)
        for i in items:
            pdf.cell(80, 10, i["Item"], 1)
            pdf.cell(25, 10, str(i["Qty"]), 1, 0, "C")
            pdf.cell(40, 10, str(i["Price"]), 1, 0, "C")
            pdf.cell(45, 10, str(i["Total"]), 1, 1, "C")

        pdf.ln(4)

    # SUMMARY
    new_balance = max(0, (bill_total + old_bal) - paid_amt)

    pdf.set_font("Arial", "B", 10)
    if not only_payment:
        pdf.cell(150, 8, "Current Bill:", 0, 0, "R")
        pdf.cell(40, 8, f"Rs. {bill_total}", 1, 1, "C")

    pdf.cell(150, 8, "Previous Balance:", 0, 0, "R")
    pdf.cell(40, 8, f"Rs. {old_bal}", 1, 1, "C")

    pdf.set_fill_color(200, 255, 200)
    pdf.cell(150, 8, "Amount Received:", 0, 0, "R")
    pdf.cell(40, 8, f"Rs. {paid_amt}", 1, 1, "C", True)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(150, 10, "Remaining Balance:", 0, 0, "R")
    pdf.cell(40, 10, f"Rs. {new_balance}", 1, 1, "C")

    return pdf.output(dest="S")

# ---------------- UI ----------------
st.title("🛒 Zeeshan Mobile Accessories POS")

left, right = st.columns([2, 1])

# ---------------- RIGHT PANEL ----------------
with right:
    st.header("👤 Customer")

    customers = sorted(st.session_state.customer_db.keys())
    sel_cust = st.selectbox("Select Customer", customers)

    cust = st.session_state.customer_db[sel_cust]
    st.info(f"Balance: Rs. {cust['balance']}")

    st.divider()
    st.subheader("💸 Quick Payment")

    quick_pay = st.number_input("Received Amount", min_value=0.0)

    if st.button("Confirm Payment"):
        if quick_pay > cust["balance"]:
            st.error("Received amount balance se zyada hai")
        elif quick_pay > 0:
            old = cust["balance"]
            st.session_state.customer_db[sel_cust]["balance"] = max(0, old - quick_pay)

            bill_id = f"PAY-{st.session_state.bill_counter}"
            st.session_state.bill_counter += 1

            st.session_state.sales_history.loc[len(st.session_state.sales_history)] = [
                bill_id, pd.Timestamp.now(), sel_cust, 0, quick_pay
            ]

            pdf = create_pdf(bill_id, sel_cust, cust["phone"], [], 0, old, quick_pay, True)
            st.download_button("Download Receipt", pdf, f"{bill_id}.pdf", "application/pdf")
            st.rerun()

    with st.expander("➕ Add New Customer"):
        n = st.text_input("Name")
        p = st.text_input("Phone")
        if st.button("Save"):
            if n:
                st.session_state.customer_db[n] = {"phone": p, "balance": 0.0}
                st.rerun()

# ---------------- LEFT PANEL ----------------
with left:
    st.header("📦 Billing")

    c1, c2, c3 = st.columns([3, 1, 1])
    name = c1.text_input("Item Name")
    qty = c2.number_input("Qty", min_value=1, value=1)
    price = c3.number_input("Price", min_value=0)

    if st.button("Add Item"):
        if name:
            st.session_state.temp_items.append({
                "Item": name,
                "Qty": qty,
                "Price": price,
                "Total": qty * price
            })

    if st.session_state.temp_items:
        df = pd.DataFrame(st.session_state.temp_items)
        st.table(df)

        total_bill = df["Total"].sum()
        st.metric("Total Bill", f"Rs. {total_bill}")

        paid = st.number_input("Paid Amount", min_value=0.0)

        if st.button("Save & Print Bill"):
            if paid > (total_bill + cust["balance"]):
                st.error("Paid amount zyada hai")
            else:
                old = cust["balance"]
                st.session_state.customer_db[sel_cust]["balance"] = (total_bill + old) - paid

                bill_id = f"ZMA-{st.session_state.bill_counter}"
                st.session_state.bill_counter += 1

                st.session_state.sales_history.loc[len(st.session_state.sales_history)] = [
                    bill_id, pd.Timestamp.now(), sel_cust, total_bill, paid
                ]

                pdf = create_pdf(
                    bill_id, sel_cust, cust["phone"],
                    st.session_state.temp_items, total_bill, old, paid
                )

                st.download_button("Download Bill PDF", pdf, f"{bill_id}.pdf", "application/pdf")
                st.session_state.temp_items = []
                st.success("Bill Saved Successfully")
