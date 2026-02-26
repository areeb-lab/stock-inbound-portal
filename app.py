import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import io
import gspread
from google.oauth2.service_account import Credentials
import requests
import base64

st.set_page_config(page_title="Stock Inbound Portal", page_icon="📦", layout="wide")

# CACHE CLEAR BUTTON
if st.sidebar.button("🔄 Clear Cache"):
    st.cache_resource.clear()
    st.rerun()

@st.cache_resource
def get_google_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(credentials)
    return client

def get_google_sheet():
    client = get_google_client()
    sheet = client.open_by_key(st.secrets["google_sheets"]["sheet_id"]).sheet1
    return sheet

# Category fetch from Dump sheet (FIXED)
def get_category_by_order(order_num):
    try:
        client = get_google_client()
        spreadsheet = client.open_by_key(st.secrets["google_sheets"]["sheet_id"])
        dump_sheet = spreadsheet.worksheet("Dump")  # Capital D
        
        # Column E (fleek_id) = 5, Column CL (category) = 90
        order_numbers = dump_sheet.col_values(5)[1:]
        categories = dump_sheet.col_values(90)[1:]
        
        for i, order in enumerate(order_numbers):
            if str(order).strip() == str(order_num).strip():
                if i < len(categories):
                    return categories[i]
                return None
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def upload_to_imgbb(image):
    try:
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=70)
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        url = "https://api.imgbb.com/1/upload"
        payload = {"key": st.secrets["imgbb"]["api_key"], "image": img_base64}
        response = requests.post(url, payload)
        
        if response.status_code == 200:
            return response.json()["data"]["url"]
        return None
    except Exception as e:
        st.error(f"Upload error: {e}")
        return None

def load_data():
    try:
        sheet = get_google_sheet()
        return sheet.get_all_records()
    except:
        return []

def save_to_sheet(order_number, category, image_url):
    try:
        sheet = get_google_sheet()
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([date_now, order_number, category, image_url])
        return True
    except:
        return False

def delete_from_sheet(row_index):
    try:
        sheet = get_google_sheet()
        sheet.delete_rows(row_index + 2)
        return True
    except:
        return False

st.markdown("""
<style>
    .main-header {text-align: center; padding: 20px; background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%); color: white; border-radius: 10px; margin-bottom: 20px;}
    .stButton>button {width: 100%; background-color: #4CAF50; color: white;}
    .category-box {padding: 15px; background-color: #1e3a5f; border-radius: 8px; margin: 10px 0; border-left: 4px solid #4CAF50;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>📦 Stock Inbound Portal</h1><p>Stock ki photo aur order number save karein</p></div>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 📝 New Stock Entry")
    order_number = st.text_input("Order Number *", placeholder="Enter order number")
    
    # AUTO-FETCH CATEGORY
    category = None
    if order_number:
        with st.spinner("🔍 Fetching category..."):
            category = get_category_by_order(order_number)
            if category:
                st.markdown(f"""
                <div class="category-box">
                    📦 <strong>Category:</strong> {category}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ Category not found for this order number")
    
    st.markdown("#### 📷 Stock Image")
    option = st.radio("Select option:", ["📷 Take Photo", "📤 Upload Photo"], horizontal=True)
    
    image_data = None
    if option == "📷 Take Photo":
        camera_photo = st.camera_input("Take a photo")
        if camera_photo:
            image_data = camera_photo
    else:
        uploaded_file = st.file_uploader("Upload image", type=['jpg', 'jpeg', 'png'])
        if uploaded_file:
            image_data = uploaded_file
    
    if st.button("💾 Save Record", use_container_width=True):
        if not order_number:
            st.error("⚠️ Order Number is required!")
        elif not category:
            st.error("⚠️ Category not found! Please check order number.")
        elif not image_data:
            st.error("⚠️ Please take or upload an image!")
        else:
            with st.spinner("Uploading..."):
                image = Image.open(image_data)
                image.thumbnail((800, 800))
                image_url = upload_to_imgbb(image)
                
                if image_url and save_to_sheet(order_number, category, image_url):
                    st.success("✅ Saved!")
                    st.balloons()
                    st.rerun()

with col2:
    st.markdown("### 📋 Saved Records")
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()
    
    records = load_data()
    search = st.text_input("🔍 Search by Order #", placeholder="Search...")
    
    if search:
        records = [r for r in records if search.lower() in str(r.get('Order Number', '')).lower()]
    
    st.markdown(f"**Total Records: {len(records)}**")
    
    if not records:
        st.info("📭 No records yet!")
    else:
        for idx, record in enumerate(reversed(records)):
            actual_idx = len(records) - 1 - idx
            with st.expander(f"📦 Order #{record.get('Order Number', 'N/A')} - {str(record.get('Date', ''))[:10]}", expanded=(idx == 0)):
                st.markdown(f"**Order #:** {record.get('Order Number', 'N/A')}")
                st.markdown(f"**Category:** {record.get('Category', 'N/A')}")
                st.markdown(f"**Date:** {record.get('Date', 'N/A')}")
                st.markdown(f"**🔗 Image:** [Click to View]({record.get('Image URL', '#')})")
                
                if st.button(f"🗑️ Delete", key=f"del_{actual_idx}"):
                    if delete_from_sheet(actual_idx):
                        st.success("Deleted!")
                        st.rerun()

with st.sidebar:
    st.markdown("### 📊 Dashboard")
    records = load_data()
    st.metric("Total Records", len(records))
    
    if records:
        df = pd.DataFrame([{
            "Date": r.get('Date', ''), 
            "Order Number": r.get('Order Number', ''), 
            "Category": r.get('Category', ''),
            "Image URL": r.get('Image URL', '')
        } for r in records])
        st.download_button("📥 Download CSV", df.to_csv(index=False), f"stock_records_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)

st.markdown("<p style='text-align: center; color: #888;'>📦 Stock Inbound Portal</p>", unsafe_allow_html=True)
