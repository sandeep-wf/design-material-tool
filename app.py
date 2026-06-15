import streamlit as st
import pandas as pd

# --- Wakefit Branding Configuration ---
W_ORANGE = '#FF6600'
W_LOGO = 'https://upload.wikimedia.org/wikipedia/commons/e/e3/Wakefit_Logo.png'

st.set_page_config(page_title='Wakefit Design-to-Material Tool', layout='wide', page_icon='🛋️')

# Inject CSS for branding and mobile responsiveness
st.markdown(f'''<style>
    .stApp {{ background-color: #FDFDFD; }}
    .stButton>button { background-color: {W_ORANGE}; color: white; border-radius: 4px; border: none; }
    .stButton>button:hover { border: 1px solid {W_ORANGE}; color: {W_ORANGE}; }
    h1, h2, h3 {{ color: #333333; }}
    .stMainView {{ will-change: transform; }}
    /* Cart layout optimization for mobile */
    @media (max-width: 768px) { 
        /* Target the container for each cart item row */
        div[data-testid="stVerticalBlock"] > div > div[data-testid="stHorizontalBlock"] { 
            flex-direction: row; /* Ensure horizontal layout */
            flex-wrap: nowrap;   /* Prevent wrapping to multiple lines */
            align-items: center; /* Vertically align content */
            gap: 0.25rem;        /* Reduce gap between columns */
        }
        /* Adjust columns within the cart item to be compact */
        div[data-testid="stVerticalBlock"] > div > div[data-testid="stHorizontalBlock"] > div[data-testid="column"] { 
            flex-basis: auto; /* Allow columns to determine their own size based on content */
            flex-grow: 1;     /* Allow columns to grow if space permits */
            flex-shrink: 1;   /* Allow columns to shrink if space is tight */
            min-width: 0;     /* Allow content to push columns to minimum size */
            white-space: nowrap; /* Prevent text wrapping */
            overflow: hidden;    /* Hide overflowing text */
            text-overflow: ellipsis; /* Show ellipsis for truncated text */
        }
        /* Specific adjustments for number input */
        div[data-testid="stNumberInput"] { 
            width: 50px !important; /* Make number input very compact */
            min-width: 50px !important;
        }
        /* Smaller font for all text within cart items */
        div[data-testid="stVerticalBlock"] > div > div[data-testid="stHorizontalBlock"] * { 
            font-size: 0.75em !important; /* Smaller text for compactness */
        }
        /* Make button even smaller */
        .stButton>button { 
            padding: 0.1em 0.2em;
            font-size: 0.7em !important;
        }
    }
</style>'''
unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def load_data():
    try:
        file_path = 'design-material mapping.xlsx'
        xl = pd.ExcelFile(file_path)
        return pd.read_excel(xl, 'Designs'), pd.read_excel(xl, 'Material'), pd.read_excel(xl, 'Mapping')
    except Exception as e: st.error(f'Critical Data Error: {e}'); return None, None, None

designs_df, materials_df, mappings_df = load_data()
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'screen' not in st.session_state: st.session_state.screen = 'Design Selection'
if 'sel_design' not in st.session_state: st.session_state.sel_design = None

def nav(s): st.session_state.screen = s; st.rerun()

st.sidebar.image(W_LOGO, use_container_width=True)
st.sidebar.title('Navigation')
cnt = sum(i['quantity'] for i in st.session_state.cart.values())
if st.sidebar.button(f'🛒 View My Cart ({cnt})', use_container_width=True): nav('Cart Management')
if st.sidebar.button('🔍 Start New Search', use_container_width=True): nav('Design Selection')

if st.session_state.screen == 'Design Selection':
    st.title('🏠 Design Selection')
    if designs_df is not None:
        opts = designs_df.apply(lambda x: f"{x['design_name']} ({x['design_code']})", axis=1).tolist()
        sel = st.selectbox('Search Wakefit Designs:', opts)
        if st.button('Load Materials', type='primary'):
            st.session_state.sel_design = sel.split('(')[-1].strip(')')
            nav('Material Selection')

elif st.session_state.screen == 'Material Selection':
    d = st.session_state.sel_design
    st.title(f'📦 Materials: {d}')
    if st.button('🔙 Back to Search'): nav('Design Selection')
    m = pd.merge(mappings_df[mappings_df['design_code']==d], materials_df, left_on='material_code', right_on='material_crm_code')
    for i, r in m.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([3,1,1])
            c1.markdown(f"### {r['material_name']}"); c1.write(f"Price: ₹{r['price']:,}")
            q = c2.number_input('Quantity', 1, 100, 1, key=f'q{i}')
            if c3.button('Add to Cart', key=f'b{i}', type='primary', use_container_width=True):
                cd = r['material_crm_code']
                if cd in st.session_state.cart: st.session_state.cart[cd]['quantity'] += q
                else: st.session_state.cart[cd] = {'name':r['material_name'], 'price':r['price'], 'quantity':q}
                st.toast(f"✅ Added {r['material_name']}!")

elif st.session_state.screen == 'Cart Management':
    st.title('🛒 Cart Management')
    if st.button('➕ Add More Items'): nav('Design Selection')
    if not st.session_state.cart: st.info('Your cart is empty.')
    else:
        tot = 0
        for c, itm in list(st.session_state.cart.items()):
            sub = itm['price'] * itm['quantity']; tot += sub
            with st.container(border=True):
                cl = st.columns([3,1,1,0.5])
                cl[0].write(f"**{itm['name']}**")
                itm['quantity'] = cl[1].number_input('Qty', 1, 1000, itm['quantity'], key=f'e{c}', label_visibility='collapsed')
                cl[2].write(f"₹{sub:,.2f}")
                if cl[3].button('🗑️', key=f'd{c}'): del st.session_state.cart[c]; st.rerun()
        st.divider(); st.subheader(f'Total Estimated Cost: ₹{tot:,.2f}')
        if st.button('Clear All Items', type='secondary'): st.session_state.cart = {}; st.rerun()
