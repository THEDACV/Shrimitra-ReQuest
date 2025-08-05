from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import httpx
import json
import os
from datetime import datetime
from pydantic import BaseModel
from typing import Dict, Any, Optional

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
HISTORY_FILE = "history.json"

class APIRequest(BaseModel):
    method: str
    url: str
    headers: Dict[str, str] = {}
    body: Optional[Any] = None

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

async def make_request(method, url, headers, body=None):
    async with httpx.AsyncClient() as client:
        try:
            headers.pop("Host", None)
            request_data = {
                "method": method.upper(),
                "url": url,
                "headers": headers,
                "timeout": 30.0
            }
            if body and method.upper() in ["POST", "PUT", "PATCH"]:
                request_data["json"] = body
            
            response = await client.request(**request_data)
            try:
                response_body = response.json()
            except ValueError:
                response_body = response.text
            
            return {
                "status": response.status_code,
                "headers": dict(response.headers),
                "body": response_body
            }
        except Exception as e:
            return {
                "status": 0,
                "headers": {},
                "body": {"error": str(e)}
            }

# Serve frontend HTML
@app.get("/")
async def get_frontend():
    try:
        with open("index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Frontend file not found")

# API Endpoints
@app.post("/send-request")
async def send_request(request: APIRequest):
    response = await make_request(
        request.method,
        request.url,
        request.headers,
        request.body
    )
    history = load_history()
    history.insert(0, {
        "id": str(datetime.now().timestamp()),
        "timestamp": datetime.now().isoformat(),
        "method": request.method,
        "url": request.url,
        "request": {
            "headers": request.headers,
            "body": request.body
        },
        "response": response
    })
    save_history(history)
    return response

@app.get("/history")
async def get_history():
    return load_history()

@app.delete("/history")
async def clear_history():
    save_history([])
    return {"message": "History cleared"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)