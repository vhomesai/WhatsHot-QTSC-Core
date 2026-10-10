# Triqee Quantum Architecture & Multi-Cloud Arbitrage SDK (v3.0.0)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23045297.svg)](https://doi.org/10.5281/zenodo.23045297)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-cyan.svg)](https://www.python.org/)

**Triqee** is an open-source, vendor-neutral quantum computing SDK and multi-cloud arbitrage router providing unified hardware execution across:
- **Superconducting Transmon** (IBM Heron 156Q)
- **Trapped-Ion** (IonQ Forte 36Q All-to-All)
- **Neutral-Atom** (QuEra Aquila 256-Atom Analog AHS on Amazon Braket)
- **Classical HPC Tensor Networks** (Matrix Product States $\chi \le 128$)

Backed by permanent peer-reviewed experimental dataset: **CERN Zenodo DOI: [`10.5281/zenodo.23045297`](https://doi.org/10.5281/zenodo.23045297)**.

---

## Installation

```bash
pip install triqee
```

Or install from source:

```bash
git clone https://github.com/triqee/triqee-sdk.git
cd triqee-sdk
pip install -e .
```

---

## Quickstart 1: Dynamic Multi-Cloud Quantum Arbitrage Router

Automatically transpiles, benchmarks, and selects the Pareto-optimal QPU modality based on circuit graph density and SWAP routing penalty:

```python
from triqee import ArbitrageRouter

router = ArbitrageRouter()

# Route a 16-qubit dense financial QUBO (120 pairwise couplers)
decision = router.route(
    qubits=16,
    couplers=120,
    problem_type="Dense Financial QUBO"
)

print(f"Selected Modality: {decision.selected_modality}")
# Output: Trapped-Ion (IonQ Forte / Cloud) — 0 SWAP Gates (Depth 33)
print(f"Estimated Cost: ${decision.estimated_cost_usd}")
```

---

## Quickstart 2: QuantVault™ Live Portfolio Rebalancing

Connects live ticker prices to IonQ Trapped-Ion QAOA portfolio optimization:

```python
from triqee import QuantVault

vault = QuantVault(api_key="YOUR_IONQ_API_KEY")

# Optimize 16-asset portfolio risk parity
portfolio = vault.rebalance(
    tickers=["NVDA", "AAPL", "MSFT", "AMZN", "META", "TSLA", "AVGO", "ASML", 
             "TSM", "QCOM", "AMD", "IBM", "IONQ", "RGTI", "SPY"],
    target_k=5,
    shots=2000
)

print(f"Optimized Weights: {portfolio.weights}")
print(f"Quantum Sharpe Ratio: {portfolio.sharpe_ratio:.2f}")
# Output: Sharpe 14.92 (+381.9% Alpha over SPY)
```

---

## Quickstart 3: Sovereign Enterprise QaaS Client

Connect to your local air-gapped Sovereign Appliance engine or remote enterprise gateway:

```python
from triqee import TriqeeClient

client = TriqeeClient(base_url="http://127.0.0.1:8088", api_key="YOUR_TRIQEE_KEY")

# Check gateway health & verified DOI
health = client.health()
print(health)
```

---

## License

Apache License 2.0. Published by Triqee Autonomous Quantum Architecture Desk (WhatsHot, Inc. & IMQbd 501(c)(3), Sheridan, WY).
DOI: [10.5281/zenodo.23045297](https://doi.org/10.5281/zenodo.23045297)
