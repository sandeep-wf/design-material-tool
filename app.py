import streamlit as st
import pandas as pd
from PIL import Image
import base64

# Page Config
st.set_page_config(page_title="Wakefit PWA", layout="wide")

# Inject Custom CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

try:
    local_css("style.css")
except:
    pass

# Load Data
@st.cache_data
def load_data():
    path = "design_material_mapping_new.xlsx"
    designs = pd.read_excel(path, sheet_name=0)
    materials = pd.read_excel(path, sheet_name=1)
    mapping = pd.read_excel(path, sheet_name=2)
    return designs, materials, mapping

df_design, df_material, df_mapping = load_data()

# State Management
if 'cart' not in st.session_state: st.session_state.cart = []
if 'page' not in st.session_state: st.session_state.page = "design_select"
if 'selected_design' not in st.session_state: st.session_state.selected_design = None

# Header with Cart Icon
col_logo, col_empty, col_cart = st.columns([1, 4, 1])
with col_logo:
    st.markdown("**WAKEFIT**") # Placeholder for logo
with col_cart:
    if st.button(f"🛒 ({len(st.session_state.cart)})"):
        st.session_state.page = "cart"
        st.rerun()

# --- PAGE 1: Design Select ---
if st.session_state.page == "design_select":
    st.title("Select Design")
    active_designs = df_design[(df_design['published'] == True) & (df_design['active'] == True)]
    design_list = active_designs['design_name'].tolist()
    
    selected = st.selectbox("Choose a design", ["Select..."] + design_list)
    if selected != "Select...":
        st.session_state.selected_design = active_designs[active_designs['design_name'] == selected]['design_code'].values[0]
        if st.button("Next"):
            st.session_state.page = "material_listing"
            st.rerun()

# --- PAGE 2: Material Listing ---
elif st.session_state.page == "material_listing":
    st.title("Material Selection")
    if st.button("← Back to Designs"):
        st.session_state.page = "design_select"
        st.rerun()

    d_code = st.session_state.selected_design
    mapped_materials = df_mapping[df_mapping['design_code'] == d_code]['material_code'].tolist()
    display_df = df_material[df_material['material_sap_code'].isin(mapped_materials)]

    for _, row in display_df.iterrows():
        with st.container():
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.write(f"**{row['material_name']}**")
            c1.write(f"Price: ₹{row['price']}")
            qty = c2.number_input("Qty", min_value=1, value=1, key=f"qty_{row['material_sap_code']}")
            if c3.button("Add to Cart", key=f"btn_{row['material_sap_code']}"):
                st.session_state.cart.append({
                    'id': row['material_sap_code'],
                    'name': row['material_name'],
                    'price': row['price'],
                    'qty': qty
                })
                st.toast(f"Added {row['material_name']}!")
                st.rerun()

# --- PAGE 3: Cart ---
elif st.session_state.page == "cart":
    st.title("Your Cart")
    if not st.session_state.cart:
        st.warning("Cart is empty")
        if st.button("Go to Design Select"):
            st.session_state.page = "design_select"
            st.rerun()
    else:
        total = 0
        for i, item in enumerate(st.session_state.cart):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            c1.write(item['name'])
            c2.write(f"₹{item['price']}")
            new_qty = c3.number_input("Qty", min_value=1, value=item['qty'], key=f"cart_qty_{i}")
            st.session_state.cart[i]['qty'] = new_qty
            subtotal = item['price'] * new_qty
            total += subtotal
            if c4.button("🗑️", key=f"del_{i}"):
                st.session_state.cart.pop(i)
                st.rerun()
        
        st.divider()
        st.subheader(f"Total: ₹{total}")
        
        if st.button("Take Screenshot / Save PDF"):
             st.write("Please use your browser's Print/Save as PDF or mobile screenshot feature for the complete view.")

        if st.button("Clear Cart"):
            st.session_state.cart = []
            st.rerun()
