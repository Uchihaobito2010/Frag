from http.server import BaseHTTPRequestHandler
import json
import httpx
import asyncio
from typing import Dict
import re

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "message": "Telegram Username Check API",
                "endpoints": {
                    "POST /api/check": "Check username availability",
                    "GET /": "API information"
                }
            }).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/api/check':
            content_length = int(self.headers['Content-Length'])
            post_data = self.read_content(content_length)
            
            try:
                data = json.loads(post_data)
                username = data.get('username', '')
                
                if not username:
                    self.send_error_response("Username is required", 400)
                    return
                
                # Run async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self.check_username(username))
                loop.close()
                
                self.send_success_response(result)
                
            except json.JSONDecodeError:
                self.send_error_response("Invalid JSON", 400)
            except Exception as e:
                self.send_error_response(f"Server error: {str(e)}", 500)
        else:
            self.send_response(404)
            self.end_headers()
    
    def read_content(self, content_length):
        return self.rfile.read(content_length).decode('utf-8')
    
    def send_success_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def send_error_response(self, message, code):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode())
    
    async def check_username(self, username: str) -> Dict:
        """Check username on Fragment and Telegram"""
        clean_username = username.replace('@', '').strip().lower()
        
        # Default response
        response = {
            "username": f"@{clean_username}",
            "status": "unknown",
            "price": "Unknown Ton",
            "can_claim": False,
            "message": "",
            "source": "unknown"
        }
        
        # Check Fragment first
        fragment_result = await self.check_fragment(clean_username)
        
        if fragment_result["status"] != "unknown":
            response.update(fragment_result)
        else:
            # Fallback to Telegram check
            telegram_result = await self.check_telegram(clean_username)
            response.update(telegram_result)
        
        return response
    
    async def check_fragment(self, username: str) -> Dict:
        """Check username on Fragment marketplace"""
        try:
            url = f"https://fragment.com/username/{username}"
            
            async with httpx.AsyncClient(
                timeout=10.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                }
            ) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    html_content = response.text
                    
                    # Parse HTML for status
                    status = "unknown"
                    price = "Unknown Ton"
                    can_claim = False
                    message = ""
                    
                    # Check for available username
                    if "Available" in html_content and "usernameTable" in html_content:
                        status = "fragment_available"
                        # Extract price using regex
                        price_match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*TON', html_content)
                        if price_match:
                            price = f"{price_match.group(1)} Ton"
                        
                        # Check if can be claimed
                        if "buy now" in html_content.lower() or "claim" in html_content.lower():
                            can_claim = True
                            message = "Buy link of fragment"
                        else:
                            message = "Available on Fragment"
                    
                    # Check for sold username
                    elif "Sold" in html_content or "Unavailable" in html_content:
                        status = "fragment_sold"
                        price_match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*TON', html_content)
                        if price_match:
                            price = f"{price_match.group(1)} Ton"
                        message = "Sold on Fragment"
                    
                    return {
                        "status": status,
                        "price": price,
                        "can_claim": can_claim,
                        "message": message,
                        "source": "fragment"
                    }
                
        except Exception as e:
            print(f"Fragment check error: {e}")
        
        return {"status": "unknown", "source": "fragment"}
    
    async def check_telegram(self, username: str) -> Dict:
        """Check username availability on Telegram"""
        try:
            url = f"https://t.me/{username}"
            
            async with httpx.AsyncClient(
                timeout=10.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            ) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    html_content = response.text
                    
                    # Check for "available" indicators
                    if "If you have Telegram, you can contact" in html_content:
                        return {
                            "status": "taken",
                            "price": "Unknown Ton",
                            "can_claim": False,
                            "message": "Username is taken on Telegram",
                            "source": "telegram"
                        }
                    else:
                        # Username might be available or page structure changed
                        return {
                            "status": "available",
                            "price": "N/A",
                            "can_claim": False,
                            "message": "May be available on Telegram",
                            "source": "telegram"
                        }
                
        except Exception as e:
            print(f"Telegram check error: {e}")
        
        return {"status": "unknown", "source": "telegram"}
