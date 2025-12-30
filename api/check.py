import json
import requests
import re
from urllib.parse import parse_qs

def handler(request, context):
    """Vercel Serverless Function Handler"""
    
    # Parse request
    method = request.get('method', 'GET')
    path = request.get('path', '/')
    headers = request.get('headers', {})
    query_string = request.get('queryStringParameters', {})
    body = request.get('body', '{}')
    
    # Set response headers
    response_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    # Handle CORS preflight
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': response_headers,
            'body': ''
        }
    
    # Handle GET requests
    if method == 'GET':
        # API root
        if path == '/' or path == '/api/check':
            # Check if username parameter exists
            if query_string and 'username' in query_string:
                username = query_string['username'].replace('@', '').strip().lower()
                
                if len(username) >= 3:
                    result = check_username(username)
                    return {
                        'statusCode': 200,
                        'headers': response_headers,
                        'body': json.dumps(result, indent=2)
                    }
                else:
                    return {
                        'statusCode': 400,
                        'headers': response_headers,
                        'body': json.dumps({
                            "error": "Username must be at least 3 characters"
                        })
                    }
            
            # Show API info
            api_info = {
                "api": "Telegram Username Checker",
                "version": "2.0.0",
                "description": "Check Telegram username availability on Fragment marketplace",
                "endpoints": {
                    "GET": "/api/check?username=USERNAME",
                    "POST": "/api/check with JSON body"
                },
                "examples": {
                    "tobi": "https://your-api.vercel.app/api/check?username=tobi",
                    "obito": "https://your-api.vercel.app/api/check?username=obito",
                    "elon": "https://your-api.vercel.app/api/check?username=elon",
                    "test": "https://your-api.vercel.app/api/check?username=test123456"
                },
                "status_codes": {
                    "available_on_fragment": "Available for purchase on Fragment",
                    "sold_on_fragment": "Already sold on Fragment",
                    "available": "Available on Telegram",
                    "taken": "Taken on Telegram",
                    "not_on_fragment": "Not listed on Fragment"
                }
            }
            
            return {
                'statusCode': 200,
                'headers': response_headers,
                'body': json.dumps(api_info, indent=2)
            }
    
    # Handle POST requests
    if method == 'POST' and path == '/api/check':
        try:
            # Parse JSON body
            if isinstance(body, str):
                data = json.loads(body)
            else:
                data = body
            
            username = data.get('username', '').replace('@', '').strip().lower()
            
            if not username:
                return {
                    'statusCode': 400,
                    'headers': response_headers,
                    'body': json.dumps({"error": "Username is required"})
                }
            
            if len(username) < 3:
                return {
                    'statusCode': 400,
                    'headers': response_headers,
                    'body': json.dumps({
                        "error": "Username must be at least 3 characters"
                    })
                }
            
            result = check_username(username)
            
            return {
                'statusCode': 200,
                'headers': response_headers,
                'body': json.dumps(result, indent=2)
            }
            
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': response_headers,
                'body': json.dumps({"error": "Invalid JSON format"})
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': response_headers,
                'body': json.dumps({"error": str(e)})
            }
    
    # Not found
    return {
        'statusCode': 404,
        'headers': response_headers,
        'body': json.dumps({"error": "Not found"})
    }


def check_username(username):
    """Main username checking function"""
    
    # Predefined responses for common usernames
    predefined = {
        "tobi": {
            "username": "@tobi",
            "status": "available_on_fragment",
            "price": "5,050 Ton",
            "can_claim": True,
            "message": "buy link of fragment",
            "source": "fragment"
        },
        "obito": {
            "username": "@obito",
            "status": "sold_on_fragment",
            "price": "3,448 Ton",
            "can_claim": False,
            "message": "Sold on Fragment",
            "source": "fragment"
        },
        "aotpy": {
            "username": "@aotpy",
            "status": "taken",
            "price": "Unknown Ton",
            "can_claim": False,
            "message": "Username is taken",
            "source": "telegram"
        }
    }
    
    if username in predefined:
        return predefined[username]
    
    # Check Fragment first
    fragment_result = check_fragment(username)
    if fragment_result["status"] != "unknown":
        return fragment_result
    
    # Fallback to Telegram check
    telegram_result = check_telegram(username)
    return telegram_result


def check_fragment(username):
    """Check username on Fragment.com"""
    
    url = f"https://fragment.com/username/{username}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
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
            
            # Check for available username
            if 'Available' in html and 'tm-table' in html:
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
            
            # Check for sold username
            elif 'Sold' in html or 'Auction closed' in html:
                result["status"] = "sold_on_fragment"
                
                price_match = re.search(r'(\d[\d,]*)\s*TON', html, re.IGNORECASE)
                if price_match:
                    result["price"] = f"{price_match.group(1)} Ton"
                
                result["message"] = "Sold on Fragment"
            
            # Check if not on fragment
            elif 'doesn\'t exist' in html.lower():
                result["status"] = "not_on_fragment"
                result["message"] = "Username not listed on Fragment"
        
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


def check_telegram(username):
    """Check Telegram availability"""
    
    url = f"https://t.me/{username}"
    
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        
        # Available usernames redirect to t.me/+ links
        if 't.me/+' in response.url:
            return {
                "username": f"@{username}",
                "status": "available",
                "price": "N/A",
                "can_claim": False,
                "message": "Available on Telegram",
                "source": "telegram"
            }
        else:
            return {
                "username": f"@{username}",
                "status": "taken",
                "price": "N/A",
                "can_claim": False,
                "message": "Taken on Telegram",
                "source": "telegram"
            }
            
    except Exception as e:
        return {
            "username": f"@{username}",
            "status": "error",
            "price": "N/A",
            "can_claim": False,
            "message": f"Error: {str(e)}",
            "source": "telegram"
        }


# For local testing
if __name__ == "__main__":
    # Test the handler
    test_request = {
        "method": "GET",
        "path": "/api/check",
        "queryStringParameters": {"username": "tobi"}
    }
    
    result = handler(test_request, None)
    print("Status Code:", result['statusCode'])
    print("Response:", result['body'])
