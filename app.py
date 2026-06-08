import streamlit as st
import pandas as pd

# --- Page Configuration ---
st.set_page_config(page_title="Design-to-Material Tool", layout="wide")

# --- Data Loading ---
@st.cache_data
def load_data():
    try:
        file_path = 'design-material mapping.xlsx'
        xl = pd.ExcelFile(file_path)
        # Using indices for sheets: 0: Designs, 1: Materials, 2: Mappings
        designs = pd.read_excel(xl, sheet_name=0)
        materials = pd.read_excel(xl, sheet_name=1)
        mappings = pd.read_excel(xl, sheet_name=2)
        return designs, materials, mappings
    except Exception as e:
        st.error(f"Data Error: {e}")
        return None, None, None

designs_df, materials_df, mappings_df = load_data()

if designs_df is None:
    st.stop()

# --- Session State ---
if 'cart' not in st.session_state:
    st.session_state.cart = {}
if 'current_screen' not in st.session_state:
    st.session_state.current_screen = 'Design Selection'
if 'selected_design' not in st.session_state:
    st.session_state.selected_design = None

# --- Sidebar ---
st.sidebar.title("Selection Tool")
cart_len = sum(item['quantity'] for item in st.session_state.cart.values())

if st.sidebar.button("🔍 Search Designs", use_container_width=True):
    st.session_state.current_screen = 'Design Selection'
    st.rerun()

if st.sidebar.button(f"🛒 View Cart ({cart_len})", use_container_width=True):
    st.session_state.current_screen = 'Cart Management'
    st.rerun()

# --- Logic for Screens ---
if st.session_state.current_screen == 'Design Selection':
    st.title("Design Selection")
    options = designs_df.apply(lambda x: f"{x['design_name']} ({x['design_code']})", axis=1).tolist()
    sel = st.selectbox("Choose a design:", options)
    if st.button("View Materials", type="primary"):
        st.session_state.selected_design = sel.split('(')[-1].strip(')')
        st.session_state.current_screen = 'Material Selection'
        st.rerun()

elif st.session_state.current_screen == 'Material Selection':
    st.title(f"Materials for {st.session_state.selected_design}")
    d_code = st.session_state.selected_design
    filtered = mappings_df[mappings_df['design_code'] == d_code]
    mats = pd.merge(filtered, materials_df, left_on='material_code', right_on='material_crm_code')
    
    for i, r in mats.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{r['material_name']}**")
            c1.caption(f"Price: ${r['price']}")
            q = c2.number_input("Qty", 1, 100, 1, key=f"q_{i}")
            if c3.button("Add", key=f"b_{i}"):
                code = r['material_crm_code']
                if code in st.session_state.cart:
                    st.session_state.cart[code]['quantity'] += q
                else:
                    st.session_state.cart[code] = {'name': r['material_name'], 'price': r['price'], 'quantity': q}
                st.toast("Added!")

elif st.session_state.current_screen == 'Cart Management':
    st.title("Cart Management")
    if not st.session_state.cart:
        st.info("Empty cart.")
    else:
        total = 0
        for c, item in list(st.session_state.cart.items()):
            sub = item['price'] * item['quantity']
            total += sub
            with st.container(border=True):
                cols = st.columns([3, 1, 1, 0.5])
                cols[0].write(item['name'])
                item['quantity'] = cols[1].number_input("Qty", 1, 1000, item['quantity'], key=f"edit_{c}")
                cols[2].write(f"${sub:,.2f}")
                if cols[3].button("🗑️", key=f"del_{c}"):
                    del st.session_state.cart[c]
                    st.rerun()
        st.header(f"Total: ${total:,.2f}")
        if st.button("Clear Cart"): 
            st.session_state.cart = {}
            st.rerun()
"
