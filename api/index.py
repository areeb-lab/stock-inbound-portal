from flask import Flask, jsonify, request
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import requests
from datetime import datetime

app = Flask(__name__)

def get_sheets_client():
    creds_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    if not creds_json:
        raise Exception("GOOGLE_SERVICE_ACCOUNT_JSON not set")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=[
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ])
    return gspread.authorize(creds)

@app.route('/api/orders')
def get_orders():
    try:
        client = get_sheets_client()
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        spreadsheet = client.open_by_key(sheet_id)
        dump_sheet = spreadsheet.worksheet("Dump")
        
        order_numbers = dump_sheet.col_values(5)[1:]
        vendors = dump_sheet.col_values(54)[1:]
        categories = dump_sheet.col_values(90)[1:]
        
        orders = []
        for i, order in enumerate(order_numbers):
            if order and order.strip():
                orders.append({
                    "order": order.strip(),
                    "vendor": vendors[i] if i < len(vendors) else "",
                    "category": categories[i] if i < len(categories) else ""
                })
        
        return jsonify(orders)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scorecard')
def get_scorecard():
    try:
        client = get_sheets_client()
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        spreadsheet = client.open_by_key(sheet_id)
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        score_sheet = spreadsheet.worksheet("Score Card")
        dates = score_sheet.col_values(1)[1:]
        pickup_ready = sum(1 for d in dates if today in str(d))
        
        inbound_sheet = spreadsheet.worksheet("inbound")
        inbound_dates = inbound_sheet.col_values(1)[1:]
        inbound_done = sum(1 for d in inbound_dates if today in str(d))
        
        return jsonify({
            "pickup_ready": pickup_ready,
            "inbound_done": inbound_done
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/save', methods=['POST'])
def save_record():
    try:
        data = request.json
        order_number = data.get('order_number')
        category = data.get('category', '')
        vendor = data.get('vendor', '')
        image_base64 = data.get('image')
        
        imgbb_key = os.environ.get('IMGBB_API_KEY')
        img_response = requests.post(
            'https://api.imgbb.com/1/upload',
            data={'key': imgbb_key, 'image': image_base64}
        )
        image_url = img_response.json()['data']['url']
        
        client = get_sheets_client()
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        spreadsheet = client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("inbound")
        
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([date_now, order_number, category, vendor, image_url])
        
        return jsonify({"success": True, "image_url": image_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/history')
def get_history():
    try:
        client = get_sheets_client()
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        spreadsheet = client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("inbound")
        
        today = datetime.now().strftime("%Y-%m-%d")
        records = sheet.get_all_values()[1:]
        
        today_records = [
            {
                "date": r[0],
                "order": r[1],
                "category": r[2] if len(r) > 2 else "",
                "vendor": r[3] if len(r) > 3 else "",
                "image": r[4] if len(r) > 4 else ""
            }
            for r in records if today in r[0]
        ]
        
        return jsonify(today_records)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
