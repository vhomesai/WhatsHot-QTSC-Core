"""Read-only Token Terminal disclosure evidence validation. No network or signing."""
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse
import json

class Status(str, Enum):
    VERIFIED = "VERIFIED"
    CLAIMED = "CLAIMED"
    CONFLICTED = "CONFLICTED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"

@dataclass(frozen=True)
class Claim:
    asset_id: str
    field: str
    value: str
    vendor_source: str
    primary_source: str = ""
    primary_value: str = ""
    checked_at: str = ""

def _https(url):
    p = urlparse(url)
    return p.scheme == "https" and bool(p.netloc) and not p.username and not p.password

def evaluate(claim: Claim):
    if not claim.asset_id or not claim.field:
        raise ValueError("asset_id and field required")
    if not claim.value:
        status = Status.UNKNOWN
    elif not _https(claim.vendor_source):
        status = Status.UNKNOWN
    elif not claim.primary_source or not claim.primary_value or not claim.checked_at:
        status = Status.CLAIMED
    elif not _https(claim.primary_source):
        status = Status.CLAIMED
    elif claim.value.strip().casefold() != claim.primary_value.strip().casefold():
        status = Status.CONFLICTED
    else:
        status = Status.VERIFIED
    return {"asset_id": claim.asset_id, "field": claim.field, "status": status.value,
            "vendor_source": claim.vendor_source, "primary_source": claim.primary_source,
            "checked_at": claim.checked_at}

def evaluate_fixture(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("expected a list of claims")
    return [evaluate(Claim(**item)) for item in data]
