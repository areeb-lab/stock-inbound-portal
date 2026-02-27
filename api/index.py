from http.server import BaseHTTPRequestHandler
import json
import os
import gspread
from google.oauth2.service_account import Credentials
import requests
from datetime import datetime
from urllib.parse import parse_qs, urlparse

class handler(BaseHTTPRequestHandler):
    
    def get_sheets_client(self):
        creds_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if not creds_json:
            return None
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=[
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ])
        return gspread.authorize(creds)
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        try:
            if path == '/api/orders':
                self.handle_orders()
            elif path == '/api/scorecard':
                self.handle_scorecard()
            elif path == '/api/history':
                self.handle_history()
            elif path == '/api/test':
                self.send_json({"status": "ok", "message": "API Working!"})
            else:
                self.send_json({"status": "ok", "endpoints": ["/api/orders", "/api/scorecard", "/api/history", "/api/save"]})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def do_POST(self):
        path = urlparse(self.path).path
        
        try:
            if path == '/api/save':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode())
                self.handle_save(data)
            else:
                self.send_json({"error": "Not found"}, 404)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def handle_orders(self):
        client = self.get_sheets_client()
        if not client:
            self.send_json([])
            return
        
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
        
        self.send_json(orders)
    
    def handle_scorecard(self):
        client = self.get_sheets_client()
        if not client:
            self.send_json({"pickup_ready": 0, "inbound_done": 0})
            return
        
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        spreadsheet = client.open_by_key(sheet_id)
        
        today = datetime.now()
        today_formats = [
            today.strftime("%d-%b-%Y"),
            today.strftime("%Y-%m-%d"),
            today.strftime("%d/%m/%Y"),
        ]
        
        # Score Card count
        score_sheet = spreadsheet.worksheet("Score Card")
        score_data = score_sheet.get_all_values()[1:]
        pickup_ready = 0
        for row in score_data:
            if len(row) >= 3:
                date_val = str(row[0]).strip()
                if any(fmt in date_val for fmt in today_formats):
                    pickup_ready += 1
        
        # Inbound count
        inbound_sheet = spreadsheet.worksheet("inbound")
        inbound_data = inbound_sheet.get_all_values()[1:]
        inbound_done = 0
        for row in inbound_data:
            if len(row) >= 1:
                date_val = str(row[0]).strip()
                if any(fmt in date_val for fmt in today_formats):
                    inbound_done += 1
        
        self.send_json({"pickup_ready": pickup_ready, "inbound_done": inbound_done})
    
    def handle_history(self):
        client = self.get_sheets_client()
        if not client:
            self.send_json([])
            return
        
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        spreadsheet = client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("inbound")
        
        today = datetime.now().strftime("%Y-%m-%d")
        records = sheet.get_all_values()[1:]
        
        today_records = []
        for r in records:
            if today in str(r[0]):
                today_records.append({
                    "date": r[0] if len(r) > 0 else "",
                    "order": r[1] if len(r) > 1 else "",
                    "category": r[2] if len(r) > 2 else "",
                    "vendor": r[3] if len(r) > 3 else "",
                    "image": r[4] if len(r) > 4 else ""
                })
        
        self.send_json(today_records)
    
    def handle_save(self, data):
        order_number = data.get('order_number', '')
        category = data.get('category', '')
        vendor = data.get('vendor', '')
        image_base64 = data.get('image', '')
        
        # Upload to ImgBB
        image_url = ""
        imgbb_key = os.environ.get('IMGBB_API_KEY')
        if imgbb_key and image_base64:
            try:
                response = requests.post(
                    'https://api.imgbb.com/1/upload',
                    data={'key': imgbb_key, 'image': image_base64}
                )
                if response.status_code == 200:
                    image_url = response.json()['data']['url']
            except:
                pass
        
        # Save to Google Sheets
        client = self.get_sheets_client()
        if client:
            sheet_id = os.environ.get('GOOGLE_SHEET_ID')
            spreadsheet = client.open_by_key(sheet_id)
            sheet = spreadsheet.worksheet("inbound")
            date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([date_now, order_number, category, vendor, image_url])
        
        self.send_json({"success": True, "image_url": image_url})
