import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import io
import gspread
from google.oauth2.service_account import Credentials
import requests
import base64
import time

st.set_page_config(page_title="Fleek-bound", page_icon="🚚", layout="wide")

# ANIMATED TRUCK INTRO
if 'show_intro' not in st.session_state:
    st.session_state.show_intro = True

if st.session_state.show_intro:
    intro_placeholder = st.empty()
    
    with intro_placeholder.container():
        st.markdown("""
        <style>
            .intro-container {
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                z-index: 9999;
            }
            
            .truck-container {
                text-align: center;
                animation: driveIn 2s ease-out forwards;
            }
            
            @keyframes driveIn {
                0% { transform: translateX(-100vw); }
                100% { transform: translateX(0); }
            }
            
            .truck {
                font-size: 120px;
                animation: bounce 0.5s ease infinite;
            }
            
            @keyframes bounce {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-10px); }
            }
            
            .door-container {
                position: relative;
                width: 300px;
                height: 200px;
                margin: 20px auto;
                perspective: 1000px;
            }
            
            .truck-back {
                width: 300px;
                height: 200px;
                background: linear-gradient(145deg, #2d3436, #636e72);
                border-radius: 10px;
                display: flex;
                justify-content: center;
                align-items: center;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            }
            
            .door {
                position: absolute;
                width: 300px;
                height: 200px;
                background: linear-gradient(145deg, #74b9ff, #0984e3);
                border-radius: 10px;
                transform-origin: top;
                animation: openDoor 2s ease-out 2s forwards;
                display: flex;
                justify-content: center;
                align-items: center;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }
            
            @keyframes openDoor {
                0% { transform: rotateX(0deg); }
                100% { transform: rotateX(-110deg); }
            }
            
            .grn-text {
                font-size: 28px;
                font-weight: bold;
                color: white;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
                opacity: 0;
                animation: fadeIn 1s ease-out 3.5s forwards;
            }
            
            @keyframes fadeIn {
                0% { opacity: 0; transform: scale(0.5); }
                100% { opacity: 1; transform: scale(1); }
            }
            
            .inbound-text {
                font-size: 42px;
                font-weight: bold;
                background: linear-gradient(90deg, #00b894, #00cec9, #0984e3);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-shadow: none;
                opacity: 0;
                animation: fadeIn 1s ease-out 4s forwards, glow 2s ease-in-out infinite 4s;
            }
            
            @keyframes glow {
                0%, 100% { filter: brightness(1); }
                50% { filter: brightness(1.3); }
            }
            
            .wheels {
                display: flex;
                justify-content: space-around;
                margin-top: -10px;
            }
            
            .wheel {
                width: 40px;
                height: 40px;
                background: #2d3436;
                border-radius: 50%;
                border: 5px solid #636e72;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .loading-text {
                color: #dfe6e9;
                font-size: 18px;
                margin-top: 30px;
                opacity: 0;
                animation: fadeIn 1s ease-out 4.5s forwards;
            }
        </style>
        
        <div class="intro-container">
            <div class="truck-container">
                <div class="truck">🚚</div>
                
                <div class="door-container">
                    <div class="truck-back">
                        <div style="text-align: center;">
                            <div class="inbound-text">📦 INBOUND</div>
                            <div class="grn-text">GRN</div>
                        </div>
                    </div>
                    <div class="door">
                        <span style="font-size: 40px;">📦</span>
                    </div>
                </div>
                
                <div class="wheels">
                    <div class="wheel"></div>
                    <div class="wheel"></div>
                </div>
                
                <div class="loading-text">Loading Fleek-bound...</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    time.sleep(6)
    st.session_state.show_intro = False
    intro_placeholder.empty()
    st.rerun()

# CACHE CLEAR BUTTON
if st.sidebar.button("🔄 Clear Cache"):
    st.cache_resource.clear()
    st.rerun()

# REPLAY INTRO BUTTON
if st.sidebar.button("🚚 Replay Intro"):
    st.session_state.show_intro = True
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

# Category fetch from Dump sheet
def get_category_by_order(order_num):
    try:
        client = get_google_client()
        spreadsheet = client.open_by_key(st.secrets["google_sheets"]["sheet_id"])
        dump_sheet = spreadsheet.worksheet("Dump")
        
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

st.markdown('<div class="main-header"><h1>🚚 Fleek-bound</h1><p>Stock ki photo aur order number save karein</p></div>', unsafe_allow_html=True)

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
        st.download_button("📥 Download CSV", df.to_csv(index=False), f"fleek_bound_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)

st.markdown("<p style='text-align: center; color: #888;'>🚚 Fleek-bound</p>", unsafe_allow_html=True)
