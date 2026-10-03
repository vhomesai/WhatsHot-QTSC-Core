"""Generate the deterministic QPU planning and deployment report."""

from __future__ import annotations

import argparse
import platform
import shutil
from datetime import datetime, timezone
from pathlib import Path

from src.qpu_transpiler import plan_multivendor_workload

ROOT = Path(__file__).resolve().parents[1]


def render_report(*, generated_at: str, command: str) -> str:
    workloads = {
        "QAOA portfolio risk (p=1)": plan_multivendor_workload(
            "qaoa_portfolio_risk",
            qaoa_p=1,
        ),
        "qLDPC syndrome extraction (36 data + 12 ancilla)": (
            plan_multivendor_workload("qldpc_syndrome_extraction")
        ),
    }
    rows: list[str] = []
    ionq_details: list[str] = []
    for workload_name, bundle in workloads.items():
        for plan in bundle["plans"].values():
            rows.append(
                f"| {workload_name} | {plan['backend']['vendor']} "
                f"{plan['backend']['model']} | {plan['backend']['capacity']} / "
                f"{plan['backend']['topology']} | {plan['original_depth']} | "
                f"{plan['baseline_depth']} | {plan['optimized_depth']} | "
                f"{plan['optimized_swap_count']} | {plan['placement_selected']} |"
            )
        diagnostic = bundle["unsupported_backends"]["ionq_forte"]
        rows.append(
            f"| {workload_name} | IonQ Forte | 36 / All-to-All | "
            f"{len(bundle['circuit_ir']['operations'])} gates | N/A | "
            f"{diagnostic['status']} | 0 | fail-closed; "
            f"{diagnostic['cut_count']} cross-fragment gates |"
        )
        ionq_details.append(
            f"- **{workload_name}:** diagnostic widths "
            f"{diagnostic['fragment_widths']}, {diagnostic['cut_count']} crossing "
            "interactions, zero SWAPs. Exact independently sampled density-matrix/"
            "process-tensor reconstruction is not implemented, so no fragments, "
            "depth equivalence, experiment multiplier, or submission-ready plan "
            "is emitted. The rejected ket-only term count is encoded only as the "
            f"exact decimal string `{diagnostic['rejected_amplitude_expansion_term_count']['decimal']}`."
        )

    docker_status = "available" if shutil.which("docker") else "not installed"
    caddy_status = "available" if shutil.which("caddy") else "not installed"
    return f"""# Transpilation and Deployment Report

Generated at `{generated_at}` by:

```text
{command}
```

## Scope and truth boundary

All QPU values below are deterministic circuit-planning, routing, scheduling,
or fail-closed capacity diagnostics. **No vendor QPU was contacted and no hardware
execution, fidelity, or runtime result is claimed.** The placement/routing
algorithm is a deterministic heuristic, not a claim of global optimality.

## Representative 48-logical-qubit plans

| Workload | Backend | Capacity / topology | Original depth | Baseline routed depth | Planned depth | SWAPs | Routing/partition detail |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |
{chr(10).join(rows)}

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

{chr(10).join(ionq_details)}

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
| Docker | {docker_status} |
| Caddy CLI | {caddy_status} |

Local deployment tests are structural and explicitly non-authoritative when
those executables are unavailable. Authoritative executable validation remains
**PENDING CI** until the configured CI job completes. Equivalent local commands are
`docker compose config` and
`docker run --rm -v "$PWD/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2.10.2-alpine caddy validate --config /etc/caddy/Caddyfile`.

## Environment and reproducibility

- Host: `{platform.platform()}`
- Python: `{platform.python_implementation()} {platform.python_version()}`
- QPU report command: `{command}`
- QPU plan IDs are deterministic hashes of the canonical circuit IR and backend.
- Connected-topology plans retain executable gate parameters and are JSON
  serializable for asynchronous vendor submission. IonQ is explicitly
  `UNSUPPORTED_EXACT_CIRCUIT_CUTTING`; only a capacity diagnostic is emitted.
  Credentialed calls and SDK lock-in are intentionally outside this increment.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "TRANSPILATION_DEPLOYMENT_REPORT.md",
    )
    arguments = parser.parse_args()
    command = "python scripts/generate_transpilation_deployment_report.py"
    if arguments.output != ROOT / "TRANSPILATION_DEPLOYMENT_REPORT.md":
        command += f" --output {arguments.output}"
    arguments.output.write_text(
        render_report(
            generated_at=datetime.now(timezone.utc).isoformat(),
            command=command,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
