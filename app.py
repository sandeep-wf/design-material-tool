
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

def display_header():
    total_items = sum(item['qty'] for item in st.session_state.cart)
    if st.session_state.page == "cart":
        col1, col2 = st.columns([1, 1])
        if col1.button("🏠 Home", key="top_home_btn"): st.session_state.cart = []; st.session_state.page = "design_select"; st.rerun()
        if col2.button("← Back", key="top_back_btn"): st.session_state.page = "material_listing"; st.rerun()
    elif st.session_state.page == "catalog":
        if st.button("← Back to Home"): st.session_state.page = "design_select"; st.rerun()
    else:
        if st.button(f"🛒 Cart ({total_items})", key="sticky_cart_btn"): st.session_state.page = "cart"; st.rerun()

display_header()

if st.session_state.page == "catalog":
    st.title("Catalog Collection")
    catalogs = {"PVC Catalog": "pvc.pdf", "UV Sheet": "uv.pdf", "Charcoal": "charcoal.pdf", "CPC": "cpc.pdf", "3D Panels": "3d.pdf", "Designs": "design.pdf", "Past Work": "past.pdf"}
    for label, file_path in catalogs.items():
        with st.container():
            col_label, col_down = st.columns([3, 1])
            col_label.markdown(f"### {label}")
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    col_down.download_button("Download", data=f, file_name=file_path, mime="application/pdf", key=f"dl_{label}", use_container_width=True)
            else:
                col_down.button("File Missing", disabled=True, key=f"missing_{label}", use_container_width=True)
            st.divider()

elif st.session_state.page == "design_select":
    st.title("Wakefit Selector")
    if st.button("View Catalogs", use_container_width=True): st.session_state.page = "catalog"; st.rerun()
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
