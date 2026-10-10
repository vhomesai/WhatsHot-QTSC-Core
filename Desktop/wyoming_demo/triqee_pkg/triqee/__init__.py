"""
Triqee Sovereign Quantum Architecture & Multi-Cloud QPU Arbitrage SDK
Version: 3.1.0
DOI: 10.5281/zenodo.23045297
Integrated with Google Gemini 4 Argon Co-Processor
"""

__version__ = "3.1.0"
__author__ = "Jon Vierk & CAO Trixee"
__doi__ = "10.5281/zenodo.23045297"

from .router import ArbitrageRouter, RoutingDecision
from .quantvault import QuantVault, PortfolioResult
from .client import TriqeeClient, GeminiArgonClient

# Alias Client to TriqeeClient for convenience
Client = TriqeeClient
from .gemini_argon import (
    GeminiArgonTranspiler,
    GeminiArgonAlphaEngine,
    GeminiArgonCyberShield,
    GEMINI_ARGON_SPECS,
    ArgonTranspileResult,
    ArgonAlphaResult,
    ArgonCyberDefenseResult
)

__all__ = [
    "ArbitrageRouter",
    "RoutingDecision",
    "QuantVault",
    "PortfolioResult",
    "TriqeeClient",
    "GeminiArgonClient",
    "GeminiArgonTranspiler",
    "GeminiArgonAlphaEngine",
    "GeminiArgonCyberShield",
    "GEMINI_ARGON_SPECS",
    "ArgonTranspileResult",
    "ArgonAlphaResult",
    "ArgonCyberDefenseResult",
    "__version__",
    "__doi__"
]
