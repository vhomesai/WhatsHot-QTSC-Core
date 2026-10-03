"""
Triqee Intelligence & Headline Taxonomy Engine
===============================================
Defines priority search taxonomy for scientific breakthroughs, hardware scaling,
compact edge sensing (SQUID/RF, NV diamond), on-device edge AI, and photonic computing.
"""

from typing import Dict, List, Any
import re

TAXONOMY_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "QUANTUM_RF_SENSING": {
        "label": "Quantum RF & SQUID Sensing (Speed / Wavelength Invariance)",
        "priority": "P0_CRITICAL",
        "keywords": [
            "quantum rf", "squid", "rf sensing", "superconducting sensor", "josephson",
            "sensemaking", "terahertz", "gigahertz", "magnetic flux", "monolayer", "mbe"
        ],
        "relevance": "Direct applicability to sub-nanosecond signal detection, size-independent compact antenna design, and Fourth State RF arbitrage."
    },
    "EDGE_QUANTUM_HARDWARE": {
        "label": "Compact & Room-Temperature Quantum Hardware (Size / Portability)",
        "priority": "P0_CRITICAL",
        "keywords": [
            "room temperature", "diamond", "nv center", "nitrogen vacancy", "solid state",
            "photonic chip", "waveguide", "optotensor", "micro-ring", "compact quantum",
            "wearable", "edge quantum", "swip", "mems"
        ],
        "relevance": "Key enabling technology for edge, low-power, or non-cryogenic consumer/device hardware form factors."
    },
    "EDGE_AI_AND_KERNEL_OPTIMIZATION": {
        "label": "High-Efficiency Edge AI & JIT Kernel Generation (Cost / Speed)",
        "priority": "P1_HIGH",
        "keywords": [
            "cuda kernel", "triton", "gpu kernel", "quantization", "ggml", "edge ai",
            "on-device", "recurrent memory", "lora", "sparse attention", "tiny model",
            "distillation", "npu", "apple silicon", "snapdragon", "latency reduction"
        ],
        "relevance": "Provides the low-cost, high-speed execution layer for running responsive intelligence on client machines and edge appliances."
    },
    "FAULT_TOLERANT_COMPILATION": {
        "label": "Fault-Tolerant Quantum Algorithms & qLDPC Surgery (Quantum Horizon)",
        "priority": "P1_HIGH",
        "keywords": [
            "qldpc", "surface code", "error correction", "fault tolerant", "logical qubit",
            "algebraic surgery", "qaoa", "hamiltonian", "transpiler", "swap reduction",
            "ibm heron", "ionq", "quera", "neutral atom"
        ],
        "relevance": "Maintains leadership in genuine multi-vendor QPU transpilation, benchmark reproducibility, and algorithm scaling."
    },
    "CONSUMER_DEVICE_INTEGRATION": {
        "label": "Form Factor & Device Integration (Ease of Use / Adoption)",
        "priority": "P2_MEDIUM",
        "keywords": [
            "wearable", "smart glasses", "edge device", "sensor fusion", "low power",
            "battery life", "ultra-wideband", "uwb", "ble", "bluetooth", "haptic"
        ],
        "relevance": "Ensures software stack can interface with consumer interfaces and portable hardware appliances."
    }
}


def evaluate_headline_relevance(text: str) -> Dict[str, Any]:
    """
    Evaluates a title, abstract, or article text against the Triqee Intelligence Taxonomy.

    Args:
        text: Raw text string to analyze.

    Returns:
        Structured evaluation with matched categories, priority level, and matched keywords.
    """
    if not text:
        return {"matched": False, "categories": []}

    text_lower = text.lower()
    matched_cats = []

    for cat_key, cat_data in TAXONOMY_CATEGORIES.items():
        matched_kws = [
            kw for kw in cat_data["keywords"]
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower)
        ]
        if matched_kws:
            matched_cats.append({
                "category_key": cat_key,
                "label": cat_data["label"],
                "priority": cat_data["priority"],
                "matched_keywords": matched_kws,
                "relevance_summary": cat_data["relevance"]
            })

    return {
        "matched": len(matched_cats) > 0,
        "match_count": len(matched_cats),
        "categories": matched_cats
    }
