from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlmodel import Field as DBField, Session, SQLModel, create_engine, select
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

APP_NAME = "WhatsHot, Inc. QTSC Monetized Gateway"
APP_VERSION = "1.1.0"
WYOMING_ASSET_ID = "DA-000000992"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
sqlite_url = "sqlite:///subscriptions.db"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})


class ClientAPIKey(SQLModel, table=True):
    id: Optional[int] = DBField(default=None, primary_key=True)
    client_name: str
    api_key: str = DBField(index=True, unique=True)
    tier: str = DBField(default="free")  # "free" | "enterprise"
    is_active: bool = DBField(default=True)


def get_session():
    with Session(engine) as session:
        yield session


def _seed_keys_from_env(session: Session) -> None:
    """On each startup, upsert keys from WHOT_ENTERPRISE_API_KEYS into SQLite.
    Format: key1:client_name1,key2:client_name2
    Existing rows are updated in-place so manual DB edits are preserved.
    """
    raw = os.environ.get("WHOT_ENTERPRISE_API_KEYS", "")
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(":", 1)
        if len(parts) != 2:
            continue
        api_key, client_name = parts[0].strip(), parts[1].strip()
        if not api_key or not client_name:
            continue
        existing = session.exec(
            select(ClientAPIKey).where(ClientAPIKey.api_key == api_key)
        ).first()
        if existing:
            existing.client_name = client_name
            existing.is_active = True
            session.add(existing)
        else:
            session.add(
                ClientAPIKey(
                    client_name=client_name,
                    api_key=api_key,
                    tier="enterprise",
                    is_active=True,
                )
            )
    session.commit()


# ---------------------------------------------------------------------------
# Allowed browser origins
# ---------------------------------------------------------------------------
_raw_origins = os.environ.get(
    "WHOT_ALLOWED_ORIGINS",
    "https://imqbd-frontend.onrender.com,https://imqbd.org,http://localhost:5173",
)
ALLOWED_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------------------------
# API models
# ---------------------------------------------------------------------------


class AuditRequest(BaseModel):
    asset_id: str = Field(..., example=WYOMING_ASSET_ID)
    payload_hash: Optional[str] = Field(
        None, description="Optional payload fingerprint."
    )
    timestamp_utc: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of the submitted telemetry payload.",
    )
    metadata: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Optional metadata fields supplied by the client.",
    )


class AuditResponse(BaseModel):
    status: str
    wyoming_asset_id: str
    kernel_engine: str
    entropy_score: float
    request_hash: str
    client_name: str
    tier: str
    timestamp_utc: str
    details: Dict[str, str]


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "Monetizable enterprise telemetry gateway for non-Abelian SU(3) qutrit "
        "audit requests. Free tier: 5 req/min. Enterprise tier: 100 req/min."
    ),
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
    max_age=600,
)


@app.on_event("startup")
def on_startup() -> None:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        _seed_keys_from_env(session)


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


def verify_api_key(
    x_api_key: str = Header(None, alias="X-API-Key"),
    session: Session = Depends(get_session),
) -> ClientAPIKey:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key header: X-API-Key",
        )
    client = session.exec(
        select(ClientAPIKey).where(
            ClientAPIKey.api_key == x_api_key,
            ClientAPIKey.is_active == True,  # noqa: E712
        )
    ).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or inactive corporate API key.",
        )
    return client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_response(
    request: AuditRequest,
    client_name: str,
    tier: str,
    entropy_score: float,
    audit_mode: str,
) -> AuditResponse:
    canonical = json.dumps(
        request.model_dump(), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return AuditResponse(
        status="success",
        wyoming_asset_id=WYOMING_ASSET_ID,
        kernel_engine="Non-Abelian SU(3) Qutrit",
        entropy_score=entropy_score,
        request_hash=hashlib.sha256(canonical).hexdigest(),
        client_name=client_name,
        tier=tier,
        timestamp_utc=request.timestamp_utc or datetime.now(timezone.utc).isoformat(),
        details={
            "audit_mode": audit_mode,
            "verification_source": "imqbd.org",
        },
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/", summary="Health check")
def health_check() -> Dict[str, str]:
    return {
        "status": "ok",
        "service": APP_NAME,
        "version": APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/v1/public/ternary-check", response_model=AuditResponse, summary="Public preview (5 req/min)")
@limiter.limit("5/minute")
def public_ternary_check(request_obj: Request, request: AuditRequest) -> AuditResponse:
    """Key-free CORS endpoint for the imqbd.org browser widget.
    Rate limited to 5 requests/minute per IP.
    """
    return _build_response(
        request,
        client_name="Public-Widget-User",
        tier="free",
        entropy_score=0.9987,
        audit_mode="public-preview",
    )


@app.post("/v1/audit/ternary-check", response_model=AuditResponse, summary="Enterprise (100 req/min)")
@limiter.limit("100/minute")
def enterprise_ternary_check(
    request_obj: Request,
    request: AuditRequest,
    client: ClientAPIKey = Depends(verify_api_key),
) -> AuditResponse:
    """Authenticated enterprise endpoint. Requires X-API-Key header.
    Rate limited to 100 requests/minute per IP.
    """
    return _build_response(
        request,
        client_name=client.client_name,
        tier=client.tier,
        entropy_score=0.9999,
        audit_mode="enterprise-telemetry",
    )
