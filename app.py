
import streamlit as st
import pandas as pd
import os
from datetime import date
from fpdf import FPDF
import base64

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
    path = "design-material-mapping_22_2.xlsx"
    if not os.path.exists(path): path = "/content/design-material-mapping_22_2.xlsx"
    if not os.path.exists(path):
        st.warning(f"File not found: {path}. Creating dummy data.")
        with pd.ExcelWriter(path) as writer:
            pd.DataFrame({'design_code': ['D001'], 'design_name': ['Sample Design'], 'published': ['YES'], 'active': ['YES']}).to_excel(writer, sheet_name=0, index=False)
            pd.DataFrame({'material_crm_code': ['M001', 'M002'], 'material_name': ['Sample Material 1', 'Sample Material 2'], 'price': [100.0, 150.0]}).to_excel(writer, sheet_name=1, index=False)
            pd.DataFrame({'design_code': ['D001', 'D001'], 'material_crm_code': ['M001', 'M002']}).to_excel(writer, sheet_name=2, index=False)

    designs = pd.read_excel(path, sheet_name=0)
    materials = pd.read_excel(path, sheet_name=1)
    mapping = pd.read_excel(path, sheet_name=2)

    def clean_df(df):
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
        return df

    designs = clean_df(designs); materials = clean_df(materials); mapping = clean_df(mapping)

    for df in [designs, mapping, materials]:
        for col in df.columns:
            if 'code' in col: df[col] = df[col].astype(str).str.strip()

    return designs, materials, mapping

try:
    df_design, df_material, df_mapping = load_data()
except Exception as e:
    st.error(f"Error loading Excel: {e}"); st.stop()

# Session State
if "cart" not in st.session_state: st.session_state.cart = []
if "page" not in st.session_state: st.session_state.page = "design_select"
if "selected_design" not in st.session_state: st.session_state.selected_design = None
if "selected_design_name" not in st.session_state: st.session_state.selected_design_name = None

# UI Header - Clickable Sticky Cart Button (Main Container)
total_items = sum(item['qty'] for item in st.session_state.cart)
if st.button(f"🛒 Cart ({total_items})", key="sticky_cart_btn"):
    st.session_state.page = "cart"
    st.rerun()

# Helper to display logo
def display_logo():
    try:
        with open("wakefit logo.png", "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode("utf-8")
        st.markdown(f"""<div style='position: fixed; top: 70px; right: 10px; z-index: 1001; padding: 5px; background-color: rgba(255,255,255,0.8); border-radius: 5px;'><img src='data:image/png;base64,{logo_base64}' alt='Wakefit Logo' width='80'></div>""", unsafe_allow_html=True)
    except FileNotFoundError: st.error("Wakefit logo file 'wakefit logo.png' not found.")

def display_footer():
    st.markdown("<br><hr><p style='text-align: center;'>© 2026 Wakefit. All Rights Reserved</p>", unsafe_allow_html=True)

if st.session_state.page == "design_select":
    display_logo(); st.title("Select Design")
    mask_pub = df_design["published"].astype(str).str.strip().str.upper() == "YES" if "published" in df_design.columns else True
    mask_act = df_design["active"].astype(str).str.strip().str.upper() == "YES" if "active" in df_design.columns else True
    active_designs = df_design[mask_pub & mask_act]

    design_names = active_designs["design_name"].unique().tolist() if "design_name" in active_designs.columns else []
    selected_name = st.selectbox("Choose a design", ["-- Select --"] + design_names)
    if selected_name != "-- Select --":
        design_row = active_designs[active_designs["design_name" ] == selected_name]
        st.session_state.selected_design = str(design_row["design_code"].values[0])
        st.session_state.selected_design_name = selected_name
        if st.button("Next"): st.session_state.page = "material_listing"; st.rerun()
    display_footer()

elif st.session_state.page == "material_listing":
    display_logo(); st.title("Materials")
    if st.session_state.selected_design_name: st.subheader(st.session_state.selected_design_name)
    if st.button("← Back"): st.session_state.page = "design_select"; st.rerun()

    target_design = st.session_state.selected_design
    m_code_col = "material_code" if "material_code" in df_mapping.columns else "material_crm_code"
    mapped_codes = df_mapping[df_mapping["design_code"] == target_design][m_code_col].unique().tolist()
    m_crm_col = "material_crm_code" if "material_crm_code" in df_material.columns else df_material.columns[0]
    listing = df_material[df_material[m_crm_col].isin(mapped_codes)]

    if listing.empty:
        st.warning("No materials mapped.")
    else:
        for i, row in listing.iterrows():
            price = row.get("price", 0); m_id = row.get(m_crm_col)
            with st.container():
                st.markdown(f"<div class='card'><b>{row.get('material_name', 'Unknown')}</b><br>Code: {m_id}<br>Price: ₹{price}</div>", unsafe_allow_html=True)
                qty = st.number_input("Qty", min_value=1, value=1, key=f"qty_{i}")
                if st.button("Add to Cart", key=f"add_{i}"):
                    found = False
                    for item in st.session_state.cart:
                        if item["id" ] == m_id: item["qty"] += qty; found = True; break
                    if not found: st.session_state.cart.append({"name": row.get("material_name"), "qty": qty, "id": m_id, "price": float(price)})
                    st.toast("Added!")
        if st.button("View Cart 🛒", key="view_cart_bottom"): 
            st.session_state.page = "cart"
            st.rerun()
    display_footer()

elif st.session_state.page == "cart":
    display_logo(); st.title("Your Cart")
    customer_name = st.text_input("Customer Name", key="customer_name_input")
    partner_name = st.selectbox("Select Partner", ["Rajesh", "Nirmal"], key="partner_name_select")
    special_remarks = st.text_area("Special Remarks", key="special_remarks_input")

    if not st.session_state.cart:
        st.info("Your cart is empty.")
        if st.button("Back"): st.session_state.page = "design_select"; st.rerun()
    else:
        grand_total = 0
        for i, item in enumerate(st.session_state.cart):
            item_total = item["price"] * item["qty"]; grand_total += item_total
            st.write(f"{item['name']} x {item['qty']} = ₹{item_total}")

        st.divider()
        dp = st.number_input("Discount %", 0.0, 100.0, 0.0, step=0.1); da = (grand_total * dp) / 100; ft = grand_total - da
        st.markdown(f"### Total: ₹{ft:,.2f}")
        uploaded_file = st.file_uploader("Hand Made Design Image", type=["png", "jpg", "jpeg"])

        if st.button("🖨️ Print PDF", use_container_width=True):
            pdf = FPDF(); pdf.add_page(); pdf.image('wakefit logo.png', x=175, y=10, w=25)
            pdf.set_font("Arial", "B", 16); pdf.set_xy(30, 15); pdf.cell(0, 10, "Wakefit Quotation", 0, 1, "C"); pdf.ln(5)
            pdf.set_font("Arial", "", 12); pdf.cell(190, 10, f"Customer: {customer_name}", 0, 1); pdf.cell(190, 10, f"Partner: {partner_name}", 0, 1)
            pdf.cell(190, 10, f"Design: {st.session_state.selected_design_name}", 0, 1); pdf.cell(190, 10, f"Date: {date.today().strftime('%d-%m-%Y')}", 0, 1); pdf.multi_cell(190, 10, f"Remarks: {special_remarks}"); pdf.ln(5)

            pdf.set_font("Arial", "B", 12); pdf.cell(100, 10, "Product", 1); pdf.cell(20, 10, "Qty", 1, 0, "C"); pdf.cell(35, 10, "Price", 1, 0, "C"); pdf.cell(35, 10, "Total", 1, 1, "C")
            pdf.set_font("Arial", "", 10)
            for item in st.session_state.cart:
                y_pre = pdf.get_y(); pdf.multi_cell(100, 10, f"{item['name']} ({item['id']})", 1); rh = pdf.get_y() - y_pre
                pdf.set_xy(110, y_pre); pdf.cell(20, rh, str(item['qty']), 1, 0, "C"); pdf.cell(35, rh, f"Rs.{item['price']}", 1, 0, "C"); pdf.cell(35, rh, f"Rs.{item['price']*item['qty']}", 1, 1, "C")

            pdf.set_font("Arial", "B", 12); pdf.cell(155, 10, "Grand Total", 1, 0, "R"); pdf.cell(35, 10, f"Rs.{grand_total:,.2f}", 1, 1, "C")
            if dp > 0:
                pdf.set_font("Arial", "", 10); pdf.cell(155, 10, f"Discount ({dp}%)", 1, 0, "R"); pdf.cell(35, 10, f"- Rs.{da:,.2f}", 1, 1, "C")
                pdf.set_font("Arial", "B", 12); pdf.cell(155, 10, "Final Amount", 1, 0, "R"); pdf.cell(35, 10, f"Rs.{ft:,.2f}", 1, 1, "C")

            # Static Disclaimer Section
            pdf.ln(5); pdf.set_font("Arial", "B", 11); pdf.cell(190, 10, "Disclaimer:", 0, 1)
            pdf.set_font("Arial", "", 10)
            disclaimer_txt = ["1: It is not an invoice, Invoice will be shared after payment and installation.", "2: The quotes shared are valid for 15 days.", "3: Discount is valid only for 3 days.", "4: Please reach out to us on whatsapp at +91-9071079479 for the installation or any customer query"]
            for point in disclaimer_txt: pdf.multi_cell(190, 7, point)

            if uploaded_file:
                ext = uploaded_file.name.split('.')[-1]
                tp = f"temp_design.{ext}"
                with open(tp, "wb") as f: f.write(uploaded_file.getbuffer())
                pdf.ln(5); pdf.cell(190, 10, "Hand Made Design:", 0, 1); pdf.image(tp, x=10, w=100)

            pdf.ln(10); pdf.set_font("Arial", "", 8); pdf.cell(190, 10, "© 2026 Wakefit. All Rights Reserved", 0, 0, "C")

            b64 = base64.b64encode(pdf.output(dest='S').encode('latin-1')).decode('latin-1')

            # Dynamic Filename generation
            today_str = date.today().strftime('%d-%m-%Y')
            clean_cust = customer_name.replace(' ', '_').strip() if customer_name else "Customer"
            clean_partner = partner_name.replace(' ', '_').strip() if partner_name else "Partner"
            filename = f"{clean_cust}_{clean_partner}_{today_str}.pdf"

            href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}"><button style="width:100%; padding:10px; background-color:#1A237E; color:white; border:none; border-radius:8px;">Download PDF</button></a>'
            st.markdown(href, unsafe_allow_html=True)

        c_back, c_home = st.columns(2)
        if c_back.button("Back", key="back_btn"): st.session_state.page = "material_listing"; st.rerun()
        if c_home.button("Home", key="home_btn"): st.session_state.page = "design_select"; st.rerun()
    display_footer()
