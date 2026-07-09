
import streamlit as st
import pandas as pd
import os
from datetime import date
from fpdf import FPDF
import base64

# Page Config
st.set_page_config(page_title="Wakefit PWA", layout="centered")

# Inject Custom CSS
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("style.css")

# Load Data
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

# Session State
if "cart" not in st.session_state: st.session_state.cart = []
if "page" not in st.session_state: st.session_state.page = "design_select"
if "selected_design" not in st.session_state: st.session_state.selected_design = None
if "selected_design_name" not in st.session_state: st.session_state.selected_design_name = None

# UI Header
total_items = sum(item['qty'] for item in st.session_state.cart)
st.markdown(f'<div class="cart-icon">🛒 {total_items}</div>', unsafe_allow_html=True)

if st.session_state.page == "design_select":
    st.title("Select Design")
    mask_pub = df_design['published'].astype(str).str.strip().str.upper() == 'YES' if 'published' in df_design.columns else True
    mask_act = df_design['active'].astype(str).str.strip().str.upper() == 'YES' if 'active' in df_design.columns else True
    active_designs = df_design[mask_pub & mask_act]
    design_names = active_designs["design_name"].unique().tolist() if "design_name" in active_designs.columns else []
    selected_name = st.selectbox("Choose a design", ["-- Select --"] + design_names)
    if selected_name != "-- Select --":
        design_row = active_designs[active_designs["design_name"] == selected_name]
        st.session_state.selected_design = str(design_row["design_code"].values[0])
        st.session_state.selected_design_name = selected_name
        if st.button("Next"):
            st.session_state.page = "material_listing"
            st.rerun()

elif st.session_state.page == "material_listing":
    st.title("Materials")
    if st.session_state.selected_design_name:
        st.subheader(st.session_state.selected_design_name)

    c_back, c_cart = st.columns([1,1])
    if c_back.button("← Back"): st.session_state.page = "design_select"; st.rerun()
    if c_cart.button("View Cart 🛒", key="view_cart_top"): st.session_state.page = "cart"; st.rerun()

    target_design = st.session_state.selected_design
    m_code_col = "material_code" if "material_code" in df_mapping.columns else "material_crm_code"
    mapped_codes = df_mapping[df_mapping["design_code"] == target_design][m_code_col].unique().tolist()
    m_crm_col = "material_crm_code" if "material_crm_code" in df_material.columns else df_material.columns[0]
    listing = df_material[df_material[m_crm_col].isin(mapped_codes)]

    for i, row in listing.iterrows():
        price = row.get('price', 0)
        m_id = row.get(m_crm_col)
        with st.container():
            st.markdown(f"<div class='card'><b>{row.get('material_name', 'Unknown')}</b><br>Code: {m_id}<br>Price: ₹{price}</div>", unsafe_allow_html=True)
            qty = st.number_input("Qty", min_value=1, value=1, key=f"qty_{i}")
            if st.button("Add to Cart", key=f"add_{i}"):
                found = False
                for item in st.session_state.cart:
                    if item["id"] == m_id: item["qty"] += qty; found = True; break
                if not found:
                    st.session_state.cart.append({"name": row.get('material_name'), "qty": qty, "id": m_id, "price": float(price)})
                st.toast("Added!")

elif st.session_state.page == "cart":
    st.title("Your Cart")
    if st.session_state.selected_design_name:
        st.subheader(st.session_state.selected_design_name)

    customer_name = st.text_input("Customer Name", key="customer_name_input")
    special_remarks = st.text_area("Special Remarks", key="special_remarks_input")

    if not st.session_state.cart:
        st.info("Your cart is empty.")
        if st.button("Back to Design Selection"): st.session_state.page = "design_select"; st.rerun()
    else:
        grand_total = 0
        for i, item in enumerate(st.session_state.cart):
            item_total = item['price'] * item['qty']
            grand_total += item_total
            with st.container():
                col1, col2 = st.columns([2, 1])
                col1.markdown(f"**{item['name']}**<br>₹{item['price']} x {item['qty']} = ₹{item_total}", unsafe_allow_html=True)
                new_qty = col2.number_input("Edit Qty", min_value=0, value=item['qty'], key=f"edit_{i}")
                if new_qty != item['qty']:
                    if new_qty == 0: st.session_state.cart.pop(i)
                    else: st.session_state.cart[i]['qty'] = new_qty
                    st.rerun()

        st.divider()
        st.markdown(f"### Grand Total: ₹{grand_total}")

        uploaded_file = st.file_uploader("Upload Hand Made Design", type=['png', 'jpg', 'jpeg'], key="design_upload")
        col_clr, col_prnt = st.columns(2)
        if col_clr.button("🗑️ Clear Cart", type="primary", use_container_width=True): st.session_state.cart = []; st.rerun()

        if col_prnt.button("🖨️ Print PDF", use_container_width=True):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(190, 10, "Wakefit Quotation", 0, 1, "C")
            pdf.set_font("Arial", "", 12)
            pdf.ln(5)
            pdf.cell(190, 10, f"Customer Name: {customer_name}", 0, 1)
            pdf.cell(190, 10, f"Design: {st.session_state.selected_design_name}", 0, 1)
            curr_date = date.today().strftime('%d-%m-%Y')
            pdf.cell(190, 10, f"Date: {curr_date}", 0, 1)
            pdf.multi_cell(190, 10, f"Remarks: {special_remarks}")
            pdf.ln(5)
            
            # Table Headers
            pdf.set_font("Arial", "B", 12)
            pdf.cell(100, 10, "Product (Code)", 1)
            pdf.cell(20, 10, "Qty", 1, 0, "C")
            pdf.cell(35, 10, "Price", 1, 0, "C")
            pdf.cell(35, 10, "Total", 1, 1, "C")

            pdf.set_font("Arial", "", 10)
            for item in st.session_state.cart:
                x_start = pdf.get_x()
                y_start = pdf.get_y()
                
                # Wrap product name + code
                full_desc = f"{item['name']} ({item['id']})"
                pdf.multi_cell(100, 10, full_desc, 1)
                y_end = pdf.get_y()
                row_height = y_end - y_start
                
                # Move back to fill other columns
                pdf.set_xy(x_start + 100, y_start)
                pdf.cell(20, row_height, str(item['qty']), 1, 0, "C")
                pdf.cell(35, row_height, f"Rs.{item['price']}", 1, 0, "C")
                pdf.cell(35, row_height, f"Rs.{item['price'] * item['qty']}", 1, 1, "C")

            pdf.set_font("Arial", "B", 12)
            pdf.cell(155, 10, "Grand Total", 1, 0, "R")
            pdf.cell(35, 10, f"Rs.{grand_total}", 1, 1, "C")
            
            if uploaded_file:
                temp_path = "temp_design.png"
                with open(temp_path, "wb") as f: f.write(uploaded_file.getbuffer())
                pdf.ln(10); pdf.cell(190, 10, "Hand Made Design:", 0, 1); pdf.image(temp_path, x=10, w=100)
            
            pdf_bytes = pdf.output(dest='S').encode('latin-1')
            b64 = base64.b64encode(pdf_bytes).decode('latin-1')
            
            # Filename formatting
            fn_name = customer_name.replace(" ", "_") if customer_name.strip() else ""
            filename = f"{fn_name}_{curr_date}.pdf" if fn_name else f"{curr_date}.pdf"
            
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}"><button style="width:100%; padding:10px; background-color:#1A237E; color:white; border:none; border-radius:8px;">Click here to Download PDF</button></a>'
            st.markdown(href, unsafe_allow_html=True)

        if st.button("Back"): st.session_state.page = "material_listing"; st.rerun()
