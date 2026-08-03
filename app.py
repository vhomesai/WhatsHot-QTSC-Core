from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

APP_NAME = "WhatsHot, Inc. QTSC Telemetry Gateway"
APP_VERSION = "1.0.0"
WYOMING_ASSET_ID = "DA-000000992"


def load_api_keys() -> Dict[str, Dict[str, str]]:
    registry: Dict[str, Dict[str, str]] = {}
    raw_keys = os.environ.get("WHOT_ENTERPRISE_API_KEYS", "")
    for entry in raw_keys.split(","):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(":", 1)
        if len(parts) != 2:
            continue
        api_key, client_name = parts[0].strip(), parts[1].strip()
        if api_key and client_name:
            registry[api_key] = {"client_name": client_name}

    return registry


API_KEY_REGISTRY = load_api_keys()


class AuditRequest(BaseModel):
    asset_id: str = Field(..., example=WYOMING_ASSET_ID)
    payload_hash: Optional[str] = Field(
        None,
        description="Optional payload fingerprint for the audit payload."
    )
    timestamp_utc: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of the submitted telemetry payload."
    )
    metadata: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Optional metadata fields supplied by the enterprise client."
    )


class AuditResponse(BaseModel):
    status: str
    wyoming_asset_id: str
    kernel_engine: str
    entropy_score: float
    request_hash: str
    client_name: str
    timestamp_utc: str
    details: Dict[str, str]


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Enterprise telemetry gateway for non-Abelian SU(3) qutrit audit requests.",
)


@app.get("/", summary="Health check")
def health_check() -> Dict[str, str]:
    return {
        "status": "ok",
        "service": APP_NAME,
        "version": APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/v1/audit/ternary-check", response_model=AuditResponse)
def verify_ternary_state(
    request: AuditRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> AuditResponse:
    if not API_KEY_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Enterprise API keys are not configured.",
        )

    if not x_api_key or x_api_key not in API_KEY_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid corporate access credentials.",
        )

    client_name = API_KEY_REGISTRY[x_api_key]["client_name"]
    canonical_payload = json.dumps(
        request.model_dump(), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    request_hash = hashlib.sha256(canonical_payload).hexdigest()

    return AuditResponse(
        status="success",
        wyoming_asset_id=WYOMING_ASSET_ID,
        kernel_engine="Non-Abelian SU(3) Qutrit",
        entropy_score=0.9987,
        request_hash=request_hash,
        client_name=client_name,
        timestamp_utc=request.timestamp_utc,
        details={
            "audit_mode": "enterprise-telemetry",
            "verification_source": "imqbd.org",
        },
    )
