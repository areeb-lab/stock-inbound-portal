import streamlit as st
import pandas as pd
from datetime import datetime
import base64
from PIL import Image
import io
import gspread
from google.oauth2.service_account import Credentials

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

# Load data from Google Sheets
def load_data():
    try:
        sheet = get_google_sheet()
        data = sheet.get_all_records()
        return data
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return []

# Save data to Google Sheets
def save_to_sheet(order_number, image_base64):
    try:
        sheet = get_google_sheet()
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([date_now, order_number, image_base64])
        return True
    except Exception as e:
        st.error(f"Error saving: {e}")
        return False

# Delete row from Google Sheets
def delete_from_sheet(row_index):
    try:
        sheet = get_google_sheet()
        sheet.delete_rows(row_index + 2)
        return True
    except Exception as e:
        st.error(f"Error deleting: {e}")
        return False

# Custom CSS
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
    <small>☁️ Data Google Sheets mein save hota hai</small>
</div>
""", unsafe_allow_html=True)

# Convert image to base64
def image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=30)
    return base64.b64encode(buffered.getvalue()).decode()

# Convert base64 to image
def base64_to_image(base64_string):
    image_data = base64.b64decode(base64_string)
    return Image.open(io.BytesIO(image_data))

# Main layout
col1, col2 = st.columns([1, 1])

# LEFT - Input Form
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
            with st.spinner("Saving to Google Sheets..."):
                image = Image.open(image_data)
                image.thumbnail((800, 800))
                image_base64 = image_to_base64(image)
                
                if save_to_sheet(order_number, image_base64):
                    st.success("✅ Record saved to Google Sheets!")
                    st.balloons()
                    st.rerun()

# RIGHT - Records List
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
        st.info("📭 No records yet. Add your first stock entry!")
    else:
        for idx, record in enumerate(reversed(records)):
            actual_idx = len(records) - 1 - idx
            with st.expander(f"📦 Order #{record.get('Order Number', 'N/A')} - {str(record.get('Date', ''))[:10]}", expanded=(idx == 0)):
                rec_col1, rec_col2 = st.columns([1, 1])
                
                with rec_col1:
                    try:
                        img = base64_to_image(record.get('Image URL', ''))
                        st.image(img, use_container_width=True)
                    except:
                        st.error("Image not found")
                
                with rec_col2:
                    st.markdown(f"**Order #:** {record.get('Order Number', 'N/A')}")
                    st.markdown(f"**Date:** {record.get('Date', 'N/A')}")
                    
                    if st.button(f"🗑️ Delete", key=f"del_{actual_idx}"):
                        if delete_from_sheet(actual_idx):
                            st.success("Deleted!")
                            st.rerun()

# Sidebar
with st.sidebar:
    st.markdown("### 📊 Dashboard")
    records = load_data()
    st.metric("Total Records", len(records))
    
    if records:
        today = datetime.now().strftime("%Y-%m-%d")
        today_records = [r for r in records if str(r.get('Date', '')).startswith(today)]
        st.metric("Today's Entries", len(today_records))
    
    st.markdown("---")
    st.markdown("### 📥 Export Data")
    
    if records:
        export_data = []
        for r in records:
            export_data.append({
                "Date": r.get('Date', ''),
                "Order Number": r.get('Order Number', '')
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
st.markdown("<p style='text-align: center; color: #888;'>📦 Stock Inbound Portal | Data saved in Google Sheets</p>", unsafe_allow_html=True)
