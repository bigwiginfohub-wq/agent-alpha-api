from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import hashlib
import os
import httpx
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow requests from anywhere (for testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# The correct hash for the passphrase (replace with your actual hash)
CORRECT_HASH = "2de9e046285e7a905067fbf736633ac5f85fdc8bf2e8ad868280459689c100b5"

# Your Gemini API key (set in Railway environment variables)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

class VerifyRequest(BaseModel):
    passphrase: str

class AgentRequest(BaseModel):
    mission: str
    audit_report: str = None

@app.get("/")
def root():
    return {"message": "Agent-Alpha-01 API is running"}

@app.post("/verify")
def verify(request: VerifyRequest):
    input_hash = hashlib.sha256(request.passphrase.encode()).hexdigest()
    if input_hash != CORRECT_HASH:
        raise HTTPException(status_code=401, detail="ACCESS DENIED")
    return {"status": "VERIFIED", "message": "Access granted"}

@app.post("/agent")
def agent(request: AgentRequest):
    # In a real implementation, you would verify a session token here
    # For simplicity, we are skipping session verification
    
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")
    
    prompt = f"""You are Agent-Alpha-01, a strategic co-builder.

MISSION: {request.mission}

AUDIT REPORT: {request.audit_report}

Provide strategic advice based on the mission and audit report. Be concise and actionable."""
    
    # Call Gemini API
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            advice = data["candidates"][0]["content"]["parts"][0]["text"]
            return {"advice": advice}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")