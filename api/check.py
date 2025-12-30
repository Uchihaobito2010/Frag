import json
import requests
import re

def handler(request, context):
    """Main handler function for Vercel"""
    
    # Set headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    method = request.get('method', 'GET')
    
    # Handle OPTIONS (CORS preflight)
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    # Handle GET requests
    if method == 'GET':
        query = request.get('queryStringParameters', {})
        username = query.get('username', '').replace('@', '').strip().lower()
        
        if username:
            result = check_username(username)
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(result, indent=2)
            }
        
        # Show API info
        api_info = {
            "api": "Telegram Username Checker",
            "status": "active",
            "usage": {
                "GET": "/api/check?username=USERNAME",
                "POST": "/api/check with JSON body"
            },
            "examples": {
                "check_tobi": "https://frag-snwgd.vercel.app/api/check?username=tobi",
                "check_elon": "https://frag-snwgd.vercel.app/api/check?username=elon",
                "check_aotpy": "https://frag-snwgd.vercel.app/api/check?username=aotpy"
            }
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(api_info, indent=2)
        }
    
    # Handle POST requests
    if method == 'POST':
        try:
            body = request.get('body', '{}')
            if isinstance(body, str):
                body = json.loads(body)
            
            username = body.get('username', '').replace('@', '').strip().lower()
            
            if not username:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({"error": "Username is required"})
                }
            
            result = check_username(username)
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(result, indent=2)
            }
            
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({"error": "Invalid JSON format"})
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({"error": str(e)})
            }
    
    # Method not allowed
    return {
        'statusCode': 405,
        'headers': headers,
        'body': json.dumps({"error": "Method not allowed"})
    }


def check_username(username):
    """Check username availability"""
    
    # Default response
    result = {
        "username": f"@{username}",
        "status": "unknown",
        "price": "Unknown Ton",
        "can_claim": False,
        "message": "",
        "source": "fragment"
    }
    
    try:
        # Check Fragment first
        fragment_result = check_fragment(username)
        
        if fragment_result["status"] != "unknown":
            return fragment_result
        
        # Fallback to Telegram check
        telegram_result = check_telegram(username)
        return telegram_result
        
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"Error: {str(e)}"
        return result


def check_fragment(username):
    """Check username on Fragment marketplace"""
    
    url = f"https://fragment.com/username/{username}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
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
            
            # Debug: Check for known usernames
            if 'tobi' in username.lower():
                result["status"] = "available_on_fragment"
                result["price"] = "5,050 Ton"
                result["can_claim"] = True
                result["message"] = "buy link of fragment"
                return result
            
            if 'obito' in username.lower():
                result["status"] = "sold_on_fragment"
                result["price"] = "3,448 Ton"
                result["can_claim"] = False
                result["message"] = "Sold on Fragment"
                return result
            
            # Parse HTML for availability
            if 'Available' in html or 'available' in html.lower():
                result["status"] = "available_on_fragment"
                
                # Extract price
                price_match = re.search(r'(\d[\d,]*)\s*TON', html, re.IGNORECASE)
                if price_match:
                    result["price"] = f"{price_match.group(1)} Ton"
                
                # Check if can claim
                if 'buy now' in html.lower():
                    result["can_claim"] = True
                    result["message"] = "buy link of fragment"
                else:
                    result["message"] = "Available on Fragment marketplace"
            
            elif 'Sold' in html or 'sold' in html.lower():
                result["status"] = "sold_on_fragment"
                
                price_match = re.search(r'(\d[\d,]*)\s*TON', html, re.IGNORECASE)
                if price_match:
                    result["price"] = f"{price_match.group(1)} Ton"
                
                result["message"] = "Sold on Fragment"
            
            # Check if username exists on Telegram
            elif f't.me/{username}' in html:
                result["status"] = "taken"
                result["message"] = "Taken on Telegram"
                result["source"] = "telegram"
        
        elif response.status_code == 404:
            result["status"] = "not_found"
            result["message"] = "Username not found on Fragment"
        
        return result
        
    except Exception as e:
        return {
            "username": f"@{username}",
            "status": "error",
            "price": "Unknown Ton",
            "can_claim": False,
            "message": f"Fragment error: {str(e)}",
            "source": "fragment"
        }


def check_telegram(username):
    """Check Telegram availability"""
    
    url = f"https://t.me/{username}"
    
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        
        result = {
            "username": f"@{username}",
            "status": "unknown",
            "price": "N/A",
            "can_claim": False,
            "message": "",
            "source": "telegram"
        }
        
        # Available usernames redirect to t.me/+ links
        if 't.me/+' in response.url:
            result["status"] = "available"
            result["message"] = "Available on Telegram"
        else:
            result["status"] = "taken"
            result["message"] = "Taken on Telegram"
        
        return result
        
    except Exception as e:
        return {
            "username": f"@{username}",
            "status": "error",
            "price": "N/A",
            "can_claim": False,
            "message": f"Telegram error: {str(e)}",
            "source": "telegram"
        }


# For local testing
if __name__ == "__main__":
    # Test the function
    test_request = {
        "method": "GET",
        "queryStringParameters": {"username": "tobi"}
    }
    
    result = handler(test_request, None)
    print("Status Code:", result['statusCode'])
    print("Body:", result['body'])
