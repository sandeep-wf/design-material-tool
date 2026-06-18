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

    designs.columns = [str(c).strip().lower() for c in designs.columns]
    materials.columns = [str(c).strip().lower() for c in materials.columns]
    mapping.columns = [str(c).strip().lower() for c in mapping.columns]

    for col in ["published", "active"]:
        if col in designs.columns:
            designs[col] = designs[col].astype(str).str.strip().str.upper().map({"TRUE": True, "1": True, "1.0": True, "YES": True, "FALSE": False, "0": False, "0.0": False, "NO": False}).fillna(False)

    if "design_code" in designs.columns: designs["design_code"] = designs["design_code"].astype(str).str.strip()
    if "design_code" in mapping.columns: mapping["design_code"] = mapping["design_code"].astype(str).str.strip()
    if "material_code" in mapping.columns: mapping["material_code"] = mapping["material_code"].astype(str).str.strip()
    if "material_crm_code" in materials.columns: materials["material_crm_code"] = materials["material_crm_code"].astype(str).str.strip()

    return designs, materials, mapping

df_design, df_material, df_mapping = load_data()

if "cart" not in st.session_state: st.session_state.cart = []
if "page" not in st.session_state: st.session_state.page = "design_select"
if "selected_design" not in st.session_state: st.session_state.selected_design = None

st.markdown(f'<div class="cart-icon">🛒 {len(st.session_state.cart)}</div>', unsafe_allow_html=True)

if st.session_state.page == "design_select":
    st.title("Select Design")
    active_designs = df_design[(df_design["published"] == True) & (df_design["active"] == True)]
    design_names = active_designs["design_name"].unique().tolist()

    selected_name = st.selectbox("Choose a design", ["-- Select --"] + design_names)
    if selected_name != "-- Select --":
        design_row = active_designs[active_designs["design_name"] == selected_name]
        st.session_state.selected_design = str(design_row["design_code"].values[0])
        if st.button("Next"):
            st.session_state.page = "material_listing"
            st.rerun()

elif st.session_state.page == "material_listing":
    st.title("Materials")
    col_back, col_cart_btn = st.columns([2, 1])
    if col_back.button("← Back"):
        st.session_state.page = "design_select"
        st.rerun()
    if col_cart_btn.button("Cart 🛒"):
        st.session_state.page = "cart"
        st.rerun()

    target_design = st.session_state.selected_design
    mapped_codes = df_mapping[df_mapping["design_code"] == target_design]["material_code"].unique().tolist()
    listing = df_material[df_material["material_crm_code"].isin(mapped_codes)]

    if listing.empty:
        st.warning("No materials found.")
    else:
        # Header Row
        h1, h2, h3 = st.columns([3, 2, 2])
        h1.write("**Item**")
        h2.write("**Qty**")
        h2.write(" ")
        
        st.divider()

        for i, row in listing.reset_index().iterrows():
            c1, c2, c3 = st.columns([3, 2, 2])
            c1.write(f"**{row['material_name']}**")
            c1.caption(f"₹{row['price']} | {row['material_crm_code']}")
            
            # Fixed Duplicate Key by using index i
            qty = c2.number_input("Qty", min_value=1, value=1, key=f"q_list_{i}_{row['material_crm_code']}", label_visibility="collapsed")
            
            if c3.button("Add", key=f"btn_list_{i}_{row['material_crm_code']}"):
                st.session_state.cart.append({"name": row["material_name"], "price": row["price"], "qty": qty, "id": row["material_crm_code"]})
                st.toast("Added!")
                st.rerun()
            st.divider()

elif st.session_state.page == "cart":
    st.title("Cart")
    if not st.session_state.cart:
        st.info("Empty")
        if st.button("Go Back"): 
            st.session_state.page = "design_select"
            st.rerun()
    else:
        total = 0
        # Header
        h1, h2, h3 = st.columns([3, 2, 1])
        h1.write("**Item**")
        h2.write("**Qty**")
        
        for i, item in enumerate(st.session_state.cart):
            c1, c2, c3 = st.columns([3, 2, 1])
            c1.write(item['name'])
            c1.caption(f"₹{item['price']}")
            
            new_qty = c2.number_input("Qty", min_value=1, value=item['qty'], key=f"cart_q_{i}", label_visibility="collapsed")
            st.session_state.cart[i]['qty'] = new_qty
            total += item['price'] * new_qty
            
            if c3.button("❌", key=f"del_{i}"):
                st.session_state.cart.pop(i)
                st.rerun()
        
        st.divider()
        st.subheader(f"Total: ₹{total}")
        col1, col2 = st.columns(2)
        if col1.button("Clear"):
            st.session_state.cart = []
            st.rerun()
        if col2.button("Back"):
            st.session_state.page = "material_listing"
            st.rerun()
