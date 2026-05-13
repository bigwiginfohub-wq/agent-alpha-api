from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import hashlib
import os
import httpx
from datetime import datetime

app = FastAPI(title="Agent Alpha API", version="1.0.0")

# CORS for dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Passphrase hashes for verification (Mode 2 and Mode 3)
# Mode 2: StrategOS passphrase
# Mode 3: DeltaFirst-StrategOS passphrase
VALID_HASHES = [
    "2de9e046285e7a905067fbf736633ac5f85fdc8bf2e8ad868280459689c100b5",  # KaronBeach2026
    "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",  # DeltaMode3
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
    return {
        "name": "Agent Alpha API",
        "version": "1.0.0",
        "description": "Verification and prompt generation for StrategOS and DeltaFirst-StrategOS",
        "endpoints": {
            "verify": "POST /verify",
            "agent": "POST /agent",
            "generate-prompt": "POST /generate-prompt",
            "health": "GET /health"
        }
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/verify")
def verify(request: VerifyRequest):
    """Verify passphrase for Mode 2 or Mode 3 access"""
    input_hash = hashlib.sha256(request.passphrase.encode()).hexdigest()
    if input_hash not in VALID_HASHES:
        raise HTTPException(status_code=401, detail="ACCESS DENIED")
    return {"status": "VERIFIED", "message": "Access granted"}

@app.post("/agent")
def agent(request: AgentRequest):
    """Generate strategic advice based on mission and optional audit report"""
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not set")
    
    # Build the system prompt with Fidelity Framework anchoring
    system_prompt = f"""You are Agent-Alpha-01, a strategic co-builder operating under the Fidelity Framework.

MISSION: {request.mission}

AUDIT REPORT: {request.audit_report if request.audit_report else "No audit report provided."}

PRINCIPLES:
1. Hold the anchor: Stay focused on the user's mission.
2. Detect drift: If the conversation goes off-topic, gently bring it back.
3. State boundaries: Be clear about what you cannot verify or know.
4. Log calibration: Note important decisions and corrections.
5. Be honest: If you don't know, say "I do not know."

METHODS AVAILABLE:
- Delta-First: Causal auditing (H₁/H₂/H₃, friction score, MCL coefficient)
- StrategOS: Mission-anchored strategic advice
- Fidelity Framework: Anchor Protocol, Calibration Log, Predisposition Standard

If the user pastes a JSON audit report, read it and use it to ground your advice.
If the user asks for strategic advice, provide actionable, evidence-based guidance.

BEGIN: Ask the user: "What is your next priority for this mission?""""

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Begin strategic session."}
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
    """Generate a strategic prompt for Mode 2 (StrategOS)"""
    mission = request.mission
    audit = request.audit_report or "No additional data provided."
    today = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""You are now Agent-Alpha-01, a strategic co-builder.

**ACTIVATION DATE:** {today}
**MISSION:** {mission}
**AUDIT/CONTEXT:** {audit}

**RULES:**
1. You are in STRATEGIC MODE. Do not engage in casual chat.
2. Anchor to the mission. If the user drifts, say: "Let us return to your mission: {mission}"
3. Provide strategic advice based on the audit/context. Be concise and actionable.
4. Use the Fidelity Framework: identify primary drivers, friction scores, and causal linkages.
5. State boundaries: what you cannot verify or know.
6. If the user pastes a JSON audit report, read it and ground your advice in its evidence.

**BEGIN:**
Ask the user: "What is your next priority for this mission?""""
    
    return {"prompt": prompt}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
