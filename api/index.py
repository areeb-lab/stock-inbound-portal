from flask import Flask, jsonify, request, send_from_directory
import json
import os
import requests
from datetime import datetime

app = Flask(__name__)

# In-memory storage (for demo - data will reset on redeploy)
stock_data = []

@app.route('/')
def home():
    return send_from_directory('../public', 'index.html')

@app.route('/api/orders')
def get_orders():
    try:
        # Demo orders - replace with your actual data later
        orders = [
            {"order": "ORD001", "vendor": "Vendor A", "category": "Electronics"},
            {"order": "ORD002", "vendor": "Vendor B", "category": "Clothing"},
            {"order": "ORD003", "vendor": "Vendor C", "category": "Food"},
        ]
        return jsonify(orders)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/scorecard')
def get_scorecard():
    try:
        return jsonify({
            "pickup_ready": len(stock_data),
            "inbound_done": len(stock_data)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/save', methods=['POST'])
def save_record():
    try:
        data = request.json
        record = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "order": data.get('order_number', ''),
            "category": data.get('category', ''),
            "vendor": data.get('vendor', ''),
            "image": ""
        }
        
        # Upload image to ImgBB if provided
        image_base64 = data.get('image')
        if image_base64:
            imgbb_key = os.environ.get('IMGBB_API_KEY', '')
            if imgbb_key:
                img_response = requests.post(
                    'https://api.imgbb.com/1/upload',
                    data={'key': imgbb_key, 'image': image_base64}
                )
                if img_response.status_code == 200:
                    record["image"] = img_response.json()['data']['url']
        
        stock_data.append(record)
        return jsonify({"success": True, "image_url": record["image"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/history')
def get_history():
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        today_records = [r for r in stock_data if today in r["date"]]
        return jsonify(today_records)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# For Vercel
app = app
