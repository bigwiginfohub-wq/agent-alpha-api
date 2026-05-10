from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import hashlib
import os
import httpx
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Replace this with your actual passphrase hash
CORRECT_HASH = "2de9e046285e7a905067fbf736633ac5f85fdc8bf2e8ad868280459689c100b5"

# Groq API key from environment variable
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

class VerifyRequest(BaseModel):
    passphrase: str

class AgentRequest(BaseModel):
    mission: str
    audit_report: str = None

@app.get("/")
def root():
    return {"message": "Agent-Alpha-01 API is running (Groq backend)"}

@app.post("/verify")
def verify(request: VerifyRequest):
    input_hash = hashlib.sha256(request.passphrase.encode()).hexdigest()
    if input_hash != CORRECT_HASH:
        raise HTTPException(status_code=401, detail="ACCESS DENIED")
    return {"status": "VERIFIED", "message": "Access granted"}

@app.post("/agent")
def agent(request: AgentRequest):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not set")
    
    prompt = f"""You are Agent-Alpha-01, a strategic co-builder.

MISSION: {request.mission}

AUDIT REPORT: {request.audit_report}

Provide strategic advice based on the mission and audit report. Be concise and actionable."""
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "messages": [
            {"role": "system", "content": "You are Agent-Alpha-01, a strategic co-builder."},
            {"role": "user", "content": prompt}
        ],
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.7
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            advice = data["choices"][0]["message"]["content"]
            return {"advice": advice}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq API error: {str(e)}")
