import streamlit as st
import pandas as pd

# --- Wakefit Branding Configuration ---
W_ORANGE = '#FF6600'
W_LOGO = 'wakefit logo.png'

st.set_page_config(page_title='Wakefit Material Tool', layout='wide', page_icon='🛋️')

# Custom CSS for UI Density and Hardware Acceleration
st.markdown(f'''<style>
    .stApp {{ background-color: #FDFDFD; }}
    .stButton>button {{ background-color: {W_ORANGE}; color: white; border-radius: 4px; border: none; }}
    .stButton>button:hover {{ border: 1px solid {W_ORANGE}; color: {W_ORANGE}; }}
    .stMainView {{ will-change: transform; }}
    h1 {{ font-size: 1.2rem !important; }}
    h2 {{ font-size: 1.0rem !important; }}
    h3 {{ font-size: 0.9rem !important; }}
</style>''', unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def load_data():
    try:
        xl = pd.ExcelFile('design-material mapping.xlsx')
        return pd.read_excel(xl, 'Designs'), pd.read_excel(xl, 'Material'), pd.read_excel(xl, 'Mapping')
    except Exception as e: st.error(f'Data Error: {e}'); return None, None, None

designs_df, materials_df, mappings_df = load_data()
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'screen' not in st.session_state: st.session_state.screen = 'Design Selection'
if 'sel_design' not in st.session_state: st.session_state.sel_design = None

def nav(s): st.session_state.screen = s; st.rerun()

# --- Sidebar Navigation ---
st.sidebar.image(W_LOGO, use_container_width=True)
cnt = sum(i['quantity'] for i in st.session_state.cart.values())
if st.sidebar.button(f'🛒 View Cart ({cnt})', use_container_width=True): nav('Cart Management')
if st.sidebar.button('🔍 New Search', use_container_width=True): nav('Design Selection')

# --- Screen 1: Design Selection ---
if st.session_state.screen == 'Design Selection':
    st.title('🏠 Select Design')
    if designs_df is not None:
        opts = designs_df.apply(lambda x: f"{x['design_name']} ({x['design_code']})", axis=1).tolist()
        sel = st.selectbox('Search Design:', opts)
        if st.button('Map Materials', type='primary'):
            st.session_state.sel_design = sel.split('(')[-1].strip(')')
            nav('Material Selection')

# --- Screen 2: Material Selection ---
elif st.session_state.screen == 'Material Selection':
    d = st.session_state.sel_design
    col_title, col_cart = st.columns([5, 1])
    with col_title: st.title(f'📦 Materials: {d}')
    with col_cart: 
        if st.button(f'🛒 ({cnt})'): nav('Cart Management')

    m = pd.merge(mappings_df[mappings_df['design_code']==d], materials_df, left_on='material_code', right_on='material_crm_code')
    for i, r in m.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([3,1,1])
            c1.markdown(f"**{r['material_name']}**"); c1.write(f"₹{r['price']:,}")
            q = c2.number_input('Qty', 1, 100, 1, key=f'q{i}', label_visibility='collapsed')
            if c3.button('Add', key=f'b{i}', type='primary', use_container_width=True):
                cd = r['material_crm_code']
                if cd in st.session_state.cart: st.session_state.cart[cd]['quantity'] += q
                else: st.session_state.cart[cd] = {'name':r['material_name'], 'price':r['price'], 'quantity':q}
                st.toast('Added!')

# --- Screen 3: Cart Management (Single-Line Layout) ---
elif st.session_state.screen == 'Cart Management':
    st.title('🛒 Cart Management')
    if not st.session_state.cart: st.info('Cart is empty.')
    else:
        tot = 0
        for c, itm in list(st.session_state.cart.items()):
            sub = itm['price'] * itm['quantity']; tot += sub
            with st.container(border=True):
                # Space-optimized Single-line Cart Item
                cols = st.columns([3, 1, 1, 0.5])
                cols[0].write(f"**{itm['name']}**")
                itm['quantity'] = cols[1].number_input('Qty', 1, 1000, itm['quantity'], key=f'e{c}', label_visibility='collapsed')
                cols[2].write(f"₹{sub:,.2f}")
                if cols[3].button('🗑️', key=f'd{c}'): del st.session_state.cart[c]; st.rerun()
        st.divider(); st.subheader(f'Total Estimate: ₹{tot:,.2f}')
        if st.button('Clear All', type='secondary'): st.session_state.cart = {}; st.rerun()
