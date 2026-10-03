# Triqee Core Package

A Python library and REST API service for geodesic distance calculations, latency modeling, and inbound message classification.

---

## Installation

```bash
# Clone the repository
git clone https://github.com/vhomesai/WhatsHot-QTSC-Core.git
cd WhatsHot-QTSC-Core

# Install package in editable mode
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .

# Install development & test dependencies
python -m pip install pytest==8.4.2 pytest-cov==7.0.0 httpx==0.27.2 PyYAML==6.0.3
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

The public cockpit never receives or requests the CRM operator key. CRM exports are
operator-only API operations and must be performed by trusted server-side tooling.
Never place `TRIQEE_ADMIN_KEY` in the HTML, an image build argument, or a committed
environment file.

---

## Deterministic multi-vendor QPU planning

The vendor-neutral planner supports two typed 48-logical-qubit workloads:

- QAOA portfolio-risk circuits with configurable `p` depth from 1 through 8,
  a typed 48-asset return/covariance instance, coefficient-weighted cost
  rotations, cardinality penalty, mixers, and complete Z-basis readout.
- A defined toy qLDPC-like syndrome-extraction benchmark with 36 data qubits,
  12 ancillas, explicit stabilizer support, and physically correct X/Z check
  extraction. It does not claim a named code, distance, threshold, or correction
  capability.

IBM Heron plans target 156 physical qubits and Heavy-Hex connectivity. Rigetti
Ankaa plans target 84 physical qubits and square-lattice tunable couplers. Both
use interaction-aware placement, deterministic shortest-path SWAP routing, and
dependency-safe parallel scheduling, with an identity-placement baseline and a
non-regression fallback.

IonQ Forte has 36 algorithmic qubits, so a 48-qubit circuit is never represented
as an intact execution. The planner emits a deterministic 36+12 capacity
diagnostic, identifies every crossing interaction, and reports zero topology
SWAPs. It then fails closed with `UNSUPPORTED_EXACT_CIRCUIT_CUTTING`: no gate is
deleted and no fragment depth, experiment multiplier, or submission-ready plan
is claimed until an independently sampled density-matrix/process-tensor
reconstruction is implemented.

Generate the representative plan/deployment report with:

```bash
python scripts/generate_transpilation_deployment_report.py
```

See
[`TRANSPILATION_DEPLOYMENT_REPORT.md`](TRANSPILATION_DEPLOYMENT_REPORT.md) for
exact deterministic metrics and the explicit no-hardware-execution boundary.

---

## Live intelligence index

The SI agent seeds and queries a local SQLite index from the sanitized,
deterministic `src/data/intelligence_seed.json` artifact. The public read-only
endpoints `GET /api/v1/intelligence/latest` and
`GET /api/v1/intelligence/stats` expose only public research metadata and
provenance; no mailbox identifiers, private bodies, credentials, or database
paths are returned. Filters use canonical category/priority enums, and “live”
means each response queries current indexed state—not that a mailbox or network
scanner runs at startup. See `LIVE_INTELLIGENCE_REPORT.md` for the authoritative
source audit, the authorized five-record distribution, and the explicit
mismatch with the unverified 21-record claim.

---

## Production deployment

The bundle runs `src.api_server:app` behind Caddy and exposes only Caddy. Caddy
obtains and renews certificates automatically and serves the zero-CDN cockpit at
`https://www.triqee.com/cockpit`. The API and SQLite network are internal.

### Prerequisites and DNS

1. Install Docker Engine with the Compose v2 plugin.
2. Create public `A` and/or `AAAA` records for `www.triqee.com` pointing to the
   deployment host.
3. Permit inbound TCP 80 and TCP/UDP 443. Do **not** expose port 8000.
4. Ensure outbound HTTPS and DNS are available so Caddy can issue certificates.

Set the administrator secret only in the process environment (or inject it from
your host secret manager). Compose intentionally has no secret value or default:

```bash
export TRIQEE_ADMIN_KEY="$(openssl rand -base64 48)"
docker compose config --quiet
docker compose up -d --build
docker compose ps
curl --fail --show-error https://www.triqee.com/health
curl --fail --show-error https://www.triqee.com/api/health
curl --fail --show-error https://www.triqee.com/cockpit >/dev/null
```

For PowerShell, use
`$env:TRIQEE_ADMIN_KEY = [Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }))`
before the same `docker compose` commands. Production CORS is fixed to
`https://www.triqee.com`; wildcard origins are never used.

The API and Caddy run as non-root users with read-only root filesystems,
`no-new-privileges`, dropped capabilities (except Caddy's low-port bind
capability), bounded temporary filesystems, health checks, and automatic restart.
`triqee_data` contains SQLite state and `caddy_data` contains certificate state.

### Backup and restore

Use SQLite's online backup command so a live WAL/transaction cannot produce an
inconsistent copy:

```bash
mkdir -p backups
docker compose exec -T api python -c "import sqlite3; s=sqlite3.connect('/app/data/operational.db'); d=sqlite3.connect('/tmp/backup.db'); s.backup(d); d.close(); s.close()"
docker compose cp api:/tmp/backup.db ./backups/operational-$(date +%Y%m%d-%H%M%S).db
```

Restore during a maintenance window (replace the example filename). Keeping the
API process up allows SQLite to perform a transactional restore while Caddy is
stopped so no requests can reach it:

```bash
docker compose stop caddy
cat ./backups/operational-20260101-120000.db | docker compose exec -T api python -c "import sqlite3,sys; p='/tmp/restore.db'; open(p,'wb').write(sys.stdin.buffer.read()); s=sqlite3.connect(p); d=sqlite3.connect('/app/data/operational.db'); s.backup(d); d.close(); s.close()"
docker compose start caddy
curl --fail --show-error https://www.triqee.com/health
```

Keep backups encrypted with access controls appropriate for CRM data. Back up
the `caddy_data` volume separately only if retaining ACME account state is
required; certificates can otherwise be reissued.

### Health, upgrades, and rollback

`docker compose ps` reports both container health checks. The public `/health`
route checks the actual API through Caddy; a healthy response is JSON containing
`"status":"healthy"`. `/api/health` provides the equivalent same-origin API
health route. View failures with `docker compose logs --tail=200 api caddy`.

Before an upgrade, create a database backup and record the current Git revision
and image IDs (`git rev-parse HEAD` and `docker compose images`). Deploy with
`docker compose up -d --build` and verify both URLs above. To roll back:

```bash
git checkout <previous-reviewed-revision>
export TRIQEE_ADMIN_KEY='<value-from-secret-manager>'
docker compose up -d --build
# Restore the pre-upgrade database only when the release changed its schema.
curl --fail --show-error https://www.triqee.com/health
```

Do not use `docker compose down -v` during normal deployment or rollback: `-v`
permanently removes the SQLite and Caddy volumes.

---

## Testing & CI

```bash
# Run the authoritative test and coverage gate
python -m pytest tests test_app.py test_anchor_metadata.py test_anchor_metadata_extra.py \
  -q --cov=src --cov-report=term-missing --cov-fail-under=100
```

Local tests parse all YAML structurally and perform non-authoritative static
Caddy assertions. The `deployment-validation` CI job is authoritative: it runs
`docker compose config`, validates `Caddyfile` with pinned
`caddy:2.10.2-alpine`, starts the complete Compose bundle, and smoke-tests `/`,
`/cockpit`, and `/api/health` including redirect and security headers.

### Opt-in kernel benchmarks

The hardware-sensitive latency gates are intentionally separate from the ordinary
coverage matrix. They execute the real 64-lane 4-bit recurrent update and the
actual client-equivalent WebAssembly module through Node:

```bash
python benchmarks/run_benchmarks.py --markdown-output BENCHMARK_RESULTS.md
# Equivalent pytest gate used by the dedicated workflow:
python -m pytest benchmarks/test_kernel_benchmarks.py -m benchmark -v
```

The recurrent kernel uses 200 warmups and 2,000 measured calls and requires p99
strictly below 12 ms. Each WASM kernel uses 25 warmups and 100 measured runs of a
fixed internal loop containing exactly 10,000 operations. The cockpit's
`10k Ops: <250 µs` invariant therefore applies to each complete 10,000-operation
batch, not to one operation. WASM compile and instantiate time are reported
separately. No outliers are discarded. See
[`BENCHMARK_RESULTS.md`](BENCHMARK_RESULTS.md) for methodology and a measured
reference result.
