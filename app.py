
import streamlit as st
import pandas as pd
import os
from datetime import date
from fpdf import FPDF
import base64
import requests

# Page Config
st.set_page_config(page_title="Wakefit PWA", layout="centered")

def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("style.css")

@st.cache_data
def load_data():
    path = "design-material-mapping_29_1.xlsx"
    if not os.path.exists(path): path = "/content/design-material-mapping_29_1.xlsx"
    if not os.path.exists(path):
        with pd.ExcelWriter(path) as writer:
            pd.DataFrame({'design_code': ['D001'], 'design_name': ['Sample Design'], 'published': ['YES'], 'active': ['YES']}).to_excel(writer, sheet_name=0, index=False)
            pd.DataFrame({'material_crm_code': ['M001'], 'material_name': ['Wall U Trim'], 'price': [100.0]}).to_excel(writer, sheet_name=1, index=False)
            pd.DataFrame({'design_code': ['D001'], 'material_crm_code': ['M001']}).to_excel(writer, sheet_name=2, index=False)
    designs = pd.read_excel(path, sheet_name=0)
    materials = pd.read_excel(path, sheet_name=1)
    mapping = pd.read_excel(path, sheet_name=2)
    def clean_df(df):
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
        return df
    designs = clean_df(designs); materials = clean_df(materials); mapping = clean_df(mapping)
    for df in [designs, mapping, materials]:
        for col in df.columns:
            if 'code' in col: df[col] = df[col].astype(str).str.strip()
    return designs, materials, mapping

try:
    df_design, df_material, df_mapping = load_data()
except Exception as e:
    st.error(f"Error: {e}"); st.stop()

if "cart" not in st.session_state: st.session_state.cart = []
if "page" not in st.session_state: st.session_state.page = "design_select"

def format_sku(sku):
    sku_str = str(sku)
    return f"{sku_str[:-4]}<b style='color: black;'>{sku_str[-4:]}</b>" if len(sku_str) > 4 else f"<b>{sku_str}</b>"

def display_header():
    total_items = sum(item['qty'] for item in st.session_state.cart)
    if st.button(f"🛒 Cart ({total_items})", key="sticky_cart_btn"):
        st.session_state.page = "cart"
        st.rerun()

display_header()

if st.session_state.page == "design_select":
    st.title("Wakefit Selector")
    mode = st.radio("Choose Mode", ["Select a Design", "Select Material"])
    if mode == "Select a Design":
        design_names = df_design["design_name"].unique().tolist()
        sel = st.selectbox("Choose a design", ["-- Select --"] + design_names)
        if sel != "-- Select --":
            row = df_design[df_design["design_name"] == sel]
            st.session_state.selected_design = str(row["design_code"].values[0])
            st.session_state.selected_design_name = sel
            if st.button("Next"): st.session_state.page = "material_listing"; st.rerun()
    else:
        search = st.text_input("Search Material", "")
        filtered = df_material[df_material.apply(lambda x: search.lower() in str(x.get('material_name','')).lower(), axis=1)]
        mat = st.selectbox("Select Result", ["-- Select --"] + filtered.apply(lambda x: f"{x['material_name']} ({x['material_crm_code']})", axis=1).tolist())
        if mat != "-- Select --":
            st.session_state.selected_material_id = mat.split('(')[-1].strip(')')
            st.session_state.selected_design_name = "Single Selection"
            if st.button("Next"): st.session_state.page = "material_listing"; st.rerun()

elif st.session_state.page == "material_listing":
    st.title("Materials")
    if st.button("← Back"): st.session_state.page = "design_select"; st.rerun()
    m_crm_col = "material_crm_code"
    listing = df_material[df_material[m_crm_col].astype(str) == st.session_state.get('selected_material_id', '')] if st.session_state.get('selected_material_id') else df_material[df_material[m_crm_col].astype(str).isin(df_mapping[df_mapping["design_code"] == st.session_state.get('selected_design')]["material_crm_code"].unique().tolist())]
    for i, row in listing.iterrows():
        with st.container():
            st.write(f"**{row['material_name']}** - ₹{row['price']}")
            q = st.number_input("Qty", 1, 100, 1, key=f"q_{i}")
            if st.button("Add", key=f"a_{i}"): 
                st.session_state.cart.append({"name": row['material_name'], "qty": q, "id": row[m_crm_col], "price": float(row['price'])})
                st.toast("Added!")

elif st.session_state.page == "cart":
    st.title("Your Cart")
    c_name = st.text_input("Customer Name"); p_name = st.selectbox("Partner", ["Rajesh", "Nirmal"]); mobile = st.text_input("Mobile"); remarks = st.text_area("Remarks")
    uploaded_file = st.file_uploader("Hand Made Design Image", type=["png", "jpg", "jpeg"])
    grand_total = sum(item['price'] * item['qty'] for item in st.session_state.cart)
    dp = st.number_input("Discount %", 0.0, 100.0, 0.0); disc = (grand_total * dp)/100; final = grand_total - disc + 1000
    st.write(f"Final Total (incl. ₹1000 delivery): ₹{final:,.2f}")
    
    if st.button("Print PDF"):
        pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16)
        try: pdf.image('wakefit logo.png', x=170, y=10, w=25)
        except: pass
        pdf.cell(190, 10, "Wakefit Quotation", 0, 1, "C"); pdf.ln(5); pdf.set_font("Arial", "", 12)
        pdf.cell(190, 10, f"Customer: {c_name}", 0, 1); pdf.cell(190, 10, f"Design: {st.session_state.get('selected_design_name')}", 0, 1)
        pdf.cell(190, 10, f"Date: {date.today().strftime('%d-%m-%Y')}", 0, 1); pdf.ln(5)
        pdf.cell(100, 10, "Product", 1); pdf.cell(20, 10, "Qty", 1); pdf.cell(35, 10, "Price", 1); pdf.cell(35, 10, "Total", 1, 1)
        for item in st.session_state.cart:
            pdf.cell(100, 10, item['name'], 1); pdf.cell(20, 10, str(item['qty']), 1); pdf.cell(35, 10, str(item['price']), 1); pdf.cell(35, 10, str(item['price']*item['qty']), 1, 1)
        pdf.cell(155, 10, "Final Total", 1, 0, "R"); pdf.cell(35, 10, f"{final:,.2f}", 1, 1)
        pdf.ln(5); pdf.set_font("Arial", "B", 10); pdf.cell(190, 10, "Disclaimer:", 0, 1); pdf.set_font("Arial", "", 9)
        for txt in ["1: It is not an invoice, Invoice will be shared after payment.", "2: Valid for 15 days.", "3: WhatsApp +91-9071079479"]: pdf.cell(190, 7, txt, 0, 1)
        if uploaded_file: 
            with open("temp.png", "wb") as f: f.write(uploaded_file.getbuffer())
            pdf.ln(5); pdf.image("temp.png", x=10, w=100)
        b64 = base64.b64encode(pdf.output(dest='S').encode('latin-1')).decode('latin-1')
        st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Quotation.pdf"><button style="width:100%">Download PDF</button></a>', unsafe_allow_html=True)
    if st.button("Back"): st.session_state.page = "design_select"; st.rerun()
