
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
    if not os.path.exists(path):
        path = "/content/design_material_mapping_06.xlsx"

    if not os.path.exists(path):
        st.error(f"File not found: {path}")
        st.stop()

    designs = pd.read_excel(path, sheet_name=0)
    materials = pd.read_excel(path, sheet_name=1)
    mapping = pd.read_excel(path, sheet_name=2)

    def clean_df(df):
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
        return df

    designs = clean_df(designs)
    materials = clean_df(materials)
    mapping = clean_df(mapping)

    for df in [designs, mapping, materials]:
        for col in df.columns:
            if 'code' in col:
                df[col] = df[col].astype(str).str.strip()

    return designs, materials, mapping

try:
    df_design, df_material, df_mapping = load_data()
except Exception as e:
    st.error(f"Error loading Excel: {e}")
    st.stop()

if "cart" not in st.session_state: st.session_state.cart = []
if "page" not in st.session_state: st.session_state.page = "design_select"
if "selected_design" not in st.session_state: st.session_state.selected_design = None
if "selected_design_name" not in st.session_state: st.session_state.selected_design_name = ""

total_items = sum(item['qty'] for item in st.session_state.cart)
st.markdown(f'<div class="cart-icon no-print">🛒 {total_items}</div>', unsafe_allow_html=True)

if st.session_state.page == "design_select":
    st.title("Select Design")
    design_names = df_design["design_name"].unique().tolist() if "design_name" in df_design.columns else []
    selected_name = st.selectbox("Choose a design", ["-- Select --"] + design_names)
    if selected_name != "-- Select --":
        design_row = df_design[df_design["design_name"] == selected_name]
        st.session_state.selected_design = str(design_row["design_code"].values[0])
        st.session_state.selected_design_name = selected_name
        if st.button("Next"):
            st.session_state.page = "material_listing"
            st.rerun()

elif st.session_state.page == "material_listing":
    st.title("Materials")
    st.subheader(st.session_state.selected_design_name)
    c1, c2 = st.columns(2)
    if c1.button("← Back"): st.session_state.page = "design_select"; st.rerun()
    if c2.button("View Cart 🛒"): st.session_state.page = "cart"; st.rerun()

    target_design = st.session_state.selected_design
    m_code_col = "material_code" if "material_code" in df_mapping.columns else "material_crm_code"
    mapped_codes = df_mapping[df_mapping["design_code"] == target_design][m_code_col].unique().tolist()
    m_crm_col = "material_crm_code" if "material_crm_code" in df_material.columns else df_material.columns[0]
    listing = df_material[df_material[m_crm_col].isin(mapped_codes)]

    for i, row in listing.iterrows():
        price = row.get('price', 0)
        with st.container():
            st.markdown(f"<div class='card'><b>{row.get('material_name', 'Unknown')}</b><br>Price: ₹{price}</div>", unsafe_allow_html=True)
            qty = st.number_input("Qty", 1, 100, 1, key=f"q_{i}")
            if st.button("Add to Cart", key=f"a_{i}"):
                item_id = row.get(m_crm_col)
                found = False
                for item in st.session_state.cart:
                    if item["id"] == item_id:
                        item["qty"] += qty
                        found = True
                        break
                if not found:
                    st.session_state.cart.append({"name": row.get('material_name'), "qty": qty, "id": item_id, "price": float(price)})
                st.toast("Added!")

elif st.session_state.page == "cart":
    c_title, c_print = st.columns([3, 1])
    c_title.markdown("<h1 class='no-print'>Your Cart</h1>", unsafe_allow_html=True)

    if not st.session_state.cart:
        st.info("Your cart is empty.")
        if st.button("Back"): st.session_state.page = "design_select"; st.rerun()
    else:
        cust_name = st.text_input("Customer Name", placeholder="Enter customer name", key="cust_name_input")
        
        if cust_name:
             if c_print.button("🖨️ Print"):
                st.markdown('<script>window.print();</script>', unsafe_allow_html=True)

        # Hidden in UI, visible in Print
        st.markdown(f"""
        <div class='print-only'>
            <h2 style='text-align:center;'>Quotation</h2>
            <hr>
            <p style='font-size: 1.1em;'>
                <b>Customer Name:</b> {cust_name}<br>
                <b>Design Name:</b> {st.session_state.selected_design_name}<br>
                <b>Date:</b> {date.today().strftime('%d-%m-%Y')}
            </p>
        </div>
        """, unsafe_allow_html=True)

        grand_total = 0
        t_html = "<table style='width:100%; border-collapse: collapse; margin-top:10px;' border='1'>"
        t_html += "<tr style='background-color:#f2f2f2;'><th>Product Name</th><th>Qty</th><th>Price</th><th>Total</th></tr>"

        for i, item in enumerate(st.session_state.cart):
            item_total = item['price'] * item['qty']
            grand_total += item_total
            t_html += f"<tr><td style='padding:8px;'>{item['name']}</td><td style='padding:8px; text-align:center;'>{item['qty']}</td><td style='padding:8px;'>₹{item['price']}</td><td style='padding:8px;'>₹{item_total}</td></tr>"
            st.markdown(f"<div class='no-print'><b>{item['name']}</b> (₹{item['price']} x {item['qty']} = ₹{item_total})</div>", unsafe_allow_html=True)

        t_html += f"<tr style='background-color:#f2f2f2;'><td colspan='3' style='text-align:right; padding:8px;'><b>Grand Total</b></td><td style='padding:8px;'><b>₹{grand_total}</b></td></tr></table>"

        st.markdown(f"<div class='print-only'>{t_html}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='no-print'><hr><h3>Total: ₹{grand_total}</h3></div>", unsafe_allow_html=True)

        if st.button("🗑️ Clear Cart", key="clr"): st.session_state.cart = []; st.rerun()
        if st.button("Back to Materials", key="bm"): st.session_state.page = "material_listing"; st.rerun()
