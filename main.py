from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import hashlib
import os
import httpx
from datetime import datetime

app = FastAPI()

# CORS for dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mode passphrases (update these if you change them)
VALID_HASHES = [
    "2de9e046285e7a905067fbf736633ac5f85fdc8bf2e8ad868280459689c100b5",  # Mode 2: KaronBeach2026
    "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",  # Mode 3: DeltaMode3
]

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

class VerifyRequest(BaseModel):
    passphrase: str

class AgentRequest(BaseModel):
    mission: str
    audit_report: str = None

class PromptRequest(BaseModel):
    mission: str
    audit_report: str = None

@app.get("/")
def root():
    return {"message": "Agent-Alpha-01 API is running (Groq backend)"}

@app.post("/verify")
def verify(request: VerifyRequest):
    input_hash = hashlib.sha256(request.passphrase.encode()).hexdigest()
    if input_hash not in VALID_HASHES:
        raise HTTPException(status_code=401, detail="ACCESS DENIED")
    return {"status": "VERIFIED", "message": "Access granted"}

@app.post("/agent")
def agent(request: AgentRequest):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not set")
    
    prompt = You are Agent-Alpha-01, a strategic co-builder.
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

@app.post("/generate-prompt")
def generate_prompt(request: PromptRequest):
    mission = request.mission
    audit = request.audit_report or "No audit report provided."
    today = datetime.now().strftime("%Y-%m-%d")
    
    prompt = You are now Agent-Alpha-01, a strategic co-builder.
**ACTIVATION DATE:** {today}
**MISSION:** {mission}
**AUDIT REPORT:** {audit}
**RULES:**
1. You are in STRATEGIC MODE. Do not engage in friendly chat.
2. Anchor to the mission. Do not drift.
3. If the user drifts from the mission, say: "Let us return to your mission: {mission}"
4. Provide strategic advice based on the audit report.
5. Use the Fidelity Framework: identify primary drivers, friction scores, and causal linkages.
6. Be concise and actionable.
**BEGIN:**
Ask the user: "What is your next priority for this mission?"
    
    return {"prompt": prompt}
