# Triqee Core Package

A Python library and REST API service for geodesic distance calculations, latency modeling, and inbound message classification.

---

## Installation

```bash
# Clone the repository
git clone https://github.com/vhomesai/WhatsHot-QTSC-Core.git
cd WhatsHot-QTSC-Core

# Install package in editable mode
pip install -e .

# Install development & test dependencies
pip install -e ".[dev]"
```

---

## Quickstart

### 1. Python Library Usage

```python
from src.physics_engine import haversine_distance, calculate_propagation_latencies
from src.triage_engine import generate_triage_payload

# Compute geodesic distance (Chicago to Tokyo)
dist_km = haversine_distance(41.8781, -87.6298, 35.6762, 139.6503)
print(f"Distance: {dist_km:.2f} km")

# Calculate theoretical propagation latency
latency = calculate_propagation_latencies(dist_km)
print(f"Free-space one-way latency: {latency['free_space_one_way_ms']} ms")
print(f"Subsea fiber latency: {latency['fiber_one_way_ms']} ms")

# Triage an inbound developer inquiry
triage = generate_triage_payload("@dev_user", "How do I install the SDK via python?")
print(f"Category: {triage['category']}")
```

### 2. Launching the REST API Service

```bash
# Start the FastAPI server with hot-reload
uvicorn src.api_server:app --host 127.0.0.1 --port 8000 --reload
```

Interactive OpenAPI documentation will be available at:
* Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### Runtime configuration

| Variable | Purpose | Default |
| :--- | :--- | :--- |
| `TRIQEE_DB_PATH` | SQLite filesystem path; Docker Compose uses `/app/data/operational.db` on its persistent volume | `gemini_agent_dashboard.db` in the project root |
| `TRIQEE_CORS_ORIGINS` | Comma-separated HTTP(S) browser-origin allowlist; wildcards are rejected | `http://localhost:3000,http://127.0.0.1:3000` |
| `TRIQEE_ADMIN_KEY` | Operator secret required in `X-Admin-Key` for CRM CSV/JSON exports | Unset; exports fail closed with HTTP 503 |

The self-contained cockpit prompts for the CRM operator key for each export and does not persist it. Set `TRIQEE_ADMIN_KEY` in the environment before starting Docker Compose; never place it in the HTML.

---

## Testing & CI

```bash
# Run the authoritative test and coverage gate
python -m pytest tests test_app.py test_anchor_metadata.py test_anchor_metadata_extra.py \
  -q --cov=src --cov-report=term-missing --cov-fail-under=100
```
