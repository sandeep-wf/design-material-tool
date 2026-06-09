import streamlit as st
import pandas as pd

st.set_page_config(page_title='Design-to-Material Tool', layout='wide')

st.markdown("\n    <style>\n    .stMainView { will-change: transform; }\n    [data-testid='stVerticalBlock'] > div:has(div.stMetric) { contain: content; }\n    </style>\n", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def load_data():
    try:
        file_path = 'design-material mapping.xlsx'
        xl = pd.ExcelFile(file_path)
        designs = pd.read_excel(xl, sheet_name='Designs')
        materials = pd.read_excel(xl, sheet_name='Material')
        mappings = pd.read_excel(xl, sheet_name='Mapping')
        return designs, materials, mappings
    except Exception as e:
        st.error(f'Critical Data Error: {e}')
        return None, None, None

designs_df, materials_df, mappings_df = load_data()

if 'cart' not in st.session_state: st.session_state.cart = {}
if 'current_screen' not in st.session_state: st.session_state.current_screen = 'Design Selection'
if 'selected_design' not in st.session_state: st.session_state.selected_design = None

def navigate_to(screen):
    st.session_state.current_screen = screen
    st.rerun()

st.sidebar.title('Selection Tool')
cart_count = sum(item['quantity'] for item in st.session_state.cart.values())
if st.sidebar.button(f'🛒 View Cart ({cart_count})', use_container_width=True): navigate_to('Cart Management')
if st.sidebar.button('🔍 Search Designs', use_container_width=True): navigate_to('Design Selection')

if st.session_state.current_screen == 'Design Selection':
    st.title('Design Selection')
    if designs_df is not None:
        options = designs_df.apply(lambda x: f"{x['design_name']} ({x['design_code']})", axis=1).tolist()
        sel = st.selectbox('Search for a design:', options)
        if st.button('Proceed to Materials', type='primary'):
            st.session_state.selected_design = sel.split('(')[-1].strip(')')
            navigate_to('Material Selection')

elif st.session_state.current_screen == 'Material Selection':
    d_code = st.session_state.selected_design
    st.title(f'Materials for: {d_code}')
    filtered = mappings_df[mappings_df['design_code'] == d_code]
    mats = pd.merge(filtered, materials_df, left_on='material_code', right_on='material_crm_code')
    for idx, row in mats.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.markdown(f"### {row['material_name']}")
                st.markdown(f"**Price:** ₹{row['price']:,}")
            with c2:
                qty = st.number_input('Qty', 1, 100, 1, key=f'q_{idx}')
            with c3:
                st.write('')
                if st.button('Add', key=f'b_{idx}', type='primary', use_container_width=True):
                    code = row['material_crm_code']
                    if code in st.session_state.cart: st.session_state.cart[code]['quantity'] += qty
                    else: st.session_state.cart[code] = {'name': row['material_name'], 'price': row['price'], 'quantity': qty}
                    st.toast(f"✅ Added {row['material_name']}!")

elif st.session_state.current_screen == 'Cart Management':
    st.title('🛒 Cart Management')
    if not st.session_state.cart: st.info('Your cart is empty.')
    else:
        total = 0
        for c, item in list(st.session_state.cart.items()):
            sub = item['price'] * item['quantity']
            total += sub
            with st.container(border=True):
                cols = st.columns([3, 1, 1, 0.5])
                cols[0].write(item['name'])
                item['quantity'] = cols[1].number_input('Qty', 1, 1000, item['quantity'], key=f'edit_{c}')
                cols[2].write(f'₹{sub:,.2f}')
                if cols[3].button('🗑️', key=f'del_{c}'):
                    del st.session_state.cart[c]
                    st.rerun()
        st.divider()
        st.header(f'Grand Total: ₹{total:,.2f}')
        if st.button('Clear All', type='secondary'):
            st.session_state.cart = {}
            st.rerun()
