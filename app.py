import streamlit as st
import pandas as pd
import os

# --- Page Configuration ---
st.set_page_config(page_title='Wakefit Material Tool', layout='wide', page_icon='🛋️')

# --- Load External CSS ---
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f.read(), unsafe_allow_html=True)

local_css('style.css')

# --- Data Loading ---
@st.cache_data(show_spinner=False)
def load_data():
    try:
        xl = pd.ExcelFile('design-material mapping.xlsx')
        return pd.read_excel(xl, sheet_name=0), pd.read_excel(xl, sheet_name=1), pd.read_excel(xl, sheet_name=2)
    except Exception as e:
        st.error(f'Data Error: {e}')
        return None, None, None

designs_df, materials_df, mappings_df = load_data()

# --- State Management ---
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'screen' not in st.session_state: st.session_state.screen = 'Design Selection'
if 'sel_design' not in st.session_state: st.session_state.sel_design = None

def nav(s):
    st.session_state.screen = s
    st.rerun()

# --- Sidebar ---
st.sidebar.title('Selection Tool')
cnt = sum(i['quantity'] for i in st.session_state.cart.values())
if st.sidebar.button(f'🛒 View Cart ({cnt})', use_container_width=True): nav('Cart Management')
if st.sidebar.button('🔍 Search Designs', use_container_width=True): nav('Design Selection')

# --- Screens ---
if st.session_state.screen == 'Design Selection':
    st.title('🏠 Select Design')
    if designs_df is not None:
        opts = designs_df.apply(lambda x: f"{x[designs_df.columns[1]]} ({x[designs_df.columns[2]]})", axis=1).tolist()
        sel = st.selectbox('Search available designs:', opts)
        if st.button('Map Materials', type='primary'):
            st.session_state.sel_design = sel.split('(')[-1].strip(')')
            nav('Material Selection')

elif st.session_state.screen == 'Material Selection':
    d_code = st.session_state.sel_design
    st.title(f'📦 Materials for: {d_code}')
    if st.button('🔙 Back'): nav('Design Selection')

    filtered = mappings_df[mappings_df['design_code'] == d_code]
    mats = pd.merge(filtered, materials_df, left_on='material_code', right_on='material_crm_code')

    for idx, row in mats.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([3,1,1])
            c1.markdown(f"**{row['material_name']}**")
            c1.write(f"Price: ₹{row['price']:,}")
            qty = c2.number_input('Qty', 1, 100, 1, key=f'q{idx}', label_visibility='collapsed')
            if c3.button('Add to Cart', key=f'b{idx}', type='primary', use_container_width=True):
                code = row['material_crm_code']
                if code in st.session_state.cart:
                    st.session_state.cart[code]['quantity'] += qty
                else:
                    st.session_state.cart[code] = {'name': row['material_name'], 'price': row['price'], 'quantity': qty}
                st.toast(f'✅ Added {row["material_name"]}!')

elif st.session_state.screen == 'Cart Management':
    st.title('🛒 Cart Management')
    if st.button('➕ Add More'): nav('Design Selection')
    if not st.session_state.cart:
        st.info('Your cart is empty.')
    else:
        tot = 0
        for c, itm in list(st.session_state.cart.items()):
            sub = itm['price'] * itm['quantity']
            tot += sub
            with st.container(border=True):
                # Space-optimized Single-line Cart Item using tight column ratios
                cols = st.columns([3.5, 1, 1, 0.5])
                cols[0].write(f"**{itm['name']}**")
                itm['quantity'] = cols[1].number_input('Qty', 1, 1000, itm['quantity'], key=f'e{c}', label_visibility='collapsed')
                cols[2].write(f'₹{sub:,.2f}')
                if cols[3].button('🗑️', key=f'd{c}'):
                    del st.session_state.cart[c]
                    st.rerun()
        st.divider()
        st.header(f'Total Estimate: ₹{tot:,.2f}')
