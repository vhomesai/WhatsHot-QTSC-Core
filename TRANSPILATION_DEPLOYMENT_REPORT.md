# Transpilation and Deployment Report

Generated at `2026-10-03T16:55:04.992856+00:00` by:

```text
python scripts/generate_transpilation_deployment_report.py
```

## Scope and truth boundary

All QPU values below are deterministic circuit-planning, routing, scheduling,
or fail-closed capacity diagnostics. **No vendor QPU was contacted and no hardware
execution, fidelity, or runtime result is claimed.** The placement/routing
algorithm is a deterministic heuristic, not a claim of global optimality.

## Representative 48-logical-qubit plans

| Workload | Backend | Capacity / topology | Original depth | Baseline routed depth | Planned depth | SWAPs | Routing/partition detail |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| QAOA portfolio risk (p=1) | IBM Heron | 156 / Heavy-Hex | 97 | 9001 | 8161 | 5054 | interaction-aware |
| QAOA portfolio risk (p=1) | Rigetti Ankaa | 84 / Square lattice tunable couplers | 97 | 2834 | 2834 | 1696 | baseline non-regression fallback |
| QAOA portfolio risk (p=1) | IonQ Forte | 36 / All-to-All | 1320 gates | N/A | UNSUPPORTED_EXACT_CIRCUIT_CUTTING | 0 | fail-closed; 432 cross-fragment gates |
| qLDPC syndrome extraction (36 data + 12 ancilla) | IBM Heron | 156 / Heavy-Hex | 11 | 671 | 671 | 281 | baseline non-regression fallback |
| qLDPC syndrome extraction (36 data + 12 ancilla) | Rigetti Ankaa | 84 / Square lattice tunable couplers | 11 | 522 | 419 | 185 | interaction-aware |
| qLDPC syndrome extraction (36 data + 12 ancilla) | IonQ Forte | 36 / All-to-All | 72 gates | N/A | UNSUPPORTED_EXACT_CIRCUIT_CUTTING | 0 | fail-closed; 12 cross-fragment gates |

IBM Heron preserves its declared **156-qubit Heavy-Hex** target. IonQ Forte
preserves **36 algorithmic qubits with all-to-all connectivity** and never
claims intact execution of a 48-qubit circuit. Rigetti Ankaa preserves its
declared **84-qubit square lattice tunable-coupler** target.

For IBM and Rigetti, the baseline is identity placement plus deterministic
shortest-path routing. The candidate heuristic orders logical qubits by
interaction degree, places them on high-degree physical sites, inserts
shortest-path SWAPs, and schedules each operation at the earliest dependency-
and resource-safe layer. A deterministic fallback selects the baseline if the
candidate depth regresses.

### IonQ fail-closed capacity diagnostics

- **QAOA portfolio risk (p=1):** diagnostic widths [36, 12], 432 crossing interactions, zero SWAPs. Exact independently sampled density-matrix/process-tensor reconstruction is not implemented, so no fragments, depth equivalence, experiment multiplier, or submission-ready plan is emitted. The rejected ket-only term count is encoded only as the exact decimal string `11090678776483259438313656736572334813745748301503266300681918322458485231222502492159897624416558312389564843845614287315896631296`.
- **qLDPC syndrome extraction (36 data + 12 ancilla):** diagnostic widths [36, 12], 12 crossing interactions, zero SWAPs. Exact independently sampled density-matrix/process-tensor reconstruction is not implemented, so no fragments, depth equivalence, experiment multiplier, or submission-ready plan is emitted. The rejected ket-only term count is encoded only as the exact decimal string `4096`.

The prior ket-only operator-Schmidt expansion was rejected because it did not
specify the independent density-matrix experiments needed for bra/ket cross
terms. No cross-fragment gate is deleted, and no depth or experiment count is
presented as equivalent to intact execution.

## Production deployment bundle

**Authoritative Docker Compose/Caddy executable validation status: PENDING CI.**
It was not run on this report host. The CI job is configured to perform the
authoritative validation on its next execution.

- `Dockerfile` runs `src.api_server:app` as UID/GID 10001 on pinned
  `python:3.12.15-slim-bookworm`, installing the sole resolved runtime set from
  `requirements.lock` before installing the local package with `--no-deps`.
- `docker-compose.yml` exposes only Caddy on ports 80/443, keeps the API on an
  internal network, uses read-only filesystems, tmpfs, dropped capabilities,
  `no-new-privileges`, healthchecks, restart policies, and a persistent SQLite
  volume.
- `Caddyfile` obtains HTTPS automatically for `www.triqee.com`, serves the
  zero-CDN cockpit at `/cockpit`, reverse-proxies same-origin `/api/*` traffic,
  preserves streaming/WebSocket behavior, compresses responses, limits request
  bodies, and adds standard security headers.
- `.dockerignore` excludes credentials, local environments, databases, logs,
  caches, coverage output, tests, benchmarks, archives, and binary WASM files.
- `TRIQEE_ADMIN_KEY` is required only in the server environment and is not
  embedded in the image or browser. Production CORS is restricted to
  `https://www.triqee.com`.

Local validator availability on this report host:

| Tool | Status |
| :--- | :--- |
| Docker | not installed |
| Caddy CLI | not installed |

Local deployment tests are structural and explicitly non-authoritative when
those executables are unavailable. Authoritative executable validation remains
**PENDING CI** until the configured CI job completes. Equivalent local commands are
`docker compose config` and
`docker run --rm -v "$PWD/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2.10.2-alpine caddy validate --config /etc/caddy/Caddyfile`.

## Environment and reproducibility

- Host: `Windows-10-10.0.19045-SP0`
- Python: `CPython 3.12.5`
- QPU report command: `python scripts/generate_transpilation_deployment_report.py`
- QPU plan IDs are deterministic hashes of the canonical circuit IR and backend.
- Connected-topology plans retain executable gate parameters and are JSON
  serializable for asynchronous vendor submission. IonQ is explicitly
  `UNSUPPORTED_EXACT_CIRCUIT_CUTTING`; only a capacity diagnostic is emitted.
  Credentialed calls and SDK lock-in are intentionally outside this increment.
