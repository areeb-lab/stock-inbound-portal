import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import io
import gspread
from google.oauth2.service_account import Credentials
import requests
import base64

# Page config
st.set_page_config(
    page_title="Stock Inbound Portal",
    page_icon="📦",
    layout="wide"
)

# Google Sheets Connection
@st.cache_resource
def get_google_sheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(st.secrets["google_sheets"]["sheet_id"]).sheet1
    return sheet

# Upload image to Imgur (Free)
def upload_to_imgur(image):
    try:
        # Convert image to base64
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=70)
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Upload to Imgur
        url = "https://api.imgur.com/3/image"
        headers = {"Authorization": "Client-ID 546c25a59c58ad7"}
        data = {"image": img_base64, "type": "base64"}
        
        response = requests.post(url, headers=headers, data=data)
        
        if response.status_code == 200:
            return response.json()["data"]["link"]
        else:
            st.error(f"Imgur error: {response.text}")
            return None
    except Exception as e:
        st.error(f"Upload error: {e}")
        return None

# Load data
def load_data():
    try:
        sheet = get_google_sheet()
        data = sheet.get_all_records()
        return data
    except Exception as e:
        st.error(f"Error: {e}")
        return []

# Save data
def save_to_sheet(order_number, image_url):
    try:
        sheet = get_google_sheet()
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([date_now, order_number, image_url])
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# Delete row
def delete_from_sheet(row_index):
    try:
        sheet = get_google_sheet()
        sheet.delete_rows(row_index + 2)
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 20px;
        background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>📦 Stock Inbound Portal</h1>
    <p>Stock ki photo aur order number save karein</p>
</div>
""", unsafe_allow_html=True)

# Layout
col1, col2 = st.columns([1, 1])

# LEFT - Form
with col1:
    st.markdown("### 📝 New Stock Entry")
    
    order_number = st.text_input("Order Number *", placeholder="Enter order number")
    
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
        elif not image_data:
            st.error("⚠️ Please take or upload an image!")
        else:
            with st.spinner("Uploading..."):
                image = Image.open(image_data)
                image.thumbnail((800, 800))
                
                # Upload to Imgur
                image_url = upload_to_imgur(image)
                
                if image_url:
                    if save_to_sheet(order_number, image_url):
                        st.success("✅ Saved!")
                        st.balloons()
                        st.rerun()

# RIGHT - Records
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
                st.markdown(f"**Date:** {record.get('Date', 'N/A')}")
                st.markdown(f"**🔗 Image:** [Click to View]({record.get('Image URL', '#')})")
                
                if st.button(f"🗑️ Delete", key=f"del_{actual_idx}"):
                    if delete_from_sheet(actual_idx):
                        st.success("Deleted!")
                        st.rerun()

# Sidebar
with st.sidebar:
    st.markdown("### 📊 Dashboard")
    records = load_data()
    st.metric("Total Records", len(records))
    
    st.markdown("---")
    
    if records:
        export_data = []
        for r in records:
            export_data.append({
                "Date": r.get('Date', ''),
                "Order Number": r.get('Order Number', ''),
                "Image URL": r.get('Image URL', '')
            })
        
        df = pd.DataFrame(export_data)
        csv = df.to_csv(index=False)
        
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"stock_records_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

st.markdown("---")
st.markdown("<p style='text-align: center; color: #888;'>📦 Stock Inbound Portal</p>", unsafe_allow_html=True)
