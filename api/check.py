from http.server import BaseHTTPRequestHandler
from http import HTTPStatus
import json
import requests
import re

class handler(BaseHTTPRequestHandler):
    """Vercel Serverless Function Handler"""
    
    def do_OPTIONS(self):
        self.send_response(HTTPStatus.OK)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/api/check' or self.path == '/':
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "api": "Telegram Username Checker",
                "version": "1.0",
                "description": "Check Telegram username availability on Fragment",
                "endpoints": {
                    "POST /api/check": "Check username availability",
                    "parameters": {
                        "username": "Telegram username (with or without @)"
                    }
                },
                "example": {
                    "request": {"username": "testuser"},
                    "response": {
                        "username": "@testuser",
                        "status": "available_on_fragment",
                        "price": "5,050 Ton",
                        "can_claim": False,
                        "message": "Available on Fragment marketplace",
                        "source": "fragment"
                    }
                }
            }
            
            self.wfile.write(json.dumps(response, indent=2).encode())
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/api/check':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                username = data.get('username', '').replace('@', '').strip()
                
                if not username:
                    self.send_error_response("Username is required", HTTPStatus.BAD_REQUEST)
                    return
                
                # Check username
                result = self.check_fragment_username(username)
                
                self.send_response(HTTPStatus.OK)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                self.wfile.write(json.dumps(result, indent=2).encode())
                
            except json.JSONDecodeError:
                self.send_error_response("Invalid JSON", HTTPStatus.BAD_REQUEST)
            except Exception as e:
                self.send_error_response(f"Server error: {str(e)}", HTTPStatus.INTERNAL_SERVER_ERROR)
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()
    
    def send_error_response(self, message, status_code):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        error_response = {
            "error": message,
            "status": "error"
        }
        
        self.wfile.write(json.dumps(error_response).encode())
    
    def check_fragment_username(self, username):
        """Check username on Fragment.com"""
        url = f"https://fragment.com/username/{username}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            # Default response
            result = {
                "username": f"@{username}",
                "status": "unknown",
                "price": "Unknown Ton",
                "can_claim": False,
                "message": "",
                "source": "fragment"
            }
            
            if response.status_code == 200:
                html_content = response.text
                
                # Debug: Save sample HTML
                # with open('debug.html', 'w', encoding='utf-8') as f:
                #     f.write(html_content)
                
                # Check patterns
                if 'tm-table-cell tm-col-name' in html_content and 'Available' in html_content:
                    result["status"] = "available_on_fragment"
                    
                    # Extract price
                    price_match = re.search(r'(\d[\d,]*) TON', html_content, re.IGNORECASE)
                    if price_match:
                        result["price"] = f"{price_match.group(1)} Ton"
                    
                    # Check if can claim
                    if 'buy now' in html_content.lower():
                        result["can_claim"] = True
                        result["message"] = "buy link of fragment"
                    else:
                        result["message"] = "Available on Fragment marketplace"
                
                elif 'Sold' in html_content or 'unavailable' in html_content:
                    result["status"] = "sold_on_fragment"
                    
                    price_match = re.search(r'(\d[\d,]*) TON', html_content, re.IGNORECASE)
                    if price_match:
                        result["price"] = f"{price_match.group(1)} Ton"
                    
                    result["message"] = "Sold on Fragment"
                
                elif 'not exist' in html_content.lower():
                    result["status"] = "not_on_fragment"
                    result["message"] = "Username not listed on Fragment"
                
                else:
                    # Try Telegram direct check
                    telegram_status = self.check_telegram_direct(username)
                    if telegram_status == "available":
                        result["status"] = "available"
                        result["message"] = "Available on Telegram"
                        result["source"] = "telegram"
                    elif telegram_status == "taken":
                        result["status"] = "taken"
                        result["message"] = "Username is taken"
                        result["source"] = "telegram"
                    else:
                        result["status"] = "error"
                        result["message"] = "Could not determine status"
            
            elif response.status_code == 404:
                result["status"] = "not_found"
                result["message"] = "Username not found on Fragment"
            
            return result
            
        except requests.exceptions.Timeout:
            return {
                "username": f"@{username}",
                "status": "error",
                "price": "Unknown Ton",
                "can_claim": False,
                "message": "Request timeout",
                "source": "fragment"
            }
        except Exception as e:
            return {
                "username": f"@{username}",
                "status": "error",
                "price": "Unknown Ton",
                "can_claim": False,
                "message": f"Error: {str(e)}",
                "source": "fragment"
            }
    
    def check_telegram_direct(self, username):
        """Simple Telegram availability check"""
        try:
            # Check if t.me/username redirects
            url = f"https://t.me/{username}"
            response = requests.head(url, allow_redirects=True, timeout=5)
            
            # If redirects to t.me/+ link, username is available
            if '+http' in str(response.url) or 't.me/+' in str(response.url):
                return "available"
            else:
                return "taken"
        except:
            return "unknown"
