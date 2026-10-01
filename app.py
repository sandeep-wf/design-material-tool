
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

def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("style.css")

@st.cache_data
def load_data():
    path = "design-material-mapping_25_2.xlsx"
    if not os.path.exists(path): path = "/content/design-material-mapping_25_2.xlsx"
    if not os.path.exists(path):
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
    st.error(f"Error: {e}"); st.stop()

if "cart" not in st.session_state: st.session_state.cart = []
if "page" not in st.session_state: st.session_state.page = "design_select"

def format_sku(sku):
    sku_str = str(sku)
    return f"{sku_str[:-4]}<b style='color: black;'>{sku_str[-4:]}</b>" if len(sku_str) > 4 else f"<b>{sku_str}</b>"

def display_header():
    total_items = sum(item['qty'] for item in st.session_state.cart)
    if st.session_state.page == "cart":
        col1, col2 = st.columns([1, 1])
        if col1.button("🏠 Home", key="top_home_btn"): st.session_state.cart = []; st.session_state.page = "design_select"; st.rerun()
        if col2.button("← Back", key="top_back_btn"): st.session_state.page = "material_listing"; st.rerun()
    elif st.session_state.page == "catalog":
        if st.button("← Back to Home"): st.session_state.page = "design_select"; st.rerun()
    else:
        if st.button(f"🛒 Cart ({total_items})", key="sticky_cart_btn"): st.session_state.page = "cart"; st.rerun()

display_header()

if st.session_state.page == "catalog":
    st.title("Catalog Collection")
    catalogs = {"PVC Catalog": "pvc.pdf", "UV Sheet": "uv.pdf", "Charcoal": "charcoal.pdf", "CPC": "cpc.pdf", "3D Panels": "3d.pdf", "Designs": "design.pdf", "Past Work": "past.pdf"}
    for label, file_path in catalogs.items():
        with st.container():
            col_label, col_down = st.columns([3, 1])
            col_label.markdown(f"### {label}")
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    col_down.download_button("Download", data=f, file_name=file_path, mime="application/pdf", key=f"dl_{label}", use_container_width=True)
            else:
                col_down.button("File Missing", disabled=True, key=f"missing_{label}", use_container_width=True)
            st.divider()

elif st.session_state.page == "design_select":
    st.title("Wakefit Selector")
    if st.button("View Catalogs", use_container_width=True): st.session_state.page = "catalog"; st.rerun()
    st.session_state.selection_mode = st.radio("Choose Mode", ["Select a Design", "Select Material", "Manual Entry"], index=1)
    if st.session_state.selection_mode == "Select a Design":
        active_designs = df_design[((df_design["published"].astype(str).str.upper() == "YES") & (df_design["active"].astype(str).str.upper() == "YES"))]
        sel = st.selectbox("Choose a design", ["-- Select --"] + active_designs["design_name"].unique().tolist())
        if sel != "-- Select --":
            row = active_designs[active_designs["design_name"] == sel]
            st.session_state.selected_design = str(row["design_code"].values[0])
            st.session_state.selected_design_name = sel
            st.session_state.selected_material_id = None
            st.session_state.manual_entry_data = None
            if st.button("Next"): st.session_state.page = "material_listing"; st.rerun()
    elif st.session_state.selection_mode == "Select Material":
        q = st.text_input("Search Material")
        filtered = df_material[df_material.apply(lambda x: q.lower() in str(x.get('material_name','')).lower() or q.lower() in str(x.get('material_crm_code','')).lower(), axis=1)]
        mat = st.selectbox("Results", ["-- Select --"] + filtered.apply(lambda x: f"{x['material_name']} ({x['material_crm_code']})", axis=1).tolist())
        if mat != "-- Select --":
            st.session_state.selected_material_id = mat.split('(')[-1].strip(')')
            st.session_state.selected_design = None
            st.session_state.selected_design_name = "Single Selection"
            st.session_state.manual_entry_data = None
            if st.button("Next"): st.session_state.page = "material_listing"; st.rerun()
    elif st.session_state.selection_mode == "Manual Entry":
        n = st.text_input("Name"); c = st.text_input("Code"); p = st.number_input("Price", 0.0)
        if st.button("Next") and n and c:
            st.session_state.manual_entry_data = {"name": n, "code": c, "price": p}
            st.session_state.selected_design = None; st.session_state.selected_material_id = None
            st.session_state.selected_design_name = "Manual Entry"
            st.session_state.page = "material_listing"; st.rerun()

elif st.session_state.page == "material_listing":
    st.markdown(f"### Materials ({st.session_state.get('selected_design_name', 'Selection')})")
    if st.button("← Back", key="listing_back_top"): st.session_state.page = "design_select"; st.rerun()
    m_crm_col = "material_crm_code"

    if st.session_state.get("manual_entry_data"):
        listing = pd.DataFrame([st.session_state["manual_entry_data"]])
        m_crm_col = "code"
    elif st.session_state.get("selected_material_id"):
        listing = df_material[df_material[m_crm_col].astype(str) == st.session_state.selected_material_id]
    else:
        codes = df_mapping[df_mapping["design_code"] == st.session_state.get("selected_design")]["material_crm_code"].unique().tolist()
        listing = df_material[df_material[m_crm_col].isin(codes)]

    for i, row in listing.iterrows():
        m_name = str(row.get("material_name", row.get("name", "Unknown")))
        m_price = row.get("price", 0); m_id = row.get(m_crm_col)
        with st.container():
            st.markdown(f"<div class='card material-card'><b>{m_name}</b><br>Code: {format_sku(m_id)}<br>Price: ₹{m_price}</div>", unsafe_allow_html=True)
            is_trim = any(x in m_name.lower() for x in ["u trim", "t trim"])
            is_bidding = "wall bidding" in m_name.lower()
            s1, s2 = "", ""
            if is_trim:
                c1, c2 = st.columns(2)
                s1 = c1.selectbox("Color", ["Gold", "Black", "Rose gold"], key=f"c_{i}")
                s2 = c2.selectbox("Size", ["10mm", "12mm", "15mm"] if "u trim" in m_name.lower() else ["6mm", "12mm"], key=f"s_{i}")
            elif is_bidding:
                c1, c2 = st.columns(2)
                s1 = c1.selectbox("Material", ["WPC", "PVC"], key=f"bm_{i}")
                s2 = c2.selectbox("Number", [f"{x:02d}" for x in range(1, 16)], key=f"bn_{i}")

            cq, ca = st.columns([1, 2])
            qty = cq.number_input("Qty", 1, 100, 1, key=f"qty_{i}")
            if ca.button("Add to Cart", key=f"add_{i}"):
                found = False
                final_name = f"{m_name} {s1} {s2}".strip()
                for item in st.session_state.cart:
                    if item["id"] == m_id and item["name"] == final_name:
                        item["qty"] += qty; found = True; break
                if not found:
                    st.session_state.cart.append({"name": final_name, "qty": qty, "id": m_id, "price": float(m_price)})
                st.toast("Added!")
    st.divider()
    if st.button("View Cart 🛒"): st.session_state.page = "cart"; st.rerun()

elif st.session_state.page == "cart":
    st.title("Your Cart")
    c_name = st.text_input("Customer Name", key="cn_in"); p_phone = st.text_input("Phone (91...)", key="ph_in")
    p_name = st.selectbox("Partner", ["Rajesh", "Nirmal"], key="pn_sel"); remarks = st.text_area("Remarks", key="rem_in")
    if not st.session_state.cart:
        st.info("Cart is empty.")
        if st.button("Back"): st.session_state.page = "design_select"; st.rerun()
    else:
        gt = 0
        for i, item in enumerate(st.session_state.cart):
            it = item['price']*item['qty']; gt += it
            with st.container():
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"<b>{item['name']}</b><br><small>SKU: {format_sku(item['id'])}</small><br>₹{item['price']} x {item['qty']} = ₹{it:,.2f}", unsafe_allow_html=True)
                nq = c2.number_input("Qty", 0, 100, item['qty'], key=f"ed_{i}")
                if nq != item['qty']:
                    if nq == 0: st.session_state.cart.pop(i)
                    else: st.session_state.cart[i]['qty'] = nq
                    st.rerun()
        st.divider(); dp = st.number_input("Discount %", 0.0, 100.0, 0.0, step=0.1); da = (gt*dp)/100; ft = gt - da + 1000
        st.markdown(f"### Total (incl. ₹1000 delivery): ₹{ft:,.2f}")
        files = st.file_uploader("Reference Images", type=["png","jpg","jpeg"], accept_multiple_files=True)
        
        if st.button("Print PDF", use_container_width=True):
            pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16)
            try: pdf.image('wakefit logo.png', x=175, y=10, w=25)
            except: pass
            pdf.cell(190, 10, "Wakefit Quotation", 0, 1, "C"); pdf.ln(5); pdf.set_font("Arial", "", 12)
            pdf.cell(190, 10, f"Customer: {c_name}", 0, 1); pdf.cell(190, 10, f"Partner: {p_name}", 0, 1)
            pdf.cell(190, 10, f"Design: {st.session_state.get('selected_design_name')}", 0, 1); pdf.cell(190, 10, f"Date: {date.today()}", 0, 1); pdf.multi_cell(190, 10, f"Remarks: {remarks}"); pdf.ln(5)
            pdf.set_font("Arial", "B", 12); pdf.cell(100, 10, "Product", 1); pdf.cell(20, 10, "Qty", 1, 0, "C"); pdf.cell(35, 10, "Price", 1, 0, "C"); pdf.cell(35, 10, "Total", 1, 1, "C")
            pdf.set_font("Arial", "", 10)
            for item in st.session_state.cart:
                y_pre = pdf.get_y(); pdf.multi_cell(100, 10, f"{item['name']} ({item['id']})", 1); rh = pdf.get_y() - y_pre
                pdf.set_xy(110, y_pre); pdf.cell(20, rh, str(item['qty']), 1, 0, "C"); pdf.cell(35, rh, f"Rs.{item['price']}", 1, 0, "C"); pdf.cell(35, rh, f"Rs.{item['price']*item['qty']}", 1, 1, "C")
            
            pdf.set_font("Arial", "B", 12); pdf.cell(155, 10, "Items Subtotal", 1, 0, "R"); pdf.cell(35, 10, f"Rs.{gt:,.2f}", 1, 1, "C")
            if dp > 0:
                pdf.set_font("Arial", "", 10); pdf.cell(155, 10, f"Discount ({dp}%) ", 1, 0, "R"); pdf.cell(35, 10, f"- Rs.{da:,.2f}", 1, 1, "C")
            pdf.set_font("Arial", "", 10); pdf.cell(155, 10, "Delivery Charges", 1, 0, "R"); pdf.cell(35, 10, "Rs.1,000.00", 1, 1, "C")
            pdf.set_font("Arial", "B", 12); pdf.cell(155, 10, "Final Amount", 1, 0, "R"); pdf.cell(35, 10, f"Rs.{ft:,.2f}", 1, 1, "C")
            
            pdf.ln(5); pdf.set_font("Arial", "B", 11); pdf.cell(190, 10, "Disclaimer:", 0, 1); pdf.set_font("Arial", "", 10)
            disclaimer = ["1: It is not an invoice, Invoice will be shared after payment and installation.", "2: The quotes shared are valid for 15 days.", "3: Discount is valid only for 3 days.", "4: Please reach out to us on whatsapp at +91-9071079479 for the installation or any customer query"]
            for d in disclaimer: pdf.multi_cell(190, 7, d)
            
            if files:
                pdf.ln(5); pdf.cell(190, 10, "Reference Images:", 0, 1)
                for idx, f in enumerate(files):
                    ext = f.name.split('.')[-1].lower()
                    fname = f"t_{idx}.{ext}"
                    with open(fname, "wb") as tf: tf.write(f.getbuffer())
                    pdf.image(fname, x=10, w=100); pdf.ln(5)
            
            pdf.output("q.pdf"); b64 = base64.b64encode(open("q.pdf","rb").read()).decode('latin-1')
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="Quotation.pdf"><button style="width:100%">Download PDF</button></a>'
            st.markdown(href, unsafe_allow_html=True)
            st.session_state.pdf_ready = True
            st.session_state.final_amt_str = f"{ft:,.2f}"
            st.session_state.pdf_customer = c_name

        if st.session_state.get("pdf_ready") and st.button("Share on WhatsApp", use_container_width=True):
            if not p_phone: st.error("Enter phone number.")
            else:
                with st.spinner("Sending to WhatsApp..."):
                    try:
                        up_url = "https://media.smsgupshup.com/GatewayAPI/rest"
                        payload = {'method': 'UploadMedia', 'media_type': 'document', 'v': '1.1', 'format': 'json', 'auth_scheme': 'plain', 'userid': '2000264220', 'password': 'IakKOS7Ot'}
                        files_api = [('media_file', ('quotation.pdf', open('q.pdf', 'rb'), 'application/pdf'))]
                        r1 = requests.post(up_url, data=payload, files=files_api).json()
                        if r1.get("response", {}).get("status") == "success":
                            mid = r1["response"]["id"]
                            send_url = "https://mediaapi.smsgupshup.com/GatewayAPI/rest"
                            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                            data = {'method': 'SENDMEDIAMESSAGE', 'send_to': p_phone, 'msg_type': 'DOCUMENT', 'isHSM': 'true', 'v': '1.1', 'format': 'json', 'auth_scheme': 'plain', 'userid': '2000264220', 'password': 'IakKOS7Ot', 'media_id': mid, 'filename': 'Wakefit Wall Makeover Quotation.pdf', 'whatsAppTemplateId': '2216484149134300', 'var1': st.session_state.pdf_customer, 'var2': st.session_state.final_amt_str}
                            r2 = requests.post(send_url, headers=headers, data=data)
                            if r2.status_code == 200: st.success("Quotation shared successfully!")
                            else: st.error("API send error.")
                        else: st.error("Upload failed.")
                    except Exception as e: st.error(f"Integration error: {e}")

        if st.button("← Back to Materials"): st.session_state.page = "material_listing"; st.rerun()
