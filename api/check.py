from http.server import BaseHTTPRequestHandler
import json
import requests
import re
import time

def handler(request, context):
    """Vercel Serverless Function"""
    
    # Parse request
    method = request.get('method', 'GET')
    query_string = request.get('queryStringParameters', {})
    raw_body = request.get('body', '{}')
    
    # Headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    }
    
    # Handle GET
    if method == 'GET':
        if query_string and 'username' in query_string:
            username = query_string['username'].replace('@', '').strip().lower()
            
            if username and len(username) >= 3:
                result = check_fragment_username_v2(username)
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps(result, indent=2)
                }
    
    # Handle POST
    if method == 'POST':
        try:
            if isinstance(raw_body, str):
                body_data = json.loads(raw_body)
            else:
                body_data = raw_body
            
            username = body_data.get('username', '').replace('@', '').strip().lower()
            
            if not username or len(username) < 3:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({
                        "error": "Username must be at least 3 characters"
                    })
                }
            
            result = check_fragment_username_v2(username)
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(result, indent=2)
            }
            
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({"error": str(e)})
            }
    
    # API Info
    api_info = {
        "api": "Telegram Username Checker",
        "version": "1.3.0",
        "update": "Fixed Fragment parsing",
        "test_usernames": {
            "tobi": "https://frag-snwgd.vercel.app/api/check?username=tobi",
            "elon": "https://frag-snwgd.vercel.app/api/check?username=elon",
            "aotpy": "https://frag-snwgd.vercel.app/api/check?username=aotpy"
        }
    }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(api_info, indent=2)
    }

def check_fragment_username_v2(username):
    """Improved Fragment checking with better parsing"""
    
    url = f"https://fragment.com/username/{username}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        # Default result
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
            
            # Debug - save HTML for analysis
            # with open(f'{username}.html', 'w', encoding='utf-8') as f:
            #     f.write(html)
            
            # Check for "Available" status (new Fragment structure)
            if 'tm-value font-nowrap' in html and ('Available' in html or 'available' in html.lower()):
                result["status"] = "available_on_fragment"
                
                # Extract price - multiple patterns
                price_patterns = [
                    r'tm-value[^>]*>([^<]+)',
                    r'(\d[\d,]*)\s*<small>TON</small>',
                    r'(\d[\d,]*)\s*TON',
                    r'price[^>]*>([^<]+)'
                ]
                
                for pattern in price_patterns:
                    match = re.search(pattern, html)
                    if match:
                        price = match.group(1).strip()
                        if price and price[0].isdigit():
                            result["price"] = f"{price} Ton"
                            break
                
                # Check if can be purchased
                if 'buy now' in html.lower() or 'purchase' in html.lower():
                    result["can_claim"] = True
                    result["message"] = "buy link of fragment"
                else:
                    result["message"] = "Available on Fragment marketplace"
            
            # Check for "Sold" status
            elif 'Sold' in html or 'sold' in html.lower():
                result["status"] = "sold_on_fragment"
                
                # Extract sold price
                price_match = re.search(r'(\d[\d,]*)\s*(?:TON|Ton)', html, re.IGNORECASE)
                if price_match:
                    result["price"] = f"{price_match.group(1)} Ton"
                
                result["message"] = "Sold on Fragment"
            
            # Check if username doesn't exist on fragment (404 or not found)
            elif 'doesn\'t exist' in html.lower() or 'not found' in html.lower():
                # Check Telegram directly
                telegram_status = check_telegram_direct(username)
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
            
            # If none of the above, check for Telegram link
            elif f'https://t.me/{username}' in html:
                # Still check if it's available on fragment
                if 'tm-table' in html or 'usernametable' in html:
                    result["status"] = "available_on_fragment"
                    result["message"] = "Available on Fragment (has Telegram profile)"
                else:
                    result["status"] = "taken"
                    result["message"] = "Username is taken on Telegram"
                    result["source"] = "telegram"
            
            else:
                # Fallback: Check page title
                title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE)
                if title_match:
                    title = title_match.group(1)
                    if 'available' in title.lower():
                        result["status"] = "available_on_fragment"
                        result["message"] = "Available (detected from title)"
                    elif 'sold' in title.lower():
                        result["status"] = "sold_on_fragment"
                        result["message"] = "Sold (detected from title)"
                
                # Final fallback
                if result["status"] == "unknown":
                    telegram_status = check_telegram_direct(username)
                    if telegram_status == "available":
                        result["status"] = "available"
                        result["message"] = "Available on Telegram"
                        result["source"] = "telegram"
                    elif telegram_status == "taken":
                        result["status"] = "taken"
                        result["message"] = "Taken on Telegram"
                        result["source"] = "telegram"
        
        elif response.status_code == 404:
            # Fragment returns 404 for usernames not on marketplace
            telegram_status = check_telegram_direct(username)
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
                result["message"] = "Username not found on Fragment"
        
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

def check_telegram_direct(username):
    """Direct Telegram availability check"""
    try:
        url = f"https://t.me/{username}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
        
        # Available usernames redirect to t.me/+ links
        if 't.me/+' in response.url:
            return "available"
        else:
            return "taken"
    except:
        return "unknown"

# For testing specific usernames
def test_usernames():
    """Test specific usernames"""
    test_cases = [
        "tobi",      # Should be available_on_fragment
        "elon",      # Should be taken
        "aotpy",     # Should be taken  
        "verylongtestusername123456",  # Should be available
        "test123"    # Should be available
    ]
    
    for username in test_cases:
        print(f"\nChecking @{username}:")
        result = check_fragment_username_v2(username)
        print(f"Status: {result['status']}")
        print(f"Price: {result['price']}")
        print(f"Message: {result['message']}")

if __name__ == "__main__":
    # Run tests
    test_usernames()
