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
    path = "design_material_mapping_06.xlsx"
    if not os.path.exists(path):
        path = "/content/design_material_mapping_06.xlsx"

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
    if c_back.button("← Back"):
        st.session_state.page = "design_select"
        st.rerun()
    if c_cart.button("View Cart 🛒", key="view_cart_top"):
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
            price = row.get('price', 0)
            with st.container():
                st.markdown(f"<div class='card'><b>{row.get('material_name', 'Unknown')}</b><br>Code: {row.get(m_crm_col)}<br>Price: ₹{price}</div>", unsafe_allow_html=True)
                qty = st.number_input("Qty", min_value=1, value=1, key=f"qty_{i}")
                if st.button("Add to Cart", key=f"add_{i}"):
                    st.session_state.cart.append({"name": row.get('material_name'), "qty": qty, "id": row.get(m_crm_col), "price": float(price)})
                    st.toast("Added!")

        st.markdown("---")
        if st.button("View Cart 🛒", key="view_cart_bottom"):
            st.session_state.page = "cart"
            st.rerun()

elif st.session_state.page == "cart":
    st.title("Your Cart")
    if not st.session_state.cart:
        st.info("Your cart is empty.")
        if st.button("Back to Design Selection"):
            st.session_state.page = "design_select"
            st.rerun()
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
                    if new_qty == 0:
                        st.session_state.cart.pop(i)
                    else:
                        st.session_state.cart[i]['qty'] = new_qty
                    st.rerun()

        st.divider()
        st.markdown(f"### Grand Total: ₹{grand_total}")

        if st.button("🗑️ Clear Cart", type="primary"):
            st.session_state.cart = []
            st.rerun()

        if st.button("Back"):
            st.session_state.page = "material_listing"
            st.rerun()
