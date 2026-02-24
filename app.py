import streamlit as st
import pandas as pd
from datetime import datetime
import base64
from PIL import Image
import io

# Page config
st.set_page_config(
    page_title="Stock Inbound Portal",
    page_icon="📦",
    layout="wide"
)

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

# Initialize session state
if 'records' not in st.session_state:
    st.session_state.records = []

# Header
st.markdown("""
<div class="main-header">
    <h1>📦 Stock Inbound Portal</h1>
    <p>Stock ki photo aur order number save karein</p>
</div>
""", unsafe_allow_html=True)

# Convert image to base64
def image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=50)
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
    
    # 2 Options - Take Photo or Upload
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
    
    # Save Button
    if st.button("💾 Save Record", use_container_width=True):
        if not order_number:
            st.error("⚠️ Order Number is required!")
        elif not image_data:
            st.error("⚠️ Please take or upload an image!")
        else:
            image = Image.open(image_data)
            image.thumbnail((800, 800))
            image_base64 = image_to_base64(image)
            
            record = {
                "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                "order_number": order_number,
                "image": image_base64,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            st.session_state.records.insert(0, record)
            st.success("✅ Record saved successfully!")
            st.balloons()

# RIGHT - Records List
with col2:
    st.markdown("### 📋 Saved Records")
    
    search = st.text_input("🔍 Search by Order #", placeholder="Search...")
    
    filtered_records = st.session_state.records
    if search:
        filtered_records = [r for r in filtered_records if search.lower() in r['order_number'].lower()]
    
    st.markdown(f"**Total Records: {len(filtered_records)}**")
    
    if not filtered_records:
        st.info("📭 No records yet. Add your first stock entry!")
    else:
        for idx, record in enumerate(filtered_records):
            with st.expander(f"📦 Order #{record['order_number']} - {record['date'][:10]}", expanded=(idx == 0)):
                rec_col1, rec_col2 = st.columns([1, 1])
                
                with rec_col1:
                    try:
                        img = base64_to_image(record['image'])
                        st.image(img, use_container_width=True)
                    except:
                        st.error("Image not found")
                
                with rec_col2:
                    st.markdown(f"**Order #:** {record['order_number']}")
                    st.markdown(f"**Date:** {record['date']}")
                    
                    if st.button(f"🗑️ Delete", key=f"del_{record['id']}"):
                        st.session_state.records = [r for r in st.session_state.records if r['id'] != record['id']]
                        st.rerun()

# Sidebar
with st.sidebar:
    st.markdown("### 📊 Dashboard")
    st.metric("Total Records", len(st.session_state.records))
    
    if st.session_state.records:
        today = datetime.now().strftime("%Y-%m-%d")
        today_records = [r for r in st.session_state.records if r['date'].startswith(today)]
        st.metric("Today's Entries", len(today_records))
    
    st.markdown("---")
    st.markdown("### 📥 Export Data")
    
    if st.session_state.records:
        export_data = []
        for r in st.session_state.records:
            export_data.append({
                "Order Number": r['order_number'],
                "Date": r['date']
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
    if st.button("🗑️ Clear All Data", use_container_width=True):
        st.session_state.records = []
        st.rerun()

st.markdown("---")
st.markdown("<p style='text-align: center; color: #888;'>📦 Stock Inbound Portal</p>", unsafe_allow_html=True)
