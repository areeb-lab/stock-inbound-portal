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

st.markdown("""
<style>
    /* Hide default streamlit padding */
    .block-container { padding-top: 1rem; }

    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 30px 40px;
        border-radius: 15px;
        margin-bottom: 20px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .header-title {
        color: white;
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin: 0;
    }
    .header-subtitle {
        color: #888;
        text-align: center;
        font-size: 1rem;
        margin-top: 8px;
    }
    .category-box {
        background: #1e3a5f;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #4CAF50;
        margin: 10px 0;
        color: white;
    }
    .vendor-box {
        background: #1e3a5f;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #E67E22;
        margin: 10px 0;
        color: white;
    }
    /* Save button green */
    div[data-testid="stButton"]:nth-of-type(1) > button {
        background: linear-gradient(135deg, #4CAF50, #388E3C) !important;
        color: white !important;
        font-size: 1.2rem !important;
        padding: 15px 30px !important;
        border-radius: 10px !important;
        width: 100% !important;
        border: none !important;
        font-weight: bold !important;
    }
    div[data-testid="stButton"]:nth-of-type(1) > button:hover {
        background: linear-gradient(135deg, #388E3C, #2E7D32) !important;
    }
    /* History button */
    div[data-testid="stButton"]:nth-of-type(2) > button {
        background: #1e3a5f !important;
        color: white !important;
        font-size: 1rem !important;
        padding: 10px 20px !important;
        border-radius: 10px !important;
        width: 100% !important;
        border: 1px solid #3a5a8f !important;
    }
    div[data-testid="stButton"]:nth-of-type(2) > button:hover {
        background: #2a4a7f !important;
    }
    .section-title {
        color: white;
        font-size: 1.2rem;
        font-weight: bold;
        margin: 15px 0 10px 0;
    }
</style>
""", unsafe_allow_html=True)


# ─── Sound ────────────────────────────────────────────────────────────────────
def play_beep_sound():
    st.markdown("""
    <audio autoplay>
        <source src="https://www.soundjay.com/buttons/beep-01a.mp3" type="audio/mpeg">
    </audio>
    """, unsafe_allow_html=True)


# ─── Google Sheets Client ─────────────────────────────────────────────────────
@st.cache_resource
def get_gspread_client():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    return gspread.authorize(credentials)


# ─── Dump Data (5 min cache) ──────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_dump_data():
    client = get_gspread_client()
    spreadsheet = client.open_by_key(st.secrets["google_sheets"]["sheet_id"])
    dump_sheet = spreadsheet.worksheet("Dump")

    order_numbers = dump_sheet.col_values(5)[1:]    # Column E (index 5)
    vendors      = dump_sheet.col_values(54)[1:]    # Column BB (index 54)
    categories   = dump_sheet.col_values(90)[1:]    # Column CL (index 90)

    order_category_map = {}
    order_vendor_map   = {}

    for i, order in enumerate(order_numbers):
        key = str(order).strip()
        order_category_map[key] = categories[i] if i < len(categories) else ""
        order_vendor_map[key]   = vendors[i]    if i < len(vendors)    else ""

    # Remove empty order numbers
    clean_orders = [o for o in order_numbers if str(o).strip()]
    return order_category_map, order_vendor_map, clean_orders


# ─── Scorecard Counts (1 min cache) ──────────────────────────────────────────
@st.cache_data(ttl=60)
def get_scorecard_counts():
    client = get_gspread_client()
    spreadsheet = client.open_by_key(st.secrets["google_sheets"]["sheet_id"])

    # Today's date in multiple formats
    today = datetime.now()
    today_formats = [
        today.strftime("%d-%b-%Y"),      # 26-Feb-2026
        today.strftime("%d-%B-%Y"),      # 26-February-2026
        today.strftime("%Y-%m-%d"),      # 2026-02-26
        today.strftime("%d/%m/%Y"),      # 26/02/2026
        today.strftime("%-d-%b-%Y"),     # 26-Feb-2026 (no leading zero)
    ]

    def date_matches(date_val):
        date_val = str(date_val).strip()
        return any(date_val == fmt or fmt == date_val for fmt in today_formats)

    # PICKUP_READY from Score Card sheet
    score_card_sheet = spreadsheet.worksheet("Score Card")
    score_data = score_card_sheet.get_all_values()
    pickup_ready = 0
    if len(score_data) > 1:
        for row in score_data[1:]:
            if len(row) >= 3:
                if date_matches(row[0]) and str(row[2]).strip():
                    pickup_ready += 1

    # INBOUND_DONE from inbound sheet
    main_sheet = spreadsheet.worksheet("inbound")
    main_data  = main_sheet.get_all_values()
    inbound_done = 0
    if len(main_data) > 1:
        for row in main_data[1:]:
            if len(row) >= 1 and str(row[0]).strip():
                # inbound sheet stores datetime like "2026-02-26 10:30:00"
                date_part = str(row[0]).strip()[:10]
                if date_part == today.strftime("%Y-%m-%d"):
                    inbound_done += 1

    return pickup_ready, inbound_done


# ─── ImgBB Upload ─────────────────────────────────────────────────────────────
def upload_to_imgbb(image: Image.Image) -> str:
    buffered = BytesIO()
    image.thumbnail((800, 800))
    image.save(buffered, format="JPEG", quality=70)
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    response = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": st.secrets["imgbb"]["api_key"], "image": img_base64},
        timeout=30
    )
    response.raise_for_status()
    return response.json()["data"]["url"]


# ─── Save Record ──────────────────────────────────────────────────────────────
def save_record(order_number, category, vendor, image_url):
    client = get_gspread_client()
    spreadsheet = client.open_by_key(st.secrets["google_sheets"]["sheet_id"])
    sheet = spreadsheet.worksheet("inbound")
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([date_now, order_number, category, vendor, image_url])
    st.cache_data.clear()


# ─── Session State Init ───────────────────────────────────────────────────────
if "form_key"      not in st.session_state: st.session_state.form_key      = 0
if "success"       not in st.session_state: st.session_state.success       = False
if "show_records"  not in st.session_state: st.session_state.show_records  = False


# ─── Load Data ────────────────────────────────────────────────────────────────
order_category_map, order_vendor_map, order_list = get_dump_data()
pickup_ready, inbound_done = get_scorecard_counts()

total       = pickup_ready + inbound_done
pickup_pct  = (pickup_ready / total * 100) if total > 0 else 50
inbound_pct = (inbound_done / total * 100) if total > 0 else 50

# Donut conic-gradient degrees
pickup_deg  = pickup_pct * 3.6
inbound_deg = inbound_pct * 3.6


# ─── HEADER ───────────────────────────────────────────────────────────────────
col_header, col_score = st.columns([2, 1.5])

with col_header:
    st.markdown("""
    <div class="main-header">
        <div class="header-title">🚚 Fleek-Inbound 📦</div>
        <div class="header-subtitle">Jahan Vintage Wahan Fleek</div>
    </div>
    """, unsafe_allow_html=True)

with col_score:
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 15px;
        padding: 20px 25px;
        display: flex;
        align-items: center;
        gap: 25px;
        height: 100%;
        box-sizing: border-box;
    ">
        <!-- Donut Chart -->
        <div style="position: relative; width: 160px; height: 160px; flex-shrink: 0;">
            <div style="
                width: 160px;
                height: 160px;
                border-radius: 50%;
                background: conic-gradient(
                    #E67E22 0deg {pickup_deg:.2f}deg,
                    #27AE60 {pickup_deg:.2f}deg 360deg
                );
                display: flex;
                align-items: center;
                justify-content: center;
            ">
                <div style="
                    width: 110px;
                    height: 110px;
                    border-radius: 50%;
                    background: #0e1117;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                ">
                    <span style="color: white; font-size: 2rem; font-weight: bold; line-height:1;">{total}</span>
                    <span style="color: #888; font-size: 0.75rem; margin-top: 2px;">Total</span>
                </div>
            </div>
        </div>

        <!-- Legend -->
        <div style="flex: 1;">
            <div style="color: #E67E22; font-weight: bold; font-size: 1rem; margin-bottom: 4px;">🟠 PICKUP_READY</div>
            <div style="color: #E67E22; font-size: 1.3rem; font-weight: bold; margin-bottom: 14px;">
                {pickup_ready} <span style="font-size: 0.85rem; opacity: 0.8;">({pickup_pct:.1f}%)</span>
            </div>
            <div style="color: #27AE60; font-weight: bold; font-size: 1rem; margin-bottom: 4px;">🟢 INBOUND_DONE</div>
            <div style="color: #27AE60; font-size: 1.3rem; font-weight: bold;">
                {inbound_done} <span style="font-size: 0.85rem; opacity: 0.8;">({inbound_pct:.1f}%)</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─── Beep after save ──────────────────────────────────────────────────────────
if st.session_state.success:
    play_beep_sound()
    st.session_state.success = False


# ─── FORM ─────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
_, col_form, _ = st.columns([1, 2, 1])

with col_form:
    st.markdown('<div class="section-title">📝 New Stock Entry</div>', unsafe_allow_html=True)

    # Order Number selectbox
    selected_order = st.selectbox(
        "Order Number *",
        options=[""] + order_list,
        format_func=lambda x: "Select order number..." if x == "" else x,
        key=f"order_{st.session_state.form_key}"
    )

    # Auto populate Category & Vendor
    category = ""
    vendor   = ""
    if selected_order:
        category = order_category_map.get(str(selected_order).strip(), "Category not found")
        vendor   = order_vendor_map.get(str(selected_order).strip(), "Vendor not found")

        col_cat, col_ven = st.columns(2)
        with col_cat:
            st.markdown(f"""
            <div class="category-box">
                <small style="color:#4CAF50; font-weight:bold;">📦 CATEGORY</small><br>
                <span style="font-size:1rem;">{category}</span>
            </div>
            """, unsafe_allow_html=True)
        with col_ven:
            st.markdown(f"""
            <div class="vendor-box">
                <small style="color:#E67E22; font-weight:bold;">🏪 VENDOR</small><br>
                <span style="font-size:1rem;">{vendor}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">📷 Stock Image</div>', unsafe_allow_html=True)

    image_option = st.radio(
        "Select option:",
        ["📷 Take Photo", "📁 Upload Photo"],
        horizontal=True,
        key=f"option_{st.session_state.form_key}"
    )

    image = None
    if image_option == "📷 Take Photo":
        camera_image = st.camera_input(
            "Take a photo",
            key=f"camera_{st.session_state.form_key}"
        )
        if camera_image:
            image = Image.open(camera_image)
    else:
        uploaded_file = st.file_uploader(
            "Upload image",
            type=["jpg", "jpeg", "png"],
            key=f"upload_{st.session_state.form_key}"
        )
        if uploaded_file:
            image = Image.open(uploaded_file)

    if image:
        st.image(image, caption="Preview", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Save Button
    if st.button("🚚 Chalo Inbound Mai", type="primary", use_container_width=True):
        if not selected_order:
            st.error("❌ Please select an order number!")
        elif not image:
            st.error("❌ Please capture or upload an image!")
        else:
            with st.spinner("⏳ Saving record..."):
                try:
                    image_url = upload_to_imgbb(image)
                    save_record(selected_order, category, vendor, image_url)
                    st.success("✅ Record saved successfully!")
                    st.session_state.success = True
                    st.session_state.form_key += 1
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    st.markdown("<br>", unsafe_allow_html=True)

    # History Button
    history_label = "📜 Hide History" if st.session_state.show_records else "📜 History"
    if st.button(history_label, use_container_width=True):
        st.session_state.show_records = not st.session_state.show_records
        st.rerun()


# ─── HISTORY ──────────────────────────────────────────────────────────────────
if st.session_state.show_records:
    st.markdown("---")
    st.markdown("### 📜 Today's Inbound History")

    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(st.secrets["google_sheets"]["sheet_id"])
        sheet = spreadsheet.worksheet("inbound")
        all_records = sheet.get_all_values()

        today_str = datetime.now().strftime("%Y-%m-%d")

        if len(all_records) > 1:
            headers = all_records[0]
            today_rows = [
                row for row in all_records[1:]
                if len(row) >= 1 and str(row[0]).strip()[:10] == today_str
            ]

            if today_rows:
                df = pd.DataFrame(today_rows, columns=headers[:len(today_rows[0])])
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption(f"Total records today: **{len(today_rows)}**")
            else:
                st.info("📭 No records found for today.")
        else:
            st.info("📭 No records found.")
    except Exception as e:
        st.error(f"❌ Error loading history: {str(e)}")
