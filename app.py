import streamlit as st
import pandas as pd
import os
from datetime import date

# Page Config
st.set_page_config(page_title="Wakefit PWA", layout="centered")

def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("style.css")

@st.cache_data
def load_data():
    path = "design_material_mapping_06.xlsx"
    designs = pd.read_excel(path, sheet_name=0)
    materials = pd.read_excel(path, sheet_name=1)
    mapping = pd.read_excel(path, sheet_name=2)
    def clean_df(df):
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
        return df
    return clean_df(designs), clean_df(materials), clean_df(mapping)

try:
    df_design, df_material, df_mapping = load_data()
except Exception as e:
    st.error("Please ensure data is loaded.")
    st.stop()

if "cart" not in st.session_state: st.session_state.cart = []
if "page" not in st.session_state: st.session_state.page = "design_select"
if "selected_design_name" not in st.session_state: st.session_state.selected_design_name = "None"

total_items = sum(item['qty'] for item in st.session_state.cart)
st.markdown(f'<div class="cart-icon no-print">🛒 {total_items}</div>', unsafe_allow_html=True)

if st.session_state.page == "design_select":
    st.title("Select Design")
    design_names = df_design["design_name"].unique().tolist()
    selected_name = st.selectbox("Choose a design", ["-- Select --"] + design_names)
    if selected_name != "-- Select --":
        design_row = df_design[df_design["design_name" ] == selected_name]
        st.session_state.selected_design = str(design_row["design_code"].values[0])
        st.session_state.selected_design_name = selected_name
        if st.button("Next"):
            st.session_state.page = "material_listing"
            st.rerun()

elif st.session_state.page == "material_listing":
    st.title("Materials")
    c1, c2 = st.columns(2)
    if c1.button("← Back"): st.session_state.page = "design_select"; st.rerun()
    if c2.button("View Cart 🛒"): st.session_state.page = "cart"; st.rerun()
    
    target = st.session_state.selected_design
    m_codes = df_mapping[df_mapping["design_code"].astype(str) == target]["material_code"].unique().tolist()
    listing = df_material[df_material["material_crm_code"].astype(str).isin([str(x) for x in m_codes])]

    for i, row in listing.iterrows():
        with st.container():
            st.markdown(f"<div class='card'><b>{row['material_name']}</b><br>Price: ₹{row['price']}</div>", unsafe_allow_html=True)
            qty = st.number_input("Qty", 1, 100, 1, key=f"q_{i}")
            if st.button("Add to Cart", key=f"a_{i}"):
                found = False
                for item in st.session_state.cart:
                    if item["id"] == row['material_crm_code']:
                        item["qty"] += qty
                        found = True
                        break
                if not found:
                    st.session_state.cart.append({"name": row['material_name'], "qty": qty, "id": row['material_crm_code'], "price": float(row['price'])})
                st.toast("Added!")

elif st.session_state.page == "cart":
    c_title, c_print = st.columns([3, 1])
    c_title.markdown("<h1 class='no-print'>Your Cart</h1>", unsafe_allow_html=True)
    
    if not st.session_state.cart:
        st.info("Empty cart.")
        if st.button("Back"): st.session_state.page = "design_select"; st.rerun()
    else:
        # Simple Trigger: Customer name enables print
        cust_name = st.text_input("Customer Name", placeholder="Please enter customer name")
        if cust_name:
            if c_print.button("🖨️ Print"):
                st.markdown('<script>window.print();</script>', unsafe_allow_html=True)

        # Simple quotation header for print output
        st.markdown(f"""
        <div class='print-only'>
            <h2 style='text-align:center;'>Quotation</h2>
            <p><b>Customer:</b> {cust_name}<br><b>Design:</b> {st.session_state.selected_design_name}<br><b>Date:</b> {date.today()}</p>
        </div>
        """, unsafe_allow_html=True)

        grand_total = 0
        table_html = "<table style='width:100%; border-collapse: collapse; margin-top:10px;' border='1'><tr><th>Product</th><th>Qty</th><th>Price</th><th>Total</th></tr>"

        for i, item in enumerate(st.session_state.cart):
            item_total = item['price'] * item['qty']
            grand_total += item_total
            table_html += f"<tr><td style='padding:5px;'>{item['name']}</td><td style='text-align:center;'>{item['qty']}</td><td>₹{item['price']}</td><td>₹{item_total}</td></tr>"
            # Interactive screen layout
            st.markdown(f"<div class='no-print'><b>{item['name']}</b> (₹{item['price']} x {item['qty']} = ₹{item_total})</div>", unsafe_allow_html=True)

        table_html += f"<tr><td colspan='3' style='text-align:right;'><b>Grand Total</b></td><td><b>₹{grand_total}</b></td></tr></table>"
        
        st.markdown(f"<div class='print-only'>{table_html}</div>", unsafe_allow_html=True)
        st.markdown(f"<h3 class='no-print'>Grand Total: ₹{grand_total}</h3>", unsafe_allow_html=True)

        if st.button("🗑️ Clear Cart", key="clr"): st.session_state.cart = []; st.rerun()
        if st.button("← Back to Materials", key="bm"): st.session_state.page = "material_listing"; st.rerun()
