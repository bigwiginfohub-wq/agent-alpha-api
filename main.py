from datetime import datetime
from pydantic import BaseModel

class PromptRequest(BaseModel):
    mission: str
    audit_report: str = None

@app.post("/generate-prompt")
def generate_prompt(request: PromptRequest):
    # Note: In production, you would verify a session token here
    # For now, we assume the user has already verified via /verify
    
    mission = request.mission
    audit = request.audit_report or "No audit report provided."
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""You are now Agent-Alpha-01, a strategic co-builder.

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
Ask the user: "What is your next priority for this mission?""

    return {"prompt": prompt}
