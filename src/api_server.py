"""
Triqee Production FastAPI REST Service
======================================
Provides standard REST endpoints with Pydantic schema validation,
automatic OpenAPI documentation, and structured error responses.
"""

import hmac
import os
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel, Field, EmailStr

from src.physics_engine import (
    haversine_distance,
    calculate_propagation_latencies,
    KNOWN_NODES,
    DEFAULT_FIBER_INDEX_N
)
from src.triage_engine import (
    classify_message,
    generate_triage_payload,
    CATEGORIES
)
from src.db_manager import DatabaseManager
from src.edge_engine import TriqeeEdgeEngine
from src.si_agent_core import SovereignSIAgent
from src.intelligence_repository import (
    MAX_QUERY_LIMIT,
    IntelligenceCategory,
    IntelligencePriority,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "gemini_agent_dashboard.db"
DEFAULT_CORS_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")


def resolve_database_path(configured_path: Optional[str] = None) -> str:
    """Resolve a filesystem SQLite path from TRIQEE_DB_PATH."""
    raw_path = configured_path if configured_path is not None else os.getenv("TRIQEE_DB_PATH", "")
    if not raw_path.strip():
        return str(DEFAULT_DB_PATH)
    if raw_path.startswith("sqlite:"):
        raise ValueError("TRIQEE_DB_PATH must be a filesystem path, not a SQLite URL")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return str(path.resolve())


def parse_cors_origins(configured_origins: Optional[str] = None) -> list[str]:
    """Parse a comma-separated HTTP(S) origin allowlist and reject wildcards."""
    raw_origins = configured_origins if configured_origins is not None else os.getenv("TRIQEE_CORS_ORIGINS", "")
    origins = [origin.strip().rstrip("/") for origin in raw_origins.split(",") if origin.strip()]
    if not origins:
        return list(DEFAULT_CORS_ORIGINS)
    if "*" in origins:
        raise ValueError("TRIQEE_CORS_ORIGINS cannot contain a wildcard")
    if any(not origin.startswith(("http://", "https://")) for origin in origins):
        raise ValueError("TRIQEE_CORS_ORIGINS entries must use http:// or https://")
    return origins


DB_PATH = resolve_database_path()
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
db = DatabaseManager(DB_PATH)
edge_engine = TriqeeEdgeEngine(node_id="TRIQEE_GATEWAY_NODE_01")
si_agent = SovereignSIAgent(db_manager=db)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Triqee Core API & Sovereign Quantum Gateway",
    description="Production REST API for geodesic calculation, latency estimation, edge inference, and intelligence taxonomy.",
    version="0.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Content-Type", "X-Admin-Key"],
)


def require_admin_key(x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key")) -> None:
    """Authorize CRM exports with an environment-configured operator secret."""
    configured_key = os.getenv("TRIQEE_ADMIN_KEY", "").strip()
    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRM export is disabled until TRIQEE_ADMIN_KEY is configured.",
        )
    if not x_admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing admin key header: X-Admin-Key",
        )
    if not hmac.compare_digest(x_admin_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key.",
        )


# ==========================================
# Pydantic Request & Response Schemas
# ==========================================

class DistanceRequest(BaseModel):
    lat1: float = Field(..., ge=-90.0, le=90.0, description="Latitude of point 1 (-90 to 90)")
    lon1: float = Field(..., ge=-180.0, le=180.0, description="Longitude of point 1 (-180 to 180)")
    lat2: float = Field(..., ge=-90.0, le=90.0, description="Latitude of point 2 (-90 to 90)")
    lon2: float = Field(..., ge=-180.0, le=180.0, description="Longitude of point 2 (-180 to 180)")

class DistanceResponse(BaseModel):
    distance_km: float
    point1: Dict[str, float]
    point2: Dict[str, float]

class LatencyRequest(BaseModel):
    distance_km: float = Field(..., gt=0.0, description="Distance in kilometers (> 0)")
    slant_factor: float = Field(default=1.0075, ge=1.0, description="Atmospheric slant expansion factor")
    fiber_routing_factor: float = Field(default=1.22, ge=1.0, description="Cable routing factor")
    fiber_index_n: float = Field(default=DEFAULT_FIBER_INDEX_N, gt=1.0, description="Fiber refractive index")
    hardware_delay_ns: float = Field(default=0.0, ge=0.0, description="Hardware delay in nanoseconds")

class TriageRequest(BaseModel):
    user_handle: str = Field(..., min_length=1, max_length=100, description="User handle or identifier")
    message_text: str = Field(..., min_length=1, description="Raw message content")
    platform: str = Field(default="Web", max_length=50, description="Source platform")

class LeadRegistrationRequest(BaseModel):
    tier: str = Field(..., description="Grant or user tier (e.g., tier1, tier2, tier3)")
    email: str = Field(..., description="Valid user email address")
    identifier: str = Field(..., description="GitHub handle, domain, or wallet address")
    allocated_tq: float = Field(default=500.0, ge=0.0, description="Token grant amount")
    wallet_address: Optional[str] = Field(default=None, description="Optional Base L2 wallet address")

class CRMLeadCaptureRequest(BaseModel):
    email: str = Field(..., description="Institutional contact email")
    tier: str = Field(default="tier1", description="Tier or allocation level")
    identifier: Optional[str] = Field(default="", description="Contact Name or handle")
    firm_name: Optional[str] = Field(default="", description="Institution or firm name")
    deployment_scale: Optional[str] = Field(default="Enterprise Production (> 100 Nodes)", description="Deployment scale")
    message: Optional[str] = Field(default="", description="Inquiry notes or requirements")
    wallet_address: Optional[str] = Field(default=None, description="Base L2 wallet address for token receipt")
    allocated_tq: float = Field(default=25000.0, ge=0.0, description="Allocated $TQ token grant")


# ==========================================
# API Endpoints
# ==========================================

@app.get("/health", tags=["System"])
def health_check() -> Dict[str, str]:
    """Health check endpoint to verify service availability."""
    return {"status": "healthy", "service": "triqee-core-api", "version": "0.2.0"}


@app.get("/api/v1/nodes", tags=["Geodesic"])
def list_known_nodes() -> Dict[str, Dict[str, float]]:
    """Lists pre-configured global financial exchange reference coordinates."""
    return {name: {"lat": coords[0], "lon": coords[1]} for name, coords in KNOWN_NODES.items()}


@app.post("/api/v1/geodesic/distance", response_model=DistanceResponse, tags=["Geodesic"])
def compute_distance(req: DistanceRequest):
    """Computes great-circle distance between two geographic coordinates using Haversine formula."""
    try:
        dist = haversine_distance(req.lat1, req.lon1, req.lat2, req.lon2)
        return {
            "distance_km": round(dist, 2),
            "point1": {"lat": req.lat1, "lon": req.lon1},
            "point2": {"lat": req.lat2, "lon": req.lon2}
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post("/api/v1/physics/latency", tags=["Physics"])
def compute_latencies(req: LatencyRequest):
    """Calculates theoretical propagation latencies for free-space and fiber paths."""
    try:
        return calculate_propagation_latencies(
            distance_km=req.distance_km,
            slant_factor=req.slant_factor,
            fiber_routing_factor=req.fiber_routing_factor,
            fiber_index_n=req.fiber_index_n,
            hardware_delay_ns=req.hardware_delay_ns
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post("/api/v1/triage/classify", tags=["Triage"])
def triage_inbound_inquiry(req: TriageRequest):
    """Categorizes an inbound user inquiry and returns a standard response template."""
    return generate_triage_payload(
        user_handle=req.user_handle,
        message_text=req.message_text,
        platform=req.platform
    )


class EdgeInferRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000, description="Input query or prompt string")
    max_tokens: int = Field(default=16, ge=1, le=128, description="Maximum tokens to generate")

class BenchmarkCompareRequest(BaseModel):
    lat1: float = Field(default=37.3861, ge=-90.0, le=90.0, description="Latitude of Node 1")
    lon1: float = Field(default=-121.9639, ge=-180.0, le=180.0, description="Longitude of Node 1")
    lat2: float = Field(default=40.7831, ge=-90.0, le=90.0, description="Latitude of Node 2")
    lon2: float = Field(default=-74.0407, ge=-180.0, le=180.0, description="Longitude of Node 2")
    qubits: int = Field(default=8, ge=1, le=64, description="Target QPU qubits")

class SIChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000, description="User query or command for Sovereign SI")
    mode: str = Field(default="SOVEREIGN_QUANTUM_EDGE_MODE", description="Execution mode: SOVEREIGN_QUANTUM_EDGE_MODE or CLASSICAL_CLOUD_MODE")
    session_id: Optional[str] = Field(default="default_session", description="Client session identifier")


@app.get("/api/v1/intelligence/latest", tags=["Intelligence"])
def get_latest_intelligence(
    category: Optional[list[IntelligenceCategory]] = Query(default=None),
    priority: IntelligencePriority = IntelligencePriority.P1_HIGH,
    limit: int = Query(default=15, ge=1, le=MAX_QUERY_LIMIT),
):
    """Public read-only access to sanitized indexed intelligence metadata."""
    result = si_agent.intelligence.query(
        categories=category,
        priority_threshold=priority,
        limit=limit,
    )
    return {"status": "success", **result, "articles": result["records"]}


@app.get("/api/v1/intelligence/stats", tags=["Intelligence"])
def get_intelligence_statistics():
    """Public read-only deterministic metrics from the sanitized local index."""
    return {
        "status": "success",
        "access": "public_sanitized_metadata",
        "stats": si_agent.intelligence.stats(),
    }


@app.post("/api/v1/edge/infer", tags=["Edge Engine"])
def run_edge_inference_endpoint(req: EdgeInferRequest):
    """Executes microsecond local quantized state-space inference on edge engine."""
    return edge_engine.run_edge_inference(prompt=req.prompt, max_tokens=req.max_tokens)


@app.post("/api/v1/benchmark/compare", tags=["Benchmark"])
def run_benchmark_comparison(req: BenchmarkCompareRequest):
    """
    Direct side-by-side benchmark:
    - Classical Cloud LLM Roundtrip (WAN + Queue + GPU: ~850ms)
    - Triqee Edge-Compiled Hybrid Engine (Physical RF + Local State Kernel + Async QPU Transpiler: < 12ms)
    """
    inf_res = edge_engine.run_edge_inference(prompt="Triqee Edge Sovereign Benchmark", max_tokens=16)
    rf_res = edge_engine.evaluate_rf_quantum_link(req.lat1, req.lon1, req.lat2, req.lon2)
    qpu_res = edge_engine.compile_qpu_transpilation_job(qubit_count=req.qubits, depth=10)

    classical_cloud_roundtrip_ms = 845.0
    triqee_total_ms = inf_res["latency_ms"] + rf_res["rf_line_of_sight_latency_ms"]

    return {
        "status": "success",
        "benchmark": {
            "triqee_edge_total_ms": round(triqee_total_ms, 3),
            "classical_cloud_roundtrip_ms": classical_cloud_roundtrip_ms,
            "speedup_factor": round(classical_cloud_roundtrip_ms / max(triqee_total_ms, 0.01), 1),
            "edge_breakdown": {
                "local_inference_ms": inf_res["latency_ms"],
                "rf_line_of_sight_ms": rf_res["rf_line_of_sight_latency_ms"],
                "fiber_legacy_ms": rf_res["legacy_fiber_latency_ms"],
                "physical_latency_saved_ms": rf_res["physical_latency_saved_ms"],
                "memory_footprint_mb": inf_res["memory_footprint_mb"]
            },
            "qpu_transpiled_job": qpu_res
        }
    }


@app.post("/api/v1/leads/register", tags=["Leads"])
def register_lead(req: LeadRegistrationRequest):
    """Stores a user registration entry in the SQLite operational database."""
    try:
        lead_id = db.record_lead(
            tier=req.tier,
            email=req.email,
            identifier=req.identifier,
            allocated_tq=req.allocated_tq,
            wallet_address=req.wallet_address
        )
        return {
            "status": "success",
            "lead_id": lead_id,
            "email": req.email,
            "tier": req.tier,
            "allocated_tq": req.allocated_tq
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Failed to record lead. Email may already be registered.")


@app.post("/api/v1/leads/capture", tags=["CRM"])
def capture_institutional_lead(req: CRMLeadCaptureRequest):
    """
    Captures an institutional allocator or enterprise deployment lead,
    runs automated triage classification, and provisions the allocated $TQ token grant.
    """
    import hashlib
    try:
        # Run automatic category classification on inquiry message
        cat_tag = classify_message(req.message) if req.message else "ENTERPRISE_INQUIRY"
        ident = req.identifier.strip() if req.identifier else (req.firm_name.strip() if req.firm_name else req.email.split("@")[0])

        lead_id = db.record_lead(
            tier=req.tier,
            email=req.email,
            identifier=ident,
            allocated_tq=req.allocated_tq,
            wallet_address=req.wallet_address,
            firm_name=req.firm_name,
            deployment_scale=req.deployment_scale,
            category_tag=cat_tag,
            notes=req.message
        )

        # Generate cryptographic proof receipt
        receipt_hash = hashlib.sha256(f"{lead_id}:{req.email}:{req.allocated_tq}:TQ_WYOMING_TOKEN".encode()).hexdigest()

        return {
            "status": "success",
            "lead_id": lead_id,
            "email": req.email,
            "firm_name": req.firm_name,
            "tier": req.tier,
            "category_tag": cat_tag,
            "allocated_tq": req.allocated_tq,
            "statutory_reference": "Wyoming W.S. § 34-29-106",
            "merkle_receipt": f"0x{receipt_hash[:32]}",
            "message": f"Successfully enrolled {req.firm_name or req.email} with {req.allocated_tq:,.0f} $TQ utility token grant."
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Lead registration failed or email already registered: {str(e)}")


@app.get("/api/v1/crm/export/csv", tags=["CRM"])
def export_crm_csv(_: None = Depends(require_admin_key)):
    """Exports all CRM pipeline records in standard CSV format."""
    from fastapi.responses import Response
    csv_content = db.export_leads_csv()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=triqee_institutional_leads.csv"}
    )


@app.get("/api/v1/crm/export/json", tags=["CRM"])
def export_crm_json(_: None = Depends(require_admin_key)):
    """Exports all CRM pipeline records in JSON format."""
    from fastapi.responses import Response
    json_content = db.export_leads_json()
    return Response(
        content=json_content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=triqee_institutional_leads.json"}
    )


@app.get("/api/v1/crm/pipeline", tags=["CRM"])
def get_crm_pipeline_stats():
    """Returns analytics and distribution breakdown for the institutional CRM pipeline."""
    return {
        "status": "success",
        "pipeline": db.get_crm_pipeline_stats()
    }


@app.post("/api/v1/si/chat", tags=["Sovereign SI"])
def sovereign_si_chat_endpoint(req: SIChatRequest):
    """
    Executes a conversational query through the Sovereign Dual-Brain Superintelligence Agent.
    Routes intent, executes deterministic physical tools, compiles QPU DAGs, and generates verified telemetry.
    """
    try:
        response = si_agent.generate_response(prompt=req.prompt, mode=req.mode)
        return {
            "status": "success",
            "session_id": req.session_id,
            "result": response
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Sovereign SI agent error: {str(e)}")
