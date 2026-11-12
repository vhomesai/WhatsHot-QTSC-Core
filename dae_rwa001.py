"""RWA evidence gate. Offline, conservative: never auto-certify legal title."""
from dataclasses import dataclass
from hashlib import sha256
from datetime import datetime, timezone
from urllib.parse import urlparse

GATES = ("asset_existence", "holder_rights", "custody", "onchain_supply", "redemption", "assurance")
MATERIAL = frozenset(GATES[:5])
STATES = frozenset(("VERIFIED", "CLAIMED", "CONFLICTED", "UNKNOWN", "NOT_APPLICABLE"))

@dataclass(frozen=True)
class Evidence:
    gate: str
    status: str
    source_url: str = ""
    document_sha256: str = ""
    source_locator: str = ""
    observed_at: str = ""
    independent: bool = False

def digest(data: bytes) -> str:
    return sha256(data).hexdigest()

def _valid_url(url):
    p = urlparse(url)
    return p.scheme == "https" and bool(p.hostname) and not p.username and not p.password

def _valid_time(value):
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return t.tzinfo is not None and t.utcoffset() is not None
    except (TypeError, ValueError):
        return False

def evaluate(asset_id, records):
    if not asset_id:
        raise ValueError("asset_id required")
    if not all(isinstance(x, Evidence) for x in records):
        raise TypeError("records must be Evidence")
    grouped = {g: [] for g in GATES}
    for e in records:
        if e.gate not in grouped or e.status not in STATES:
            raise ValueError("invalid gate/status")
        grouped[e.gate].append(e)
    result = {}
    for gate, items in grouped.items():
        if any(e.status == "CONFLICTED" for e in items):
            result[gate] = "CONFLICTED"
        elif any(e.status == "VERIFIED" and e.independent and _valid_url(e.source_url)
                 and len(e.document_sha256) == 64
                 and all(c in "0123456789abcdef" for c in e.document_sha256.lower())
                 and bool(e.source_locator) and _valid_time(e.observed_at) for e in items):
            result[gate] = "EVIDENCE_PRESENT_REVIEW_REQUIRED"
        elif items:
            result[gate] = "UNVERIFIED"
        else:
            result[gate] = "UNKNOWN"
    if "CONFLICTED" in result.values():
        decision = "ESCALATE"
    elif all(result[g] == "EVIDENCE_PRESENT_REVIEW_REQUIRED" for g in MATERIAL):
        decision = "LEGAL_AND_CUSTODY_REVIEW_REQUIRED"
    else:
        decision = "INSUFFICIENT_EVIDENCE"
    return {"asset_id": asset_id, "gates": result, "decision": decision,
            "independent_legal_verification": False}
