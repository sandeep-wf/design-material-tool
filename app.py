
import streamlit as st
import pandas as pd
import os
import base64

st.set_page_config(page_title="Wakefit PWA", layout="centered")

def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("style.css")

if "cart" not in st.session_state: st.session_state.cart = []
if "page" not in st.session_state: st.session_state.page = "design_select"

# UI Header
total_items = sum(item['qty'] for item in st.session_state.cart)
st.markdown(f'<div class="cart-icon">🛒 {total_items}</div>', unsafe_allow_html=True)

def display_logo():
    st.markdown("""<div style='position: fixed; top: 70px; right: 10px; z-index: 1001;'><img src='https://www.wakefit.co/favicon.ico' alt='Wakefit Logo' width='40'></div>""", unsafe_allow_html=True)

if st.session_state.page == "design_select":
    display_logo()
    st.title("Select Design")
    st.write("Please select your design to continue.")
    if st.button("Next"): 
        st.session_state.page = "material_listing"
        st.rerun()
elif st.session_state.page == "material_listing":
    display_logo()
    st.title("Materials")
    if st.button("Back"): 
        st.session_state.page = "design_select"
        st.rerun()
