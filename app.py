import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import io
import gspread
from google.oauth2.service_account import Credentials
import requests
import base64

st.set_page_config(page_title="Fleek-Inbound", page_icon="🚚", layout="centered")

if 'show_records' not in st.session_state:
    st.session_state.show_records = False

if st.sidebar.button("🔄 Clear Cache"):
    st.cache_resource.clear()
    st.cache_data.clear()
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

@st.cache_data(ttl=300)
def get_dump_data():
    try:
        client = get_google_client()
        spreadsheet = client.open_by_key(st.secrets["google_sheets"]["sheet_id"])
        dump_sheet = spreadsheet.worksheet("Dump")
        order_numbers = dump_sheet.col_values(5)[1:]
        categories = dump_sheet.col_values(90)[1:]
        order_category_map = {}
        for i, order in enumerate(order_numbers):
            if i < len(categories):
                order_category_map[str(order).strip()] = categories[i]
        return order_category_map
    except:
        return {}

# Get Pickup Ready count from Score Card tab
@st.cache_data(ttl=60)
def get_pickup_ready_count():
    try:
        client = get_google_client()
        spreadsheet = client.open_by_key(st.secrets["google_sheets"]["sheet_id"])
        score_card_sheet = spreadsheet.worksheet("score card")
        orders = score_card_sheet.col_values(3)[1:]  # Column C = Fleek order ID
        return len([o for o in orders if o.strip()])  # Count non-empty orders
    except Exception as e:
        return 0

# Get Inbound Done count from Sheet1
@st.cache_data(ttl=60)
def get_inbound_done_count():
    try:
        sheet = get_google_sheet()
        records = sheet.get_all_records()
        return len(records)
    except:
        return 0

def get_category_by_order(order_num):
    try:
        order_category_map = get_dump_data()
        return order_category_map.get(str(order_num).strip(), None)
    except:
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
    .category-box {
        padding: 15px; 
        background-color: #1e3a5f; 
        border-radius: 8px; 
        margin: 10px 0; 
        border-left: 4px solid #4CAF50;
    }
    .scorecard {
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        color: white;
        font-weight: bold;
    }
    .pickup-ready {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    .inbound-done {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }
    .score-number {
        font-size: 36px;
        margin: 10px 0;
    }
    .score-label {
        font-size: 14px;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# HEADER WITH SCORECARDS
st.markdown('<div class="main-header"><h1>🚚 Fleek-Inbound 📦</h1><p>Stock ki photo aur order number save karein</p></div>', unsafe_allow_html=True)

# SCORECARDS
pickup_ready = get_pickup_ready_count()
inbound_done = get_inbound_done_count()

col1, col2 = st.columns(2)

with col1:
    st.markdown(f"""
    <div class="scorecard pickup-ready">
        <div class="score-label">📦 Pickup Ready</div>
        <div class="score-number">{pickup_ready}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="scorecard inbound-done">
        <div class="score-label">✅ Inbound Done</div>
        <div class="score-number">{inbound_done}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# RECORDS BUTTON
col_spacer, col_btn = st.columns([4, 1])
with col_btn:
    if st.button("📋 Records", use_container_width=True):
        st.session_state.show_records = not st.session_state.show_records
        st.rerun()

if st.session_state.show_records:
    st.markdown("---")
    st.markdown("### 📋 Saved Records")
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("❌ Close", use_container_width=True):
            st.session_state.show_records = False
            st.rerun()
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()
    records = load_data()
    search = st.text_input("🔍 Search by Order #", placeholder="Search...", key="search_box")
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
    st.markdown("---")

st.markdown("### 📝 New Stock Entry")

order_category_map = get_dump_data()
all_orders = list(order_category_map.keys())

order_number = st.selectbox(
    "Order Number *",
    options=[""] + all_orders,
    index=0,
    placeholder="Type or select order number"
)

category = None
if order_number:
    category = order_category_map.get(order_number, None)
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

if st.button("🚚 Chalo Inbound Mai", use_container_width=True):
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
                st.cache_data.clear()  # Refresh scorecard
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
        st.download_button("📥 Download CSV", df.to_csv(index=False), f"fleek_inbound_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)

st.markdown("<p style='text-align: center; color: #888; margin-top: 50px;'>🚚 Fleek-Inbound 📦</p>", unsafe_allow_html=True)
