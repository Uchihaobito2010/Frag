import json
import requests
import re
import time

def handler(request):
    """Main Vercel Serverless Function Handler"""
    
    # Set CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }
    
    # Handle OPTIONS (CORS preflight)
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    # Handle GET request (API info)
    if request.method == 'GET':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                "api": "Telegram Username Checker",
                "version": "1.0",
                "endpoint": "POST /api/check",
                "example": {
                    "request": {"username": "test"},
                    "response": {
                        "username": "@test",
                        "status": "available/taken/sold",
                        "price": "100 Ton",
                        "can_claim": False,
                        "message": "status message",
                        "source": "fragment"
                    }
                }
            })
        }
    
    # Handle POST request (check username)
    if request.method == 'POST':
        try:
            # Parse JSON body
            if hasattr(request, 'body'):
                body = json.loads(request.body)
            else:
                # For local testing
                body = request.get('body', {})
                if isinstance(body, str):
                    body = json.loads(body)
            
            username = body.get('username', '').replace('@', '').strip().lower()
            
            if not username or len(username) < 5:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({
                        "error": "Username must be at least 5 characters",
                        "username": f"@{username}" if username else ""
                    })
                }
            
            # Check username on Fragment
            result = check_fragment_username(username)
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(result)
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
                'body': json.dumps({"error": f"Server error: {str(e)}"})
            }
    
    # Method not allowed
    return {
        'statusCode': 405,
        'headers': headers,
        'body': json.dumps({"error": "Method not allowed"})
    }

def check_fragment_username(username):
    """Check if username is available on Fragment.com"""
    
    url = f"https://fragment.com/username/{username}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
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
            
            # Debug: Save HTML for analysis
            # with open(f"{username}.html", "w", encoding="utf-8") as f:
            #     f.write(html_content)
            
            # Check for available username
            if 'tm-table-cell tm-col-name' in html_content and 'Available' in html_content:
                result["status"] = "available_on_fragment"
                
                # Extract price using regex
                price_patterns = [
                    r'(\d{1,3}(?:,\d{3})*)\s*TON',
                    r'price-ton.*?>(\d[\d,]*)<',
                    r'(\d+)\s*Ton'
                ]
                
                for pattern in price_patterns:
                    match = re.search(pattern, html_content, re.IGNORECASE)
                    if match:
                        result["price"] = f"{match.group(1)} Ton"
                        break
                
                # Check if can be claimed
                if 'buy now' in html_content.lower() or 'tm-cell tm-cell-actions' in html_content:
                    result["can_claim"] = True
                    result["message"] = "buy link of fragment"
                else:
                    result["message"] = "Available on Fragment marketplace"
            
            # Check for sold username
            elif 'Sold' in html_content or 'Auction closed' in html_content:
                result["status"] = "sold_on_fragment"
                
                # Try to extract sold price
                price_match = re.search(r'(\d[\d,]*)\s*TON', html_content)
                if price_match:
                    result["price"] = f"{price_match.group(1)} Ton"
                
                result["message"] = "Username sold on Fragment"
            
            # Check if username exists but not on fragment
            elif 'not exist' in html_content.lower() or 'not found' in html_content.lower():
                result["status"] = "not_on_fragment"
                result["message"] = "Username not listed on Fragment"
            
            # Check if username is taken (has telegram link)
            elif f"https://t.me/{username}" in html_content:
                result["status"] = "taken"
                result["message"] = "Username is already taken"
            
            else:
                # If we can't determine, check Telegram directly
                telegram_result = check_telegram_direct(username)
                if telegram_result:
                    result.update(telegram_result)
                else:
                    result["status"] = "error"
                    result["message"] = "Could not determine status"
        
        elif response.status_code == 404:
            result["status"] = "not_found"
            result["message"] = "Username not found on Fragment"
        
        else:
            result["status"] = "error"
            result["message"] = f"Fragment returned status: {response.status_code}"
        
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

def check_telegram_direct(username):
    """Fallback: Check Telegram directly"""
    try:
        url = f"https://t.me/{username}"
        response = requests.head(url, timeout=5, allow_redirects=True)
        
        # Telegram redirects to https://t.me/+ for available usernames
        if response.url.startswith('https://t.me/+'):
            return {
                "status": "available",
                "price": "N/A",
                "can_claim": False,
                "message": "Available on Telegram",
                "source": "telegram"
            }
        else:
            return {
                "status": "taken",
                "price": "N/A",
                "can_claim": False,
                "message": "Taken on Telegram",
                "source": "telegram"
            }
    except:
        return None

# For local testing
if __name__ == "__main__":
    # Simulate a request
    test_request = {
        "httpMethod": "POST",
        "body": json.dumps({"username": "elonmusk"})
    }
    
    result = handler(test_request)
    print(json.dumps(json.loads(result['body']), indent=2))
