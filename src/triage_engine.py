"""
Triqee Inbound Message Triage & Classification Engine
======================================================
Deterministic rules-based parser for categorizing inbound inquiries,
validating inputs, and generating template responses.
"""

from typing import Dict, Any, List, Optional
import re
from datetime import datetime, timezone

CATEGORIES: Dict[str, Dict[str, Any]] = {
    "DEV_INQUIRY": {
        "keywords": ["github", "sdk", "qiskit", "cirq", "transpiler", "swap", "python", "install", "api key", "endpoint"],
        "default_tier": "Tier 1 Developer",
        "response_template": (
            "Thank you for contacting us. For developer and SDK access, visit "
            "https://www.triqee.com/airdrop to register your GitHub handle. "
            "To install the Python client locally: `pip install triqee`."
        )
    },
    "QUANT_INQUIRY": {
        "keywords": ["hedge fund", "sharpe", "alpha", "factor", "portfolio", "backtest", "bloomberg", "trading", "prop"],
        "default_tier": "Tier 2 Quant/Researcher",
        "response_template": (
            "Thank you for reaching out. Institutional quants and academic researchers "
            "can register for demonstration access at https://www.triqee.com/airdrop "
            "using an institutional email address."
        )
    },
    "LEGAL_UTILITY_INQUIRY": {
        "keywords": ["token", "utility", "sec", "security", "airdrop", "wyoming", "legal", "exchange", "compliance"],
        "default_tier": "Compliance Information",
        "response_template": (
            "$TQ is designed under Wyoming W.S. 34-29-106 as a consumptive utility token "
            "redeemable solely for compute services on the platform and confers no equity "
            "or profit participation rights."
        )
    },
    "ENTERPRISE_INQUIRY": {
        "keywords": ["defense", "doe", "darpa", "air-gapped", "sovereign", "on-prem", "fips", "scif", "enterprise"],
        "default_tier": "Enterprise / Federal Briefing",
        "response_template": (
            "For enterprise and on-premise deployments, please request an institutional briefing "
            "via the portal at https://www.triqee.com/portal or contact jon@triqee.com directly."
        )
    }
}


def classify_message(text: str) -> str:
    """
    Classifies an input text message into one of the standard inquiry categories.

    Args:
        text: Raw inbound message string.

    Returns:
        Category key (e.g., 'DEV_INQUIRY', 'QUANT_INQUIRY', etc.).
    """
    if not text or not isinstance(text, str):
        return "DEV_INQUIRY"

    text_lower = text.lower()
    for cat_name, data in CATEGORIES.items():
        for kw in data["keywords"]:
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                return cat_name

    return "DEV_INQUIRY"


def generate_triage_payload(
    user_handle: str,
    message_text: str,
    platform: str = "Web"
) -> Dict[str, Any]:
    """
    Constructs a structured triage dictionary ready for logging or transmission.

    Args:
        user_handle: Sender handle or email.
        message_text: Inbound content.
        platform: Originating platform (e.g., LinkedIn, X, Web).

    Returns:
        Structured response dictionary.
    """
    category = classify_message(message_text)
    cat_data = CATEGORIES[category]

    return {
        "user_handle": user_handle.strip(),
        "platform": platform.strip(),
        "category": category,
        "tier": cat_data["default_tier"],
        "suggested_response": cat_data["response_template"],
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    }
