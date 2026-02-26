import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image
import requests
import base64
from io import BytesIO
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="Fleek-Inbound", page_icon="🚚", layout="wide")

# --- Custom CSS ---
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 30px;
        border-radius: 15px;
        margin-bottom: 20px;
    }
    .header-title {
        color: white;
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
    }
    .header-subtitle {
        color: #888;
        text-align: center;
        font-size: 1rem;
    }
    .category-box {
        background: #1e3a5f;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #4CAF50;
        margin: 10px 0;
    }
    .stButton > button {
        background: #4CAF50;
        color: white;
        font-size: 1.2rem;
        padding: 15px 30px;
        border-radius: 10px;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- Google Sheets Connection ---
@st.cache_resource
def get_gspread_client():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(credentials)

@st.cache_data(ttl=300)
def get_dump_data():
    client = get_gspread_client()
    spreadsheet = client.open_by_key(st.secrets["google_sheets"]["sheet_id"])
    dump_sheet = spreadsheet.worksheet("Dump")
    order_numbers = dump_sheet.col_values(5)[1:]
    categories = dump_sheet.col_values(90)[1:]
    order_category_map = {}
    for i, order in enumerate(order_numbers):
        if i < len(categories):
            order_category_map[str(order).strip()] = categories[i]
    return order_category_map, order_numbers

@st.cache_data(ttl=60)
def get_scorecard_counts():
    client = get_gspread_client()
    spreadsheet = client.open_by_key(st.secrets["google_sheets"]["sheet_id"])
    
    score_card_sheet = spreadsheet.worksheet("Score Card")
    all_data = score_card_sheet.get_all_values()
    
    if len(all_data) > 1:
        data_rows = all_data[1:]
    else:
        data_rows = []
    
    today = datetime.now()
    today_formats = [
        today.strftime("%d-%b-%Y"),
        today.strftime("%d-%B-%Y"),
        today.strftime("%Y-%m-%d"),
        today.strftime("%d/%m/%Y"),
    ]
    
    pickup_ready = 0
    for row in data_rows:
        if len(row) >= 3:
            date_val = str(row[0]).strip()
            order_val = str(row[2]).strip() if len(row) > 2 else ""
            
            date_matches = any(fmt in date_val or date_val in fmt or date_val == fmt for fmt in today_formats)
            
            if date_matches and order_val:
                pickup_ready += 1
    
    main_sheet = spreadsheet.worksheet("inbound")
    main_data = main_sheet.get_all_values()
    
    inbound_done = 0
    if len(main_data) > 1:
        for row in main_data[1:]:
            if len(row) >= 1:
                date_val = str(row[0]).strip()
                date_matches = any(fmt in date_val for fmt in today_formats)
                if date_matches:
                    inbound_done += 1
    
    return pickup_ready, inbound_done

def upload_to_imgbb(image):
    buffered = BytesIO()
    image.thumbnail((800, 800))
    image.save(buffered, format="JPEG", quality=70)
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    response = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": st.secrets["imgbb"]["api_key"], "image": img_base64}
    )
    return response.json()["data"]["url"]

def save_record(order_number, category, image_url):
    client = get_gspread_client()
    spreadsheet = client.open_by_key(st.secrets["google_sheets"]["sheet_id"])
    sheet = spreadsheet.worksheet("inbound")
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([date_now, order_number, category, image_url])
    st.cache_data.clear()

order_category_map, order_list = get_dump_data()
pickup_ready, inbound_done = get_scorecard_counts()
total = pickup_ready + inbound_done

pickup_pct = (pickup_ready / total * 100) if total > 0 else 0
inbound_pct = (inbound_done / total * 100) if total > 0 else 0

col_header, col_score, col_btn = st.columns([2, 1, 0.5])

with col_header:
    st.markdown("""
    <div class="main-header">
        <div class="header-title">🚚 Fleek-Inbound 📦</div>
        <div class="header-subtitle">Jahan Vintage Wahan Fleek</div>
    </div>
    """, unsafe_allow_html=True)

with col_score:
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 20px;">
        <div style="position: relative; width: 120px; height: 120px;">
            <div style="
                width: 120px;
                height: 120px;
                border-radius: 50%;
                background: conic-gradient(
                    #E67E22 0deg {pickup_pct * 3.6}deg,
                    #27AE60 {pickup_pct * 3.6}deg 360deg
                );
                display: flex;
                align-items: center;
                justify-content: center;
            ">
                <div style="
                    width: 80px;
                    height: 80px;
                    border-radius: 50%;
                    background: #0e1117;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                ">
                    <span style="color: white; font-size: 1.5rem; font-weight: bold;">{total}</span>
                    <span style="color: #888; font-size: 0.7rem;">Total</span>
                </div>
            </div>
        </div>
        <div>
            <div style="color: #E67E22; font-weight: bold;">🟠 PICKUP_READY</div>
            <div style="color: #E67E22;">{pickup_ready} ({pickup_pct:.1f}%)</div>
            <div style="color: #27AE60; font-weight: bold; margin-top: 10px;">🟢 INBOUND_DONE</div>
            <div style="color: #27AE60;">{inbound_done} ({inbound_pct:.1f}%)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📋 Records"):
        st.session_state.show_records = not st.session_state.get('show_records', False)

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown("### 📝 New Stock Entry")
    
    selected_order = st.selectbox(
        "Order Number *",
        options=[""] + order_list,
        format_func=lambda x: "Select order number..." if x == "" else x
    )
    
    category = ""
    if selected_order:
        category = order_category_map.get(str(selected_order).strip(), "Category not found")
        st.markdown(f"""
        <div class="category-box">
            <strong>Category:</strong> {category}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("### 📷 Stock Image")
    image_option = st.radio("Select option:", ["📷 Take Photo", "📁 Upload Photo"], horizontal=True)
    
    image = None
    if image_option == "📷 Take Photo":
        camera_image = st.camera_input("Take a photo")
        if camera_image:
            image = Image.open(camera_image)
    else:
        uploaded_file = st.file_uploader("Upload image", type=["jpg", "jpeg", "png"])
        if uploaded_file:
            image = Image.open(uploaded_file)
    
    if image:
        st.image(image, caption="Preview", use_column_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚚 Chalo Inbound Mai", type="primary"):
        if not selected_order:
            st.error("Please select an order number!")
        elif not image:
            st.error("Please capture or upload an image!")
        else:
            with st.spinner("Saving..."):
                image_url = upload_to_imgbb(image)
                save_record(selected_order, category, image_url)
                st.success("✅ Record saved successfully!")
                st.balloons()

if st.session_state.get('show_records', False):
    st.markdown("---")
    st.markdown("### 📋 Today's Records")
    
    client = get_gspread_client()
    spreadsheet = client.open_by_key(st.secrets["google_sheets"]["sheet_id"])
    sheet = spreadsheet.worksheet("inbound")
    records = sheet.get_all_records()
    
    if records:
        df = pd.DataFrame(records)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No records found.")
