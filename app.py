import streamlit as st
import pandas as pd
import os
from datetime import date

# Page Config
st.set_page_config(page_title="Wakefit PWA", layout="centered")

def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("style.css")

@st.cache_data
def load_data():
    path = "design_material_mapping_06.xlsx"
    if not os.path.exists(path):
        st.error(f"File not found: {path}")
        st.stop()
    designs = pd.read_excel(path, sheet_name=0)
    materials = pd.read_excel(path, sheet_name=1)
    mapping = pd.read_excel(path, sheet_name=2)

    def clean_df(df):
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
        return df

    return clean_df(designs), clean_df(materials), clean_df(mapping)

try:
    df_design, df_material, df_mapping = load_data()
except Exception as e:
    st.error(f"Error loading Excel: {e}")
    st.stop()

if "cart" not in st.session_state: st.session_state.cart = []
if "page" not in st.session_state: st.session_state.page = "design_select"
if "selected_design_name" not in st.session_state: st.session_state.selected_design_name = "None"

total_items = sum(item['qty'] for item in st.session_state.cart)
st.markdown(f'<div class="cart-icon no-print">🛒 {total_items}</div>', unsafe_allow_html=True)

if st.session_state.page == "design_select":
    st.title("Select Design")
    design_names = df_design["design_name"].unique().tolist()
    selected_name = st.selectbox("Choose a design", ["-- Select --"] + design_names)
    if selected_name != "-- Select --":
        design_row = df_design[df_design["design_name"] == selected_name]
        st.session_state.selected_design = str(design_row["design_code"].values[0])
        st.session_state.selected_design_name = selected_name
        if st.button("Next"):
            st.session_state.page = "material_listing"
            st.rerun()

elif st.session_state.page == "material_listing":
    st.title("Materials")
    st.subheader(st.session_state.selected_design_name)

    c1, c2 = st.columns(2)
    if c1.button("← Back"): 
        st.session_state.page = "design_select"
        st.rerun()
    if c2.button("View Cart 🛒", key="top_v"): 
        st.session_state.page = "cart"
        st.rerun()

    target = st.session_state.selected_design
    m_codes = df_mapping[df_mapping["design_code"].astype(str) == target]["material_code"].unique().tolist()
    listing = df_material[df_material["material_crm_code"].astype(str).isin([str(x) for x in m_codes])]

    for i, row in listing.iterrows():
        with st.container():
            st.markdown(f"<div class='card'><b>{row['material_name']}</b><br>Price: ₹{row['price']}</div>", unsafe_allow_html=True)
            qty = st.number_input("Qty", 1, 100, 1, key=f"q_{i}")
            if st.button("Add to Cart", key=f"a_{i}"):
                found = False
                for item in st.session_state.cart:
                    if item["id"] == row['material_crm_code']:
                        item["qty"] += qty
                        found = True
                        break
                if not found:
                    st.session_state.cart.append({"name": row['material_name'], "qty": qty, "id": row['material_crm_code'], "price": float(row['price'])})
                st.toast("Added!")

elif st.session_state.page == "cart":
    st.markdown("<h1 class='no-print'>Your Cart</h1>", unsafe_allow_html=True)
    
    if not st.session_state.cart:
        st.info("Your cart is empty.")
        if st.button("Back to Designs"): 
            st.session_state.page = "design_select"
            st.rerun()
    else:
        col_name, col_btn = st.columns([3, 1])
        customer_name = col_name.text_input("Customer Name", placeholder="Please enter customer name")
        
        if customer_name:
            if col_btn.button("🖨️ Print"):
                st.markdown('<script>window.print();</script>', unsafe_allow_html=True)

        st.markdown(f"""
        <div class='print-only'>
            <h2 style='text-align:center;'>Quotation</h2>
            <hr>
            <p style='font-size: 1.1em;'>
                <b>Customer Name:</b> {customer_name}<br>
                <b>Design Name:</b> {st.session_state.selected_design_name}<br>
                <b>Date:</b> {date.today().strftime('%d-%m-%Y')}
            </p>
        </div>
        """, unsafe_allow_html=True)

        grand_total = 0
        table_html = "<table style='width:100%; border-collapse: collapse; margin-top:10px;' border='1'>"
        table_html += "<tr style='background-color:#f2f2f2;'><th>Product Name</th><th>Qty</th><th>Price</th><th>Total</th></tr>"

        for i, item in enumerate(st.session_state.cart):
            item_total = item['price'] * item['qty']
            grand_total += item_total
            table_html += f"<tr><td style='padding:8px;'>{item['name']}</td><td style='padding:8px; text-align:center;'>{item['qty']}</td><td style='padding:8px;'>₹{item['price']}</td><td style='padding:8px;'>₹{item_total}</td></tr>"
            
            with st.container():
                sc1, sc2 = st.columns([3, 1])
                with sc1:
                    st.markdown(f"<div class='no-print'><b>{item['name']}</b><br>₹{item['price']} x {item['qty']} = ₹{item_total}</div>", unsafe_allow_html=True)
                with sc2:
                    new_q = st.number_input("Qty", 0, 100, item['qty'], key=f"e_{i}", label_visibility="collapsed")
                    if new_q != item['qty']:
                        if new_q == 0: st.session_state.cart.pop(i)
                        else: st.session_state.cart[i]['qty'] = new_q
                        st.rerun()

        table_html += f"<tr style='background-color:#f2f2f2;'><td colspan='3' style='text-align:right; padding:8px;'><b>Grand Total</b></td><td style='padding:8px;'><b>₹{grand_total}</b></td></tr></table>"
        
        st.markdown(f"<div class='print-only'>{table_html}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='no-print'><hr><h3>Total: ₹{grand_total}</h3></div>", unsafe_allow_html=True)

        if st.button("🗑️ Clear Cart", type="primary", key="clear_c"):
            st.session_state.cart = []
            st.rerun()
        if st.button("Back to Materials", key="back_m"): 
            st.session_state.page = "material_listing"
            st.rerun()
