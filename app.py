
import streamlit as st
import pandas as pd
import os
from datetime import date
from fpdf import FPDF
import base64
import requests
import json

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
    path = "design-material-mapping_29_1.xlsx"
    if not os.path.exists(path): path = "/content/design-material-mapping_29_1.xlsx"
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
if "selection_mode" not in st.session_state: st.session_state.selection_mode = "Select a Design"
if "selected_material_id" not in st.session_state: st.session_state.selected_material_id = None

# Helper to format SKU
def format_sku(sku):
    sku_str = str(sku)
    if len(sku_str) > 4:
        return f"{sku_str[:-4]}<b style='color: black;'>{sku_str[-4:]}</b>"
    return f"<b style='color: black;'>{sku_str}</b>"

# UI Header
def display_header():
    total_items = sum(item['qty'] for item in st.session_state.cart)
    if st.session_state.page == "cart":
        col1, col2 = st.columns([1, 1])
        if col1.button("🏠 Home", key="top_home_btn"):
            st.session_state.cart = []
            st.session_state.page = "design_select"
            st.rerun()
        if col2.button("← Back", key="top_back_btn"):
            st.session_state.page = "material_listing"
            st.rerun()
    else:
        if st.button(f"🛒 Cart ({total_items})", key="sticky_cart_btn"):
            st.session_state.page = "cart"
            st.rerun()

display_header()

def display_logo():
    try:
        with open("wakefit logo.png", "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode("utf-8")
        st.markdown(f"""<div style='position: fixed; top: 70px; right: 10px; z-index: 1001; padding: 5px; background-color: rgba(255,255,255,0.8); border-radius: 5px;'><img src='data:image/png;base64,{logo_base64}' alt='Wakefit Logo' width='80'></div>""", unsafe_allow_html=True)
    except FileNotFoundError: st.error("Wakefit logo file 'wakefit logo.png' not found.")

def display_footer():
    st.markdown("<br><hr><p style='text-align: center;'>© 2026 Wakefit. All Rights Reserved</p>", unsafe_allow_html=True)

if st.session_state.page == "design_select":
    display_logo(); st.title("Wakefit Selector")
    st.session_state.selection_mode = st.radio("Choose Mode", ["Select a Design", "Select Material"], index=0)

    if st.session_state.selection_mode == "Select a Design":
        mask_pub = df_design["published"].astype(str).str.strip().str.upper() == "YES" if "published" in df_design.columns else True
        mask_act = df_design["active"].astype(str).str.strip().str.upper() == "YES" if "active" in df_design.columns else True
        active_designs = df_design[mask_pub & mask_act]
        design_names = active_designs["design_name"].unique().tolist() if "design_name" in active_designs.columns else []
        selected_name = st.selectbox("Choose a design", ["-- Select --"] + design_names)
        if selected_name != "-- Select --":
            design_row = active_designs[active_designs["design_name" ] == selected_name]
            st.session_state.selected_design = str(design_row["design_code"].values[0])
            st.session_state.selected_design_name = selected_name
            st.session_state.selected_material_id = None
            if st.button("Next"): st.session_state.page = "material_listing"; st.rerun()

    else:
        m_crm_col = "material_crm_code" if "material_crm_code" in df_material.columns else df_material.columns[0]
        search_query = st.text_input("Search Material (e.g. S168)", "")
        if search_query.strip():
            filtered_df = df_material[df_material.apply(lambda x: search_query.lower() in str(x.get('material_name', '')).lower() or search_query.lower() in str(x.get(m_crm_col, '')).lower(), axis=1)]
        else:
            filtered_df = df_material
        mat_display = filtered_df.apply(lambda x: f"{x.get('material_name', 'Unknown')} ({x.get(m_crm_col)})", axis=1).tolist()
        selected_mat_str = st.selectbox("Select from results", ["-- Select --"] + mat_display)
        if selected_mat_str != "-- Select --":
            selected_id = selected_mat_str.split('(')[-1].strip(')')
            st.session_state.selected_material_id = selected_id
            st.session_state.selected_design = None
            st.session_state.selected_design_name = "Single Material Selection"
            if st.button("Next"): st.session_state.page = "material_listing"; st.rerun()

    display_footer()

elif st.session_state.page == "material_listing":
    display_logo()
    design_suffix = f" ({st.session_state.selected_design_name})" if st.session_state.selected_design_name else ""
    st.markdown(f"### Materials{design_suffix}", unsafe_allow_html=True)
    if st.button("← Back", key="listing_back_top"): st.session_state.page = "design_select"; st.rerun()
    m_crm_col = "material_crm_code" if "material_crm_code" in df_material.columns else df_material.columns[0]
    if st.session_state.selected_material_id:
        listing = df_material[df_material[m_crm_col].astype(str) == st.session_state.selected_material_id]
    else:
        target_design = st.session_state.selected_design
        m_code_col = "material_code" if "material_code" in df_mapping.columns else "material_crm_code"
        mapped_codes = df_mapping[df_mapping["design_code"] == target_design][m_code_col].unique().tolist()
        listing = df_material[df_material[m_crm_col].isin(mapped_codes)]

    if listing.empty:
        st.warning("No materials found.")
    else:
        for i, row in listing.iterrows():
            m_name = str(row.get("material_name", "Unknown"))
            price = row.get("price", 0); m_id = row.get(m_crm_col)
            formatted_id = format_sku(m_id)
            with st.container():
                st.markdown(f"<div class='card material-card'><b>{m_name}</b><br>Code: {formatted_id}<br>Price: ₹{price}</div>", unsafe_allow_html=True)

                is_u_trim = "wall u trim" in m_name.lower()
                is_t_trim = "wall t trim" in m_name.lower()
                is_bidding = "wall bidding" in m_name.lower()
                sel_attr1, sel_attr2 = "", ""

                if is_u_trim or is_t_trim:
                    col_attr1, col_attr2 = st.columns(2)
                    sel_attr1 = col_attr1.selectbox(f"Color", ["Gold", "Black", "Rose gold"], key=f"trim_color_{i}")
                    if is_u_trim:
                        sel_attr2 = col_attr2.selectbox(f"Size", ["10mm", "12mm", "15mm", "20mm"], key=f"trim_size_{i}")
                    else:
                        sel_attr2 = col_attr2.selectbox(f"Size", ["6mm", "12mm", "18mm"], key=f"trim_size_{i}")
                elif is_bidding:
                    col_attr1, col_attr2 = st.columns(2)
                    sel_attr1 = col_attr1.selectbox(f"Material", ["WPC", "PVC"], key=f"bid_mat_{i}")
                    num_options = [f"{x:02d}" for x in range(1, 16)]
                    sel_attr2 = col_attr2.selectbox(f"Number", num_options, key=f"bid_num_{i}")

                c_qty, c_add = st.columns([1, 2])
                qty = c_qty.number_input("Qty", min_value=1, value=1, key=f"qty_{i}")
                if c_add.button("Add to Cart", key=f"add_{i}"):
                    if is_u_trim or is_t_trim or is_bidding:
                        item_name_final = f"{m_name.title()} {sel_attr1} {sel_attr2}"
                    else:
                        item_name_final = m_name

                    found = False
                    for item in st.session_state.cart:
                        if item["id"] == m_id and item["name" ] == item_name_final:
                            item["qty" ] += qty; found = True; break
                    if not found:
                        st.session_state.cart.append({"name": item_name_final, "qty": qty, "id": m_id, "price": float(price)})
                    st.toast("Added!")
        st.divider()
        if st.button("View Cart 🛒", key="view_cart_bottom"): st.session_state.page = "cart"; st.rerun()
        if st.button("← Back", key="listing_back_bottom"): st.session_state.page = "design_select"; st.rerun()
    display_footer()

elif st.session_state.page == "cart":
    display_logo(); st.title("Your Cart")
    customer_name = st.text_input("Customer Name", key="customer_name_input")
    phone_number = st.text_input("Phone number:", key="phone_number_input", placeholder="919XXXXXXXXX")
    partner_name = st.selectbox("Select Partner", ["Rajesh", "Nirmal"], key="partner_name_select")
    special_remarks = st.text_area("Special Remarks", key="special_remarks_input")

    if not st.session_state.cart:
        st.info("Your cart is empty.")
        if st.button("Back"): st.session_state.page = "design_select"; st.rerun()
    else:
        st.subheader("🛒 Items in Cart")
        grand_total = 0
        for i, item in enumerate(st.session_state.cart):
            item_total = item["price"] * item["qty"]; grand_total += item_total
            formatted_id = format_sku(item['id'])
            with st.container():
                col_txt, col_edit = st.columns([3, 1])
                col_txt.markdown(f"""
                <div style='background-color: #f9f9f9; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 5px solid #1A237E;'>
                    <b>{item['name']}</b><br>
                    <small>SKU: {formatted_id}</small><br>
                    <span>₹{item['price']} x {item['qty']} = <b>₹{item_total:,.2f}</b></span>
                </div>
                """, unsafe_allow_html=True)
                new_qty = col_edit.number_input("Qty", min_value=0, value=item["qty"], key=f"edit_{i}")
                if new_qty != item["qty"]:
                    if new_qty == 0:
                        st.session_state.cart.pop(i)
                    else:
                        st.session_state.cart[i]["qty"] = new_qty
                    st.rerun()

        st.divider()
        dp = st.number_input("Discount %", 0.0, 100.0, value=None, placeholder="0.0", step=0.1);
        dp_val = dp if dp is not None else 0.0
        da = (grand_total * dp_val) / 100; ft = (grand_total - da)
        st.markdown(f"### Total (excl. delivery): ₹{ft:,.2f}")
        uploaded_file = st.file_uploader("Hand Made Design Image", type=["png", "jpg", "jpeg"])
        if uploaded_file:
            st.image(uploaded_file, caption="Uploaded Design Preview", use_container_width=True)
        col_clr, col_prnt = st.columns(2)
        if col_clr.button("🗑️ Clear Cart", type="primary", use_container_width=True): st.session_state.cart = []; st.rerun()
        
        if col_prnt.button("🖨️ Print PDF", use_container_width=True):
            delivery_charge = 1000
            final_amount_with_delivery = ft + delivery_charge

            pdf = FPDF(); pdf.add_page(); pdf.image('wakefit logo.png', x=175, y=10, w=25)
            pdf.set_font("Arial", "B", 16); pdf.set_xy(30, 15); pdf.cell(0, 10, "Wakefit Quotation", 0, 1, "C"); pdf.ln(5)
            pdf.set_font("Arial", "", 12); pdf.cell(190, 10, f"Customer: {customer_name}", 0, 1); pdf.cell(190, 10, f"Partner: {partner_name}", 0, 1)
            pdf.cell(190, 10, f"Design: {st.session_state.selected_design_name}", 0, 1); pdf.cell(190, 10, f"Date: {date.today().strftime('%d-%m-%Y')}", 0, 1); pdf.multi_cell(190, 10, f"Remarks: {special_remarks}"); pdf.ln(5)
            pdf.set_font("Arial", "B", 12); pdf.cell(100, 10, "Product", 1); pdf.cell(20, 10, "Qty", 1, 0, "C"); pdf.cell(35, 10, "Price", 1, 0, "C"); pdf.cell(35, 10, "Total", 1, 1, "C")
            pdf.set_font("Arial", "", 10)
            for item in st.session_state.cart:
                y_pre = pdf.get_y(); pdf.multi_cell(100, 10, f"{item['name']} ({item['id']})", 1); rh = pdf.get_y() - y_pre
                pdf.set_xy(110, y_pre); pdf.cell(20, rh, str(item['qty']), 1, 0, "C"); pdf.cell(35, rh, f"Rs.{item['price']}", 1, 0, "C"); pdf.cell(35, rh, f"Rs.{item['price']*item['qty']}", 1, 1, "C")

            pdf.set_font("Arial", "B", 12); pdf.cell(155, 10, "Items Subtotal", 1, 0, "R"); pdf.cell(35, 10, f"Rs.{grand_total:,.2f}", 1, 1, "C")
            if dp_val > 0:
                pdf.set_font("Arial", "", 10); pdf.cell(155, 10, f"Discount ({dp_val}%) ", 1, 0, "R"); pdf.cell(35, 10, f"- Rs.{da:,.2f}", 1, 1, "C")

            pdf.set_font("Arial", "", 10); pdf.cell(155, 10, "Delivery Charges", 1, 0, "R"); pdf.cell(35, 10, f"Rs.{delivery_charge:,.2f}", 1, 1, "C")
            pdf.set_font("Arial", "B", 12); pdf.cell(155, 10, "Final Amount", 1, 0, "R"); pdf.cell(35, 10, f"Rs.{final_amount_with_delivery:,.2f}", 1, 1, "C")

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
            
            # Save locally for WhatsApp API and generate download link
            local_pdf_path = "quotation.pdf"
            pdf.output(local_pdf_path)
            
            b64 = base64.b64encode(open(local_pdf_path, "rb").read()).decode('latin-1')
            today_str = date.today().strftime('%d-%m-%Y')
            clean_cust = customer_name.replace(' ', '_').strip() if customer_name else "Customer"
            clean_partner = partner_name.replace(' ', '_').strip() if partner_name else "Partner"
            filename = f"{clean_cust}_{clean_partner}_{today_str}.pdf"
            
            st.session_state.pdf_ready = True
            st.session_state.pdf_b64 = b64
            st.session_state.pdf_filename = filename
            st.session_state.final_amount_val = f"{final_amount_with_delivery:,.2f}"

        if st.session_state.get("pdf_ready"):
            href = f'<a href="data:application/octet-stream;base64,{st.session_state.pdf_b64}" download="{st.session_state.pdf_filename}"><button style="width:100%; padding:10px; background-color:#1A237E; color:white; border:none; border-radius:8px; margin-bottom:10px;">Download Quotation</button></a>'
            st.markdown(href, unsafe_allow_html=True)
            
            if st.button("Share on Whatsapp", use_container_width=True):
                if not phone_number:
                    st.error("Please enter a phone number.")
                else:
                    with st.spinner("Sharing quotation..."):
                        try:
                            # API 1: Upload Media
                            upload_url = "https://media.smsgupshup.com/GatewayAPI/rest"
                            payload = {
                                'method': 'UploadMedia',
                                'media_type': 'document',
                                'v': '1.1',
                                'format': 'json',
                                'auth_scheme': 'plain',
                                'userid': '2000264220',
                                'password': 'IakKOS7Ot'
                            }
                            files = [('media_file', ('quotation.pdf', open('quotation.pdf', 'rb'), 'application/pdf'))]
                            r1 = requests.post(upload_url, data=payload, files=files)
                            res1 = r1.json()
                            
                            if res1.get("response", {}).get("status") == "success":
                                media_id = res1["response"]["id"]
                                
                                # API 2: Send Media Message
                                send_url = "https://mediaapi.smsgupshup.com/GatewayAPI/rest"
                                headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                                data = {
                                    'method': 'SENDMEDIAMESSAGE',
                                    'send_to': phone_number,
                                    'msg_type': 'DOCUMENT',
                                    'isHSM': 'true',
                                    'v': '1.1',
                                    'format': 'json',
                                    'auth_scheme': 'plain',
                                    'userid': '2000264220',
                                    'password': 'IakKOS7Ot',
                                    'media_id': media_id,
                                    'filename': 'Wakefit Wall Makeover Quotation.pdf',
                                    'whatsAppTemplateId': '2216484149134300',
                                    'var1': customer_name,
                                    'var2': st.session_state.final_amount_val
                                }
                                r2 = requests.post(send_url, headers=headers, data=data)
                                if r2.status_code == 200:
                                    st.success("Shared successfully on WhatsApp!")
                                else:
                                    st.error(f"Failed to send message: {r2.text}")
                            else:
                                st.error("Media upload failed.")
                        except Exception as e:
                            st.error(f"An error occurred: {e}")

    display_footer()
