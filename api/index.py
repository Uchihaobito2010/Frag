from http.server import BaseHTTPRequestHandler
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            "api": "Telegram Username Checker",
            "version": "1.0.0",
            "endpoints": {
                "GET /api": "This information",
                "POST /api/check": "Check username availability",
                "parameters": {
                    "username": "Telegram username (with or without @)"
                }
            },
            "example_request": {
                "method": "POST",
                "url": "/api/check",
                "body": {"username": "aotpy"}
            },
            "example_response": {
                "username": "@aotpy",
                "status": "taken",
                "price": "Unknown Ton",
                "can_claim": False,
                "message": "Username is taken",
                "source": "telegram"
            }
        }
        
        self.wfile.write(json.dumps(response, indent=2).encode())
