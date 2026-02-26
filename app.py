from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image
import requests
import base64
from io import BytesIO
from datetime import datetime
import os
import json

app = Flask(__name__, static_folder='static')
CORS(app)

# ─── Google Sheets Client ─────────────────────────────────────────────────────
def get_gspread_client():
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        raise Exception("GOOGLE_SERVICE_ACCOUNT_JSON env variable not set")
    creds_dict = json.loads(creds_json)
    credentials = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    return gspread.authorize(credentials)

def get_sheet_id():
    return os.environ.get("GOOGLE_SHEET_ID", "")

def get_imgbb_key():
    return os.environ.get("IMGBB_API_KEY", "")

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/orders", methods=["GET"])
def get_orders():
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(get_sheet_id())
        dump_sheet = spreadsheet.worksheet("Dump")

        order_numbers = dump_sheet.col_values(5)[1:]    # Col E
        vendors       = dump_sheet.col_values(54)[1:]   # Col BB
        categories    = dump_sheet.col_values(90)[1:]   # Col CL

        orders = []
        for i, order in enumerate(order_numbers):
            order = str(order).strip()
            if not order:
                continue
            orders.append({
                "id": order,
                "category": categories[i] if i < len(categories) else "",
                "vendor":   vendors[i]    if i < len(vendors)    else ""
            })

        return jsonify({"success": True, "orders": orders})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scorecard", methods=["GET"])
def get_scorecard():
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(get_sheet_id())
        today = datetime.now()

        today_formats = [
            today.strftime("%d-%b-%Y"),
            today.strftime("%d-%B-%Y"),
            today.strftime("%Y-%m-%d"),
            today.strftime("%d/%m/%Y"),
        ]

        # PICKUP_READY
        score_card_sheet = spreadsheet.worksheet("Score Card")
        score_data = score_card_sheet.get_all_values()
        pickup_ready = 0
        if len(score_data) > 1:
            for row in score_data[1:]:
                if len(row) >= 3:
                    date_val = str(row[0]).strip()
                    if any(date_val == fmt for fmt in today_formats) and str(row[2]).strip():
                        pickup_ready += 1

        # INBOUND_DONE
        main_sheet = spreadsheet.worksheet("inbound")
        main_data  = main_sheet.get_all_values()
        inbound_done = 0
        today_str = today.strftime("%Y-%m-%d")
        if len(main_data) > 1:
            for row in main_data[1:]:
                if len(row) >= 1 and str(row[0]).strip()[:10] == today_str:
                    inbound_done += 1

        return jsonify({
            "success": True,
            "pickup_ready": pickup_ready,
            "inbound_done": inbound_done
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/save", methods=["POST"])
def save_record():
    try:
        data = request.get_json()
        order_number = data.get("order_number", "")
        category     = data.get("category", "")
        vendor       = data.get("vendor", "")
        image_b64    = data.get("image_b64", "")

        if not order_number:
            return jsonify({"success": False, "error": "Order number required"}), 400
        if not image_b64:
            return jsonify({"success": False, "error": "Image required"}), 400

        # Upload to ImgBB
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": get_imgbb_key(), "image": image_b64},
            timeout=30
        )
        response.raise_for_status()
        image_url = response.json()["data"]["url"]

        # Save to Google Sheets
        client = get_gspread_client()
        spreadsheet = client.open_by_key(get_sheet_id())
        sheet = spreadsheet.worksheet("inbound")
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([date_now, order_number, category, vendor, image_url])

        return jsonify({"success": True, "image_url": image_url})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/history", methods=["GET"])
def get_history():
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(get_sheet_id())
        sheet = spreadsheet.worksheet("inbound")
        all_data = sheet.get_all_values()

        today_str = datetime.now().strftime("%Y-%m-%d")
        records = []
        if len(all_data) > 1:
            headers = all_data[0]
            for row in all_data[1:]:
                if len(row) >= 1 and str(row[0]).strip()[:10] == today_str:
                    record = {}
                    for j, header in enumerate(headers):
                        record[header] = row[j] if j < len(row) else ""
                    records.append(record)

        return jsonify({"success": True, "records": records})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
