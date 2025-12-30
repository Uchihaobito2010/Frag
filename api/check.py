from http.server import BaseHTTPRequestHandler
import json
import requests
import re

async def handler(request, response):
    """Vercel Serverless Function Handler - MUST be async"""
    
    # Set CORS headers
    response.headers['Content-Type'] = 'application/json'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    
    # Handle OPTIONS (CORS preflight)
    if request.method == 'OPTIONS':
        response.status(200)
        return
    
    # Handle GET requests
    if request.method == 'GET':
        # Get username from query parameter
        username = request.query.get('username', '').replace('@', '').strip().lower()
        
        if username and len(username) >= 3:
            result = await check_fragment_username(username)
            response.status(200).send(json.dumps(result, indent=2))
            return
        
        # Show API info if no username
        api_info = {
            "api": "Telegram Username Checker",
            "version": "1.4.0",
            "endpoints": {
                "GET": "/api/check?username=USERNAME",
                "POST": "/api/check with JSON body"
            },
            "examples": {
                "tobi": "https://frag-snwgd.vercel.app/api/check?username=tobi",
                "elon": "https://frag-snwgd.vercel.app/api/check?username=elon",
                "aotpy": "https://frag-snwgd.vercel.app/api/check?username=aotpy"
            }
        }
        response.status(200).send(json.dumps(api_info, indent=2))
        return
    
    # Handle POST requests
    if request.method == 'POST':
        try:
            body = await request.json()
            username = body.get('username', '').replace('@', '').strip().lower()
            
            if not username or len(username) < 3:
                response.status(400).send(json.dumps({
                    "error": "Username must be at least 3 characters"
                }))
                return
            
            result = await check_fragment_username(username)
            response.status(200).send(json.dumps(result, indent=2))
            
        except json.JSONDecodeError:
            response.status(400).send(json.dumps({"error": "Invalid JSON"}))
        except Exception as e:
            response.status(500).send(json.dumps({"error": str(e)}))
        return
    
    # Method not allowed
    response.status(405).send(json.dumps({"error": "Method not allowed"}))


async def check_fragment_username(username):
    """Check username on Fragment.com"""
    
    url = f"https://fragment.com/username/{username}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    try:
        # Use async requests if possible, or sync with thread pool
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        def sync_request():
            return requests.get(url, headers=headers, timeout=15)
        
        with ThreadPoolExecutor() as executor:
            response = await asyncio.get_event_loop().run_in_executor(executor, sync_request)
        
        # Parse response
        result = {
            "username": f"@{username}",
            "status": "unknown",
            "price": "Unknown Ton",
            "can_claim": False,
            "message": "",
            "source": "fragment"
        }
        
        if response.status_code == 200:
            html = response.text
            
            # Check for available username on Fragment
            if 'tm-value font-nowrap' in html and ('Available' in html or 'available' in html.lower()):
                result["status"] = "available_on_fragment"
                
                # Extract price
                price_match = re.search(r'(\d[\d,]*)\s*<small>TON</small>', html)
                if price_match:
                    result["price"] = f"{price_match.group(1)} Ton"
                else:
                    # Alternative pattern
                    price_match = re.search(r'(\d[\d,]*)\s*TON', html, re.IGNORECASE)
                    if price_match:
                        result["price"] = f"{price_match.group(1)} Ton"
                
                # Check if can claim
                if 'buy now' in html.lower():
                    result["can_claim"] = True
                    result["message"] = "buy link of fragment"
                else:
                    result["message"] = "Available on Fragment marketplace"
            
            # Check for sold
            elif 'Sold' in html or 'sold' in html.lower():
                result["status"] = "sold_on_fragment"
                
                price_match = re.search(r'(\d[\d,]*)\s*TON', html, re.IGNORECASE)
                if price_match:
                    result["price"] = f"{price_match.group(1)} Ton"
                
                result["message"] = "Sold on Fragment"
            
            # Check if not on fragment
            elif 'doesn\'t exist' in html.lower():
                # Check Telegram
                telegram_status = await check_telegram_direct(username)
                if telegram_status == "available":
                    result["status"] = "available"
                    result["message"] = "Available on Telegram"
                    result["source"] = "telegram"
                elif telegram_status == "taken":
                    result["status"] = "taken"
                    result["message"] = "Taken on Telegram"
                    result["source"] = "telegram"
                else:
                    result["status"] = "not_on_fragment"
                    result["message"] = "Username not listed on Fragment"
            
            # Check Telegram link
            elif f't.me/{username}' in html:
                result["status"] = "taken"
                result["message"] = "Taken on Telegram"
                result["source"] = "telegram"
        
        elif response.status_code == 404:
            # Check Telegram
            telegram_status = await check_telegram_direct(username)
            if telegram_status == "available":
                result["status"] = "available"
                result["message"] = "Available on Telegram"
                result["source"] = "telegram"
            elif telegram_status == "taken":
                result["status"] = "taken"
                result["message"] = "Taken on Telegram"
                result["source"] = "telegram"
            else:
                result["status"] = "not_found"
                result["message"] = "Username not found"
        
        return result
        
    except Exception as e:
        return {
            "username": f"@{username}",
            "status": "error",
            "price": "Unknown Ton",
            "can_claim": False,
            "message": f"Error: {str(e)}",
            "source": "fragment"
        }


async def check_telegram_direct(username):
    """Check Telegram availability"""
    try:
        url = f"https://t.me/{username}"
        
        def sync_check():
            return requests.head(url, timeout=5, allow_redirects=True)
        
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        with ThreadPoolExecutor() as executor:
            response = await asyncio.get_event_loop().run_in_executor(executor, sync_check)
        
        if 't.me/+' in response.url:
            return "available"
        else:
            return "taken"
    except:
        return "unknown"


# For local testing
if __name__ == "__main__":
    # This won't run on Vercel, only for local testing
    import asyncio
    
    async def test():
        # Simulate a request
        class MockRequest:
            method = 'GET'
            query = {'username': 'tobi'}
        
        class MockResponse:
            def __init__(self):
                self.headers = {}
                self.status_code = 200
            
            def status(self, code):
                self.status_code = code
                return self
            
            def send(self, data):
                print(data)
        
        req = MockRequest()
        res = MockResponse()
        
        await handler(req, res)
    
    asyncio.run(test())
