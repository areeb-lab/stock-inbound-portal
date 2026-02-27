from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import parse_qs, urlparse
from datetime import datetime

# Simple in-memory storage
records = []

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        if path == '/api/test' or path == '/':
            response = {"status": "ok", "message": "API is running!"}
        elif path == '/api/history':
            response = records
        elif path == '/api/orders':
            response = [
                {"order": "ORD001", "vendor": "Vendor A", "category": "Electronics"},
                {"order": "ORD002", "vendor": "Vendor B", "category": "Clothing"},
            ]
        elif path == '/api/scorecard':
            response = {"pickup_ready": len(records), "inbound_done": len(records)}
        else:
            response = {"status": "ok", "path": path}
        
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode())
        
        record = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "order": data.get('order_number', ''),
            "category": data.get('category', ''),
            "vendor": data.get('vendor', ''),
            "image": data.get('image', '')
        }
        records.append(record)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {"success": True}
        self.wfile.write(json.dumps(response).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
