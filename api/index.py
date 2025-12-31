import re
import time
import requests
from bs4 import BeautifulSoup
from user_agent import generate_user_agent
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Fragment Username Checker API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session = requests.Session()
session.headers.update({"User-Agent": generate_user_agent()})

DEVELOPER = "Paras Chourasiya / @Aotpy"
CHANNEL = "t.me/obitostuffs"
PORTFOLIO = "https://aotpy.vercel.app/"

def frag_api():
    try:
        r = session.get("https://fragment.com")
        soup = BeautifulSoup(r.text, 'html.parser')
        for script in soup.find_all("script"):
            if script.string and "apiUrl" in script.string:
                match = re.search(r'hash=([a-fA-F0-9]+)', script.string)
                if match:
                    return f"https://fragment.com/api?hash={match.group(1)}"
        return None
    except Exception:
        return None

def check_fgusername(username: str, retries=3):
    api_url = frag_api()
    if not api_url:
        return {"error": f"Could not get API URL for @{username}"}

    data = {"type": "usernames", "query": username, "method": "searchAuctions"}
    try:
        response = session.post(api_url, data=data).json()
    except Exception:
        if retries > 0:
            time.sleep(2)
            return check_fgusername(username, retries - 1)
        return {"error": "API request failed"}

    html_data = response.get("html")
    
    # If no HTML returned, username is not in Fragment database at all
    if not html_data:
        return {
            "username": username,
            "status": "Unknown",  # We don't know if it's taken or free
            "price": "N/A",
            "on_fragment": "No",
            "can_claim": "Unknown"  # We can't know without checking Telegram
        }

    soup = BeautifulSoup(html_data, 'html.parser')
    
    # Check if there's a "No usernames found" message
    no_results = soup.find("div", class_="table-cell-name")
    if no_results and "No usernames found" in no_results.get_text():
        return {
            "username": username,
            "status": "Not listed",  # Not on Fragment
            "price": "N/A",
            "on_fragment": "No",
            "can_claim": "Unknown"
        }
    
    elements = soup.find_all("div", class_="tm-value")
    if len(elements) < 3:
        # Not enough data to determine
        return {
            "username": username,
            "status": "Unknown",
            "price": "Unknown",
            "on_fragment": "No",
            "can_claim": "Unknown"
        }

    tag = elements[0].get_text(strip=True)
    price = elements[1].get_text(strip=True)
    raw_status = elements[2].get_text(strip=True)
    
    # Debug logging
    print(f"DEBUG: Username: {tag}, Price: {price}, Raw Status: {raw_status}")
    
    # CORRECT LOGIC:
    # Fragment shows "Available" when username is FOR SALE on Fragment
    # Fragment shows "Unavailable" when username exists but NOT FOR SALE on Fragment
    # If no results, username doesn't exist in Fragment database
    
    if raw_status.lower() == "available":
        # Username is FOR SALE on Fragment
        return {
            "username": tag,
            "status": "For Sale",  # Changed from "Available" to be clearer
            "price": price if price else "Unknown",
            "on_fragment": "Yes",
            "can_claim": "Yes"  # Can buy it on Fragment
        }
    elif raw_status.lower() == "unavailable":
        # Username exists but NOT FOR SALE on Fragment
        # This could be:
        # 1. Already taken on Telegram (not listed on Fragment)
        # 2. Or some other status on Fragment
        return {
            "username": tag,
            "status": "Not for Sale",  # Changed from "Not available"
            "price": "N/A",
            "on_fragment": "Yes",  # It's in Fragment DB but not for sale
            "can_claim": "No"  # Cannot buy it on Fragment
        }
    else:
        # Unknown status
        return {
            "username": tag,
            "status": raw_status,
            "price": price if price else "Unknown",
            "on_fragment": "Yes",
            "can_claim": "Unknown"
        }

@app.get("/")
async def root():
    return {
        "message": "Fragment Username Checker API",
        "developer": DEVELOPER,
        "channel": CHANNEL,
        "portfolio": PORTFOLIO,
        "endpoint": "GET /tobi?username=your_username",
        "example": "https://tobi-api-fragm.vercel.app/tobi?username=example"
    }

@app.get("/tobi")
async def check_username(username: str = Query(..., min_length=1)):
    username = username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="username is required")
    result = check_fgusername(username)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.exception_handler(404)
async def not_found(request: Request, exc: Exception):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "available_endpoints": ["/", "/tobi?username=xxx", "/api/health"]}
    )

app = app
