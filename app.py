
import streamlit as st
import pandas as pd
import os
from datetime import date
from fpdf import FPDF
import base64
import requests
import json

# Page Config
st.set_page_config(page_title="Wakefit PWA", layout="centered")

def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("style.css")

@st.cache_data
def load_data():
    path = "design-material-mapping_25_2.xlsx"
    if not os.path.exists(path): path = "/content/design-material-mapping_25_2.xlsx"
    if not os.path.exists(path):
        with pd.ExcelWriter(path) as writer:
            pd.DataFrame({'design_code': ['D001'], 'design_name': ['Sample Design'], 'published': ['YES'], 'active': ['YES']}).to_excel(writer, sheet_name=0, index=False)
            pd.DataFrame({'material_crm_code': ['M001', 'M002'], 'material_name': ['Sample Material 1', 'Sample Material 2'], 'price': [100.0, 150.0]}).to_excel(writer, sheet_name=1, index=False)
            pd.DataFrame({'design_code': ['D001', 'D001'], 'material_crm_code': ['M001', 'M002']}).to_excel(writer, sheet_name=2, index=False)
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
    st.error(f"Error loading Excel: {e}"); st.stop()

if "cart" not in st.session_state: st.session_state.cart = []
if "page" not in st.session_state: st.session_state.page = "design_select"
if "saved_phone" not in st.session_state: st.session_state.saved_phone = ""

@st.dialog("View Catalog")
def view_pdf_dialog(label, file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')

        # Corrected indentation for the template string
        pdf_display = f"""
            <div style="text-align: center;">
                <iframe src="data:application/pdf;base64,{base64_pdf}#toolbar=0&navpanes=0&scrollbar=0" width="100%" height="500" style="border:1px solid #1A237E; border-radius:8px;"></iframe>
                <p style="margin-top: 10px;">PDF not loading? 
                    <a href="data:application/pdf;base64,{base64_pdf}" target="_blank" style="color:#1A237E; font-weight:bold;">Open in New Tab ↗</a>
                </p>
            </div>
        """
        st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.error(f"File {file_path} not found.")

    if st.button("Done", use_container_width=True):
        st.rerun()

@st.dialog("Share via WhatsApp")
def share_whatsapp_dialog(label, file_path):
    phone = st.text_input("Enter Phone Number:", value=st.session_state.saved_phone)
    if st.button("Send WhatsApp"):
        if not phone:
            st.error("Please enter a phone number.")
        else:
            st.session_state.saved_phone = phone
            with st.spinner(f"Sharing {label}..."):
                try:
                    upload_url = "https://media.smsgupshup.com/GatewayAPI/rest"
                    payload = {'method': 'UploadMedia', 'media_type': 'document', 'v': '1.1', 'format': 'json', 'auth_scheme': 'plain', 'userid': '2000264220', 'password': 'IakKOS7Ot'}
                    with open(file_path, 'rb') as f:
                        files = [('media_file', (file_path, f, 'application/pdf'))]
                        r1 = requests.post(upload_url, data=payload, files=files)
                        res1 = r1.json()
                    if res1.get("response", {}).get("status") == "success":
                        media_id = res1["response"]["id"]
                        send_url = "https://mediaapi.smsgupshup.com/GatewayAPI/rest"
                        data = {'method': 'SENDMEDIAMESSAGE', 'send_to': phone, 'msg_type': 'DOCUMENT', 'isHSM': 'true', 'v': '1.1', 'format': 'json', 'auth_scheme': 'plain', 'userid': '2000264220', 'password': 'IakKOS7Ot', 'media_id': media_id, 'filename': f'Wakefit_{label}.pdf', 'whatsAppTemplateId': '2216484149134300', 'var1': 'Customer', 'var2': 'Catalog'}
                        r2 = requests.post(send_url, data=data)
                        if r2.status_code == 200: st.success("Shared successfully!")
                        else: st.error(f"Failed: {r2.text}")
                    else: st.error("Media upload failed.")
                except Exception as e: st.error(f"Error: {e}")

def display_header():
    total_items = sum(item['qty'] for item in st.session_state.cart)
    if st.session_state.page == "cart":
        col1, col2 = st.columns([1, 1])
        if col1.button("ጃ Home", key="top_home_btn"): st.session_state.cart = []; st.session_state.page = "design_select"; st.rerun()
        if col2.button("← Back", key="top_back_btn"): st.session_state.page = "material_listing"; st.rerun()
    elif st.session_state.page == "catalog":
        if st.button("← Back to Home"): st.session_state.page = "design_select"; st.rerun()
    else:
        if st.button(f"ጃ Cart ({total_items})", key="sticky_cart_btn"): st.session_state.page = "cart"; st.rerun()

display_header()

if st.session_state.page == "catalog":
    st.title("Catalog Collection")
    catalogs = {"PVC Catalog": "pvc.pdf", "UV Sheet": "uv.pdf", "Charcoal": "charcoal.pdf", "CPC": "cpc.pdf", "Designs": "design.pdf", "Past Work": "past.pdf"}
    for label, file_path in catalogs.items():
        with st.container():
            col_main, col_down, col_wa = st.columns([3, 1, 1])
            col_main.markdown(f"### {label}")
            if col_main.button(f"View {label}", key=f"view_{label}", use_container_width=True):
                view_pdf_dialog(label, file_path)
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    col_down.download_button("ጥ", data=f, file_name=file_path, mime="application/pdf", key=f"dl_{label}")
            else:
                col_down.button("❌", disabled=True, key=f"missing_{label}")
            if col_wa.button("ጐ", key=f"wa_{label}"): share_whatsapp_dialog(label, file_path)
            st.divider()

elif st.session_state.page == "design_select":
    st.title("Wakefit Selector")
    if st.button("View Catalog ጢ", use_container_width=True): st.session_state.page = "catalog"; st.rerun()
    st.session_state.selection_mode = st.radio("Choose Mode", ["Select a Design", "Select Material", "Manual Entry"], index=1)
    if st.session_state.selection_mode == "Select a Design":
        active_designs = df_design[((df_design["published"].astype(str).str.upper() == "YES") & (df_design["active"].astype(str).str.upper() == "YES"))]
        sel = st.selectbox("Choose a design", ["-- Select --"] + active_designs["design_name"].unique().tolist())
        if sel != "-- Select --":
            row = active_designs[active_designs["design_name"] == sel]
            st.session_state.selected_design = str(row["design_code"].values[0])
            st.session_state.selected_design_name = sel
            if st.button("Next"): st.session_state.page = "material_listing"; st.rerun()
    elif st.session_state.selection_mode == "Select Material":
        q = st.text_input("Search Material")
        filtered = df_material[df_material.apply(lambda x: q.lower() in str(x.get('material_name','')).lower() or q.lower() in str(x.get('material_crm_code','')).lower(), axis=1)]
        mat = st.selectbox("Results", ["-- Select --"] + filtered.apply(lambda x: f"{x['material_name']} ({x['material_crm_code']})", axis=1).tolist())
        if mat != "-- Select --":
            st.session_state.selected_material_id = mat.split('(')[-1].strip(')')
            st.session_state.selected_design_name = "Single Selection"
            if st.button("Next"): st.session_state.page = "material_listing"; st.rerun()
    elif st.session_state.selection_mode == "Manual Entry":
        n = st.text_input("Name"); c = st.text_input("Code"); p = st.number_input("Price", 0.0)
        if st.button("Next") and n and c:
            st.session_state.manual_entry_data = {"name": n, "code": c, "price": p}
            st.session_state.page = "material_listing"; st.rerun()

else:
    st.title("Coming Soon")
    if st.button("Back to Design Selection"): st.session_state.page = "design_select"; st.rerun()
