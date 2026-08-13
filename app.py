
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
            pd.DataFrame({'material_crm_code': ['M001'], 'material_name': ['Sample Material'], 'price': [100.0]}).to_excel(writer, sheet_name=1, index=False)
            pd.DataFrame({'design_code': ['D001'], 'material_crm_code': ['M001']}).to_excel(writer, sheet_name=2, index=False)
    
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
    design_names = df_design["design_name"].unique().tolist()
    selected_name = st.selectbox("Choose a design", ["-- Select --"] + design_names)
    if selected_name != "-- Select --":
        design_row = df_design[df_design["design_name"] == selected_name]
        st.session_state.selected_design = str(design_row["design_code"].values[0])
        st.session_state.selected_design_name = selected_name
        if st.button("Next"): st.session_state.page = "material_listing"; st.rerun()

elif st.session_state.page == "material_listing":
    st.title("Materials")
    if st.button("← Back"): st.session_state.page = "design_select"; st.rerun()
    
    m_code_col = "material_code" if "material_code" in df_mapping.columns else "material_crm_code"
    target_design = st.session_state.selected_design
    mapped_codes = df_mapping[df_mapping["design_code"] == target_design][m_code_col].unique().tolist()
    m_crm_col = "material_crm_code" if "material_crm_code" in df_material.columns else df_material.columns[0]
    listing = df_material[df_material[m_crm_col].astype(str).isin([str(x) for x in mapped_codes])]

    for i, row in listing.iterrows():
        m_name = row.get("material_name", "Unknown")
        price = row.get("price", 0)
        m_id = row.get(m_crm_col)
        with st.container():
            st.markdown(f"<div class='card material-card'><b>{m_name}</b><br>Code: {format_sku(m_id)}<br>Price: ₹{price}</div>", unsafe_allow_html=True)
            qty = st.number_input("Qty", 1, 100, 1, key=f"q_{i}")
            if st.button("Add to Cart", key=f"a_{i}"):
                st.session_state.cart.append({"name": m_name, "qty": qty, "id": m_id, "price": float(price)})
                st.toast("Added!")

elif st.session_state.page == "cart":
    st.title("Your Cart")
    customer_name = st.text_input("Customer Name", key="cn")
    customer_mobile = st.text_input("Customer Mobile (with 91)", key="cm")
    partner_name = st.selectbox("Partner", ["Rajesh", "Nirmal"], key="pn")
    
    if not st.session_state.cart:
        st.info("Cart is empty.")
        if st.button("Back"): st.session_state.page = "design_select"; st.rerun()
    else:
        grand_total = 0
        for i, item in enumerate(st.session_state.cart):
            item_total = item["price"] * item["qty"]
            grand_total += item_total
            st.markdown(f"**{item['name']}** - ₹{item['price']} x {item['qty']} = ₹{item_total:,.2f}")
        
        st.divider()
        delivery_charge = 1000
        final_total = grand_total + delivery_charge
        st.markdown(f"### Total (Incl. ₹{delivery_charge} delivery): ₹{final_total:,.2f}")

        if st.button("🖨️ Print PDF", use_container_width=True):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(190, 10, "Wakefit Quotation", 0, 1, "C")
            pdf.set_font("Arial", "", 12)
            pdf.ln(5)
            pdf.cell(190, 10, f"Customer: {customer_name}", 0, 1)
            pdf.cell(190, 10, f"Total: Rs.{final_total:,.2f}", 0, 1)
            b64 = base64.b64encode(pdf.output(dest='S').encode('latin-1')).decode('latin-1')
            st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="Quotation.pdf"><button style="width:100%; padding:10px; background-color:#1A237E; color:white; border:none; border-radius:8px;">Download PDF</button></a>', unsafe_allow_html=True)

        if st.button("Share on WhatsApp", use_container_width=True):
            if not customer_mobile:
                st.warning("Enter mobile number.")
            else:
                url = "https://mediaapi.smsgupshup.com/GatewayAPI/rest"
                payload = {
                    "method": "SENDMEDIAMESSAGE",
                    "send_to": str(customer_mobile),
                    "msg_type": "DOCUMENT",
                    "isHSM": "true",
                    "v": "1.1",
                    "format": "json",
                    "auth_scheme": "plain",
                    "userid": "2000264220",
                    "password": "IakKOS7Ot",
                    "media_url": "https://drive.google.com/uc?export=download&id=1oWHdKZtKkvFfC47z4Tj5PlOksRsvhyB6",
                    "filename": "Wakefit Wall Makeover Quotation.pdf",
                    "whatsAppTemplateId": "2216484149134300",
                    "var1": str(customer_name),
                    "var2": str(round(final_total, 2))
                }
                res = requests.post(url, data=payload)
                if res.status_code == 200: st.success("Shared!")
                else: st.error("Failed to share.")

        if st.button("Home"): st.session_state.page = "design_select"; st.rerun()
