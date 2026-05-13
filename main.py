from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
from collections import defaultdict
from datetime import datetime
import hashlib
import os
import httpx
import logging
import time

# ============================================================
# CONFIGURATION
# ============================================================

VALID_HASHES = os.environ.get(
    "STRATEGOS_HASHES",
    "2de9e046285e7a905067fbf736633ac5f85fdc8bf2e8ad868280459689c100b5"
).split(",")

ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "https://bigwiginfohub-wq.github.io"
).split(",")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 10

# ============================================================
# RATE LIMIT STORE
# ============================================================

rate_limit_store = defaultdict(list)

def check_rate_limit(client_ip: str) -> bool:
    now = time.time()

    rate_limit_store[client_ip] = [
        t for t in rate_limit_store[client_ip]
        if now - t < RATE_LIMIT_WINDOW
    ]

    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_MAX:
        return False

    rate_limit_store[client_ip].append(now)
    return True

# ============================================================
# APP SETUP
# ============================================================

app = FastAPI(
    title="Agent-Alpha-01",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer()

# ============================================================
# MODELS
# ============================================================

class VerifyRequest(BaseModel):
    passphrase: str = Field(..., min_length=8)

class ConstraintRegister(BaseModel):
    hard_limits: list[str] = Field(default_factory=list)
    soft_boundaries: list[str] = Field(default_factory=list)

    tradeoff_acceptance: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )

    routing_recommendation: str

    constraint_conflicts: list[dict] = Field(
        default_factory=list
    )

class AuditReport(BaseModel):
    audit_id: str

    integrity_score: float = Field(
        ...,
        ge=0,
        le=100
    )

    primary_driver: str = Field(
        ...,
        pattern="^(H1|H2|H3)$"
    )

    friction_score: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )

    mcl_coefficient: float = Field(
        ...,
        ge=0.0,
        le=1.0
    )

    boundary: str

    constraint_clarification: ConstraintRegister | None = None

    @validator("boundary")
    def verify_boundary_template(cls, v):
        required_phrase = "strictly within the locked window"

        if required_phrase not in v:
            raise ValueError(
                f"Boundary must contain: '{required_phrase}'"
            )

        return v

class AgentRequest(BaseModel):
    mission: str = Field(
        ...,
        min_length=10,
        max_length=2000
    )

    audit_report: AuditReport | None = None

class PromptRequest(BaseModel):
    mission: str
    audit_report: str | None = None

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def sanitize_for_prompt(text: str) -> str:
    text = text.replace("```", "`")
    return text[:5000]

def build_strategic_prompt(
    mission: str,
    audit_json: str | None,
    constraints: ConstraintRegister | None
) -> str:

    today = datetime.now().strftime("%Y-%m-%d")

    if constraints:
        if constraints.routing_recommendation == "Hypothesis-Only":
            framing = (
                "HIGH CONSTRAINT DENSITY: "
                "Provide hypothesis-level analysis only."
            )

        elif constraints.routing_recommendation == "Constrained Mode":
            framing = (
                "MODERATE CONSTRAINTS: "
                "Respect hard limits."
            )

        else:
            framing = (
                "FULL AUDIT MODE: "
                "Provide actionable strategic advice."
            )

    else:
        framing = "STANDARD MODE"

    audit_section = (
        f"\nAUDIT REPORT:\n{sanitize_for_prompt(audit_json)}"
        if audit_json
        else "\nAUDIT REPORT: None"
    )

    constraint_section = ""

    if constraints:
        constraint_section = f"""
HARD LIMITS:
{constraints.hard_limits}

SOFT BOUNDARIES:
{constraints.soft_boundaries}
"""

    return f"""
You are Agent-Alpha-01.

DATE: {today}

MISSION:
{sanitize_for_prompt(mission)}

{audit_section}

{constraint_section}

MODE:
{framing}

Ask the user:
"What is your next priority for this mission?"
"""

# ============================================================
# VERIFY ROUTE
# ============================================================

@app.post("/verify")
def verify(
    request: VerifyRequest,
    req: Request
):

    client_ip = req.client.host

    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded"
        )

    input_hash = hashlib.sha256(
        request.passphrase.encode()
    ).hexdigest()

    if input_hash not in VALID_HASHES:
        logger.warning(
            f"Failed verification from {client_ip}"
        )

        raise HTTPException(
            status_code=401,
            detail="ACCESS DENIED"
        )

    logger.info(
        f"Successful verification from {client_ip}"
    )

    return {
        "status": "VERIFIED",
        "message": "Access granted"
    }

# ============================================================
# AGENT ROUTE
# ============================================================

@app.post("/agent")
def agent(
    request: AgentRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY missing"
        )

    # SIMPLE TOKEN CHECK
    if credentials.credentials != "strategos-token":
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    constraints = (
        request.audit_report.constraint_clarification
        if request.audit_report
        else None
    )

    audit_json = (
        request.audit_report.model_dump_json()
        if request.audit_report
        else None
    )

    prompt = build_strategic_prompt(
        request.mission,
        audit_json,
        constraints
    )

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "messages": [
            {
                "role": "system",
                "content": "You are Agent-Alpha-01"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.3,
        "max_tokens": 1500
    }

    try:
        with httpx.Client(timeout=30.0) as client:

            response = client.post(
                url,
                json=payload,
                headers=headers
            )

            response.raise_for_status()

            data = response.json()

            advice = data["choices"][0]["message"]["content"]

            return {
                "advice": advice,
                "status": "success"
            }

    except Exception as e:
        logger.error(str(e))

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# ============================================================
# GENERATE PROMPT
# ============================================================

@app.post("/generate-prompt")
def generate_prompt(request: PromptRequest):

    try:
        audit_obj = (
            AuditReport.model_validate_json(
                request.audit_report
            )
            if request.audit_report
            else None
        )

        constraints = (
            audit_obj.constraint_clarification
            if audit_obj
            else None
        )

    except Exception:
        constraints = None

    prompt = build_strategic_prompt(
        request.mission,
        request.audit_report,
        constraints
    )

    return {
        "prompt": prompt
    }

# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "version": "1.1.0",
        "timestamp": datetime.now().isoformat()
    }

# ============================================================
# SCHEMA
# ============================================================

@app.get("/schema")
def get_schema():

    return {
        "audit_report": AuditReport.model_json_schema(),
        "constraint_register": ConstraintRegister.model_json_schema()
    }

# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )
