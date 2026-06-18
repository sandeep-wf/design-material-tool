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
    designs = pd.read_excel(path, sheet_name=0)
    materials = pd.read_excel(path, sheet_name=1)
    mapping = pd.read_excel(path, sheet_name=2)
    
    # Normalize columns
    designs.columns = [str(c).strip().lower() for c in designs.columns]
    materials.columns = [str(c).strip().lower() for c in materials.columns]
    mapping.columns = [str(c).strip().lower() for c in mapping.columns]
    
    # Normalize booleans
    for col in ['published', 'active']:
        if col in designs.columns:
            designs[col] = designs[col].astype(str).str.strip().str.upper().map({'TRUE': True, '1': True, '1.0': True, 'YES': True, 'FALSE': False, '0': False, '0.0': False, 'NO': False}).fillna(False)

    # Normalize ID columns to stripped strings to fix mapping issues
    if 'design_code' in designs.columns: designs['design_code'] = designs['design_code'].astype(str).str.strip()
    if 'design_code' in mapping.columns: mapping['design_code'] = mapping['design_code'].astype(str).str.strip()
    if 'material_code' in mapping.columns: mapping['material_code'] = mapping['material_code'].astype(str).str.strip()
    if 'material_sap_code' in materials.columns: materials['material_sap_code'] = materials['material_sap_code'].astype(str).str.strip()

    return designs, materials, mapping

df_design, df_material, df_mapping = load_data()

# Session State
if 'cart' not in st.session_state: st.session_state.cart = []
if 'page' not in st.session_state: st.session_state.page = "design_select"
if 'selected_design' not in st.session_state: st.session_state.selected_design = None

# UI Header
st.markdown(f'<div class="cart-icon">🛒 {len(st.session_state.cart)}</div>', unsafe_allow_html=True)

# --- PAGE 1: Design Select ---
if st.session_state.page == "design_select":
    st.title("Design Select")
    active_designs = df_design[(df_design['published'] == True) & (df_design['active'] == True)]
    design_names = active_designs['design_name'].unique().tolist()
    
    selected_name = st.selectbox("Select Design", ["-- Select --"] + design_names)
    if selected_name != "-- Select --":
        code = active_designs[active_designs['design_name'] == selected_name]['design_code'].values[0]
        st.session_state.selected_design = str(code)
        if st.button("Next"):
            st.session_state.page = "material_listing"
            st.rerun()

# --- PAGE 2: Material Listing ---
elif st.session_state.page == "material_listing":
    st.title("Materials")
    if st.button("Back"):
        st.session_state.page = "design_select"
        st.rerun()

    target_design = st.session_state.selected_design
    # Filter mapping then materials
    mapped_codes = df_mapping[df_mapping['design_code'] == target_design]['material_code'].unique().tolist()
    listing = df_material[df_material['material_sap_code'].isin(mapped_codes)]

    if listing.empty:
        st.info("No materials mapped to this design.")
    
    for _, row in listing.iterrows():
        with st.expander(f"{row['material_name']} - ₹{row['price']}"):
            qty = st.number_input("Quantity", min_value=1, value=1, key=f"q_{row['material_sap_code']}")
            if st.button("Add to Cart", key=f"a_{row['material_sap_code']}"):
                st.session_state.cart.append({'name': row['material_name'], 'price': row['price'], 'qty': qty, 'id': row['material_sap_code']})
                st.rerun()

# --- PAGE 3: Cart ---
elif st.session_state.page == "cart":
    st.title("Cart")
    if not st.session_state.cart:
        st.write("Cart is empty")
        if st.button("Back to Selection"): 
            st.session_state.page = "design_select"
            st.rerun()
    else:
        total = 0
        for i, item in enumerate(st.session_state.cart):
            st.write(f"**{item['name']}** - ₹{item['price']} x {item['qty']}")
            total += item['price'] * item['qty']
            if st.button("Remove", key=f"r_{i}"): 
                st.session_state.cart.pop(i)
                st.rerun()
        st.subheader(f"Total: ₹{total}")
        if st.button("Clear Cart"): 
            st.session_state.cart = []
            st.rerun()
