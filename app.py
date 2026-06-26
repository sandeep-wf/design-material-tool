import streamlit as st
import pandas as pd
import os

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
    path = "design_material_mapping_new.xlsx"
    if not os.path.exists(path):
        path = "/content/design_material_mapping_new.xlsx"

    if not os.path.exists(path):
        st.error(f"File not found: {path}")
        st.stop()

    designs = pd.read_excel(path, sheet_name=0)
    materials = pd.read_excel(path, sheet_name=1)
    mapping = pd.read_excel(path, sheet_name=2)

    # Normalization helper
    def clean_df(df):
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
        return df

    designs = clean_df(designs)
    materials = clean_df(materials)
    mapping = clean_df(mapping)

    # Data Type cleaning
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

# UI Header
st.markdown(f'<div class="cart-icon">🛒 {len(st.session_state.cart)}</div>', unsafe_allow_html=True)

if st.session_state.page == "design_select":
    st.title("Select Design")

    # Filter only Published and Active designs where value is 'Yes'
    mask_pub = df_design['published'].astype(str).str.strip().str.upper() == 'YES' if 'published' in df_design.columns else True
    mask_act = df_design['active'].astype(str).str.strip().str.upper() == 'YES' if 'active' in df_design.columns else True

    active_designs = df_design[mask_pub & mask_act]

    design_names = active_designs["design_name"].unique().tolist() if "design_name" in active_designs.columns else []

    selected_name = st.selectbox("Choose a design", ["-- Select --"] + design_names)
    if selected_name != "-- Select --":
        design_row = active_designs[active_designs["design_name"] == selected_name]
        st.session_state.selected_design = str(design_row["design_code"].values[0])
        if st.button("Next"):
            st.session_state.page = "material_listing"
            st.rerun()

elif st.session_state.page == "material_listing":
    st.title("Materials")
    c_back, c_cart = st.columns([1,1])
    if c_back.button("← Back"): 
        st.session_state.page = "design_select"
        st.rerun()
    if c_cart.button("View Cart 🛒"): 
        st.session_state.page = "cart"
        st.rerun()

    target_design = st.session_state.selected_design

    m_code_col = "material_code" if "material_code" in df_mapping.columns else "material_crm_code" 
    mapped_codes = df_mapping[df_mapping["design_code"] == target_design][m_code_col].unique().tolist()

    m_crm_col = "material_crm_code" if "material_crm_code" in df_material.columns else df_material.columns[0]
    listing = df_material[df_material[m_crm_col].isin(mapped_codes)]

    if listing.empty:
        st.warning("No materials mapped for this design.")
    else:
        for i, row in listing.iterrows():
            with st.container():
                st.markdown(f"<div class='card'><b>{row.get('material_name', 'Unknown')}</b><br>Code: {row.get(m_crm_col)}</div>", unsafe_allow_html=True)
                qty = st.number_input("Qty", min_value=1, value=1, key=f"qty_{i}")
                if st.button("Add to Cart", key=f"add_{i}"):
                    st.session_state.cart.append({"name": row.get('material_name'), "qty": qty, "id": row.get(m_crm_col)})
                    st.toast("Added!")

elif st.session_state.page == "cart":
    st.title("Cart")
    if not st.session_state.cart:
        st.write("Empty")
    else:
        for i, item in enumerate(st.session_state.cart):
            st.write(f"{item['name']} (Qty: {item['qty']})")
    if st.button("Back"): 
        st.session_state.page = "material_listing"
        st.rerun()
