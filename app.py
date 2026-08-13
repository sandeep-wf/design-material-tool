
import streamlit as st
import pandas as pd
import os
from datetime import date
from fpdf import FPDF
import base64
import requests

st.set_page_config(page_title="Wakefit PWA", layout="centered")

def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

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
if "selection_mode" not in st.session_state: st.session_state.selection_mode = "Select a Design"

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
    st.session_state.selection_mode = st.radio("Choose Mode", ["Select a Design", "Select Material"], index=0)

    if st.session_state.selection_mode == "Select a Design":
        design_names = df_design["design_name"].unique().tolist()
        selected_name = st.selectbox("Choose a design", ["-- Select --"] + design_names)
        if selected_name != "-- Select --":
            design_row = df_design[df_design["design_name"] == selected_name]
            st.session_state.selected_design = str(design_row["design_code"].values[0])
            st.session_state.selected_design_name = selected_name
            st.session_state.selected_material_id = None
            if st.button("Next"): st.session_state.page = "material_listing"; st.rerun()
    else:
        m_crm_col = "material_crm_code" if "material_crm_code" in df_material.columns else df_material.columns[0]
        search_query = st.text_input("Search Material (e.g. S168)", "")
        filtered_df = df_material[df_material.apply(lambda x: search_query.lower() in str(x.get('material_name', '')).lower() or search_query.lower() in str(x.get(m_crm_col, '')).lower(), axis=1)] if search_query.strip() else df_material
        mat_display = filtered_df.apply(lambda x: f"{x.get('material_name', 'Unknown')} ({x.get(m_crm_col)})", axis=1).tolist()
        selected_mat_str = st.selectbox("Select from results", ["-- Select --"] + mat_display)
        if selected_mat_str != "-- Select --":
            st.session_state.selected_material_id = selected_mat_str.split('(')[-1].strip(')')
            st.session_state.selected_design = None
            st.session_state.selected_design_name = "Search Selection"
            if st.button("Next"): st.session_state.page = "material_listing"; st.rerun()

elif st.session_state.page == "material_listing":
    st.title("Materials")
    if st.button("← Back"): st.session_state.page = "design_select"; st.rerun()

    m_crm_col = "material_crm_code" if "material_crm_code" in df_material.columns else df_material.columns[0]
    if st.session_state.selected_material_id:
        listing = df_material[df_material[m_crm_col].astype(str) == st.session_state.selected_material_id]
    else:
        target_design = st.session_state.selected_design
        m_code_col = "material_code" if "material_code" in df_mapping.columns else "material_crm_code"
        mapped_codes = df_mapping[df_mapping["design_code"] == target_design][m_code_col].unique().tolist()
        listing = df_material[df_material[m_crm_col].astype(str).isin([str(x) for x in mapped_codes])]

    for i, row in listing.iterrows():
        m_name = str(row.get("material_name", "Unknown"))
        price = row.get("price", 0)
        m_id = row.get(m_crm_col)
        with st.container():
            st.markdown(f"<div class='card material-card'><b>{m_name}</b><br>Code: {format_sku(m_id)}<br>Price: ₹{price}</div>", unsafe_allow_html=True)

            is_u_trim = "wall u trim" in m_name.lower()
            is_t_trim = "wall t trim" in m_name.lower()
            is_bidding = "wall bidding" in m_name.lower()
            sel_attr1, sel_attr2 = "", ""

            if is_u_trim or is_t_trim:
                c_attr1, c_attr2 = st.columns(2)
                sel_attr1 = c_attr1.selectbox("Color", ["Gold", "Black", "Rose gold"], key=f"col_{i}")
                sizes = ["10mm", "12mm", "15mm", "20mm"] if is_u_trim else ["6mm", "12mm", "18mm"]
                sel_attr2 = c_attr2.selectbox("Size", sizes, key=f"sz_{i}")
            elif is_bidding:
                c_attr1, c_attr2 = st.columns(2)
                sel_attr1 = c_attr1.selectbox("Material", ["WPC", "PVC"], key=f"mat_{i}")
                sel_attr2 = c_attr2.selectbox("Number", [f"{x:02d}" for x in range(1, 16)], key=f"num_{i}")

            qty = st.number_input("Qty", 1, 100, 1, key=f"q_{i}")
            if st.button("Add to Cart", key=f"a_{i}"):
                final_name = f"{m_name} {sel_attr1} {sel_attr2}" if (is_u_trim or is_t_trim or is_bidding) else m_name
                st.session_state.cart.append({"name": final_name, "qty": qty, "id": m_id, "price": float(price)})
                st.toast("Added!")

elif st.session_state.page == "cart":
    st.title("Your Cart")
    customer_name = st.text_input("Customer Name", key="cn")
    customer_mobile = st.text_input("Customer Mobile (with 91)", key="cm")

    if not st.session_state.cart:
        st.info("Cart is empty.")
        if st.button("Back"): st.session_state.page = "design_select"; st.rerun()
    else:
        grand_total = sum(item["price"] * item["qty"] for item in st.session_state.cart)
        for item in st.session_state.cart:
            st.markdown(f"**{item['name']}** - ₹{item['price']} x {item['qty']} = ₹{item['price']*item['qty']:,.2f}")
        st.divider()
        delivery_charge = 1000
        final_total = grand_total + delivery_charge
        st.markdown(f"### Total (Incl. delivery): ₹{final_total:,.2f}")

        if st.button("Share on WhatsApp", use_container_width=True):
            if not customer_mobile:
                st.warning("Enter mobile number.")
            else:
                url = "https://mediaapi.smsgupshup.com/GatewayAPI/rest"
                payload = {
                    "method": "SENDMEDIAMESSAGE", "send_to": str(customer_mobile), "msg_type": "DOCUMENT", "isHSM": "true",
                    "v": "1.1", "format": "json", "auth_scheme": "plain", "userid": "2000264220", "password": "IakKOS7Ot",
                    "media_url": "https://drive.google.com/uc?export=download&id=1oWHdKZtKkvFfC47z4Tj5PlOksRsvhyB6",
                    "filename": "Wakefit Quotation.pdf", "whatsAppTemplateId": "2216484149134300",
                    "var1": str(customer_name), "var2": str(round(final_total, 2))
                }
                res = requests.post(url, data=payload)
                if res.status_code == 200: st.success("Shared!")
                else: st.error("Failed.")

        if st.button("Home"): st.session_state.cart = []; st.session_state.page = "design_select"; st.rerun()
