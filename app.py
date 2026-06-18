import streamlit as st
import pandas as pd
import os

# --- Page Configuration ---
st.set_page_config(page_title='Wakefit Material Tool', layout='wide', page_icon='🗳️')

# --- Load External CSS ---
def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css('style.css')

# --- Branding Constants ---
W_LOGO = 'https://upload.wikimedia.org/wikipedia/commons/e/e3/Wakefit_Logo.png'

@st.cache_data(show_spinner=False)
def load_data():
    try:
        # Updated to the new verified data source
        xl = pd.ExcelFile('design_material_mapping_new.xlsx')
        return pd.read_excel(xl, sheet_name='Designs'), pd.read_excel(xl, sheet_name='Material'), pd.read_excel(xl, sheet_name='Mapping')
    except Exception as e:
        st.error(f'Data Dependency Error: {e}')
        return None, None, None

df_designs, df_mats, df_map = load_data()

if 'cart' not in st.session_state: st.session_state.cart = {}
if 'screen' not in st.session_state: st.session_state.screen = 'Design Selection'

def nav(s):
    st.session_state.screen = s
    st.rerun()

st.sidebar.image(W_LOGO, use_container_width=True)
cnt = sum(i['quantity'] for i in st.session_state.cart.values())
if st.sidebar.button(f'🛒 View Cart ({cnt})', use_container_width=True): nav('Cart Management')
if st.sidebar.button('🔍 New Search', use_container_width=True): nav('Design Selection')

if st.session_state.screen == 'Design Selection':
    st.title('🏠 Select Design')
    if df_designs is not None:
        opts = df_designs.apply(lambda x: f"{x['design_name']} ({x['design_code']})", axis=1).tolist()
        sel = st.selectbox('Search Design:', opts)
        if st.button('Map Materials', type='primary'):
            st.session_state.sel_design = sel.split('(')[-1].strip(')')
            nav('Material Selection')

elif st.session_state.screen == 'Material Selection':
    d = st.session_state.sel_design
    st.title(f'📦 Materials: {d}')

    # Relational mapping logic using verified column names
    filtered_map = df_map[df_map['design_code'] == d]
    m = pd.merge(filtered_map, df_mats, left_on='material_code', right_on='material_crm_code')

    if m.empty:
        st.warning("No materials found for this design.")

    for i, r in m.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            # Displaying material_type which was causing the regression
            mat_type = f" ({r['material_type']})" if 'material_type' in r else ""
            c1.markdown(f"**{r['material_name']}**{mat_type}")
            c1.write(f"₹{r['price']:,}")
            q = c2.number_input('Qty', 1, 100, 1, key=f'q{i}', label_visibility='collapsed')
            if c3.button('Add', key=f'b{i}', type='primary', use_container_width=True):
                cd = r['material_crm_code']
                if cd in st.session_state.cart: st.session_state.cart[cd]['quantity'] += q
                else: st.session_state.cart[cd] = {'name': r['material_name'], 'price': r['price'], 'quantity': q}
                st.toast('✅ Added!')

elif st.session_state.screen == 'Cart Management':
    st.title('🛒 Cart Management')
    if not st.session_state.cart: st.info('Your cart is empty.')
    else:
        tot = 0
        for c, itm in list(st.session_state.cart.items()):
            sub = itm['price'] * itm['quantity']; tot += sub
            with st.container(border=True):
                cols = st.columns([3, 1, 1, 0.5])
                cols[0].write(f"**{itm['name']}**")
                itm['quantity'] = cols[1].number_input('Qty', 1, 1000, itm['quantity'], key=f'e{c}', label_visibility='collapsed')
                cols[2].write(f"₹{sub:,.2f}")
                if cols[3].button('🗑️', key=f'd{c}'):
                    del st.session_state.cart[c]
                    st.rerun()
        st.divider(); st.subheader(f'Total Estimate: ₹{tot:,.2f}')
