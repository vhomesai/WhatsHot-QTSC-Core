"""Deterministic benchmark and physical-accuracy gates for Triqee SI kernels."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.edge_engine import TriqeeEdgeEngine
from src.physics_engine import (
    C_LIGHT_KM_S,
    DEFAULT_FIBER_INDEX_N,
    EARTH_RADIUS_KM,
    haversine_distance,
)
from src.silicon_kernel_wasm import build_silicon_wasm_binary

ROOT = Path(__file__).resolve().parents[1]
RECURRENT_P99_LIMIT_MS = 12.0
WASM_BATCH_P99_LIMIT_US = 250.0
FLOAT_TOLERANCE = 1e-9
DISTANCE_TOLERANCE_KM = 1e-9
BATCH_ACCUMULATION_TOLERANCE = 1e-8


def _nearest_rank(values: list[float], percentile: int) -> float:
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile / 100 * len(ordered)))
    return ordered[rank - 1]


def _distribution(values: list[float], unit: str) -> dict[str, float]:
    return {
        f"minimum_{unit}": min(values),
        f"p50_{unit}": _nearest_rank(values, 50),
        f"p95_{unit}": _nearest_rank(values, 95),
        f"p99_{unit}": _nearest_rank(values, 99),
        f"maximum_{unit}": max(values),
    }


def benchmark_recurrent(sample_count: int, warmup_count: int) -> dict[str, Any]:
    """Time the real 64-lane, 4-bit state update invoked by the SI call chain."""
    engine = TriqeeEdgeEngine("BENCHMARK_NODE", "LOCAL_CPU")
    prompt = "Triqee deterministic quantized recurrent state benchmark input"
    updates_per_sample = engine.state_dimension

    for _ in range(warmup_count):
        engine.run_edge_inference(prompt, max_tokens=updates_per_sample)

    samples_ms: list[float] = []
    for _ in range(sample_count):
        started_ns = time.perf_counter_ns()
        result = engine.run_edge_inference(prompt, max_tokens=updates_per_sample)
        elapsed_ns = time.perf_counter_ns() - started_ns
        samples_ms.append(elapsed_ns / 1_000_000)
        expected_prefixes = [f"tok_{index}_" for index in range(engine.state_dimension)]
        if (
            result["tokens_count"] != updates_per_sample
            or len(result["output_tokens"]) != updates_per_sample
            or any(
                not token.startswith(expected_prefix)
                for token, expected_prefix in zip(result["output_tokens"], expected_prefixes)
            )
        ):
            raise AssertionError("The recurrent kernel did not update each state lane exactly once.")

    levels = engine.quantization_levels
    if any(abs(value * levels - round(value * levels)) > 1e-12 for value in engine.recurrent_state):
        raise AssertionError("The recurrent state escaped the declared 4-bit quantization grid.")

    distribution = _distribution(samples_ms, "ms")
    return {
        "methodology": {
            "timer": "time.perf_counter_ns",
            "sample_count": sample_count,
            "warmup_count": warmup_count,
            "percentile_method": "nearest-rank",
            "outliers_discarded": 0,
            "setup_excluded": ["engine construction", "prompt construction", "warmup"],
            "input": {
                "prompt_utf8_bytes": len(prompt.encode("utf-8")),
                "max_tokens": updates_per_sample,
            },
            "state": {
                "lanes": engine.state_dimension,
                "lanes_updated_per_sample": engine.state_dimension,
                "update_operations_per_sample": updates_per_sample,
                "lane_index_sequence": "0..63 exactly once",
                "quantization_bits": engine.quantization_bits,
                "quantization_levels": engine.quantization_levels + 1,
            },
        },
        "distribution": distribution,
        "threshold": {"p99_ms_strictly_less_than": RECURRENT_P99_LIMIT_MS},
        "passed": distribution["p99_ms"] < RECURRENT_P99_LIMIT_MS,
    }


def _run_node_wasm_benchmark(sample_count: int, warmup_count: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temp_directory:
        wasm_path = Path(temp_directory, "triqee_silicon_kernel.wasm")
        wasm_path.write_bytes(build_silicon_wasm_binary())
        command = [
            "node",
            str(ROOT / "benchmarks" / "wasm_benchmark.mjs"),
            str(wasm_path),
            str(ROOT / "src" / "triqee_edge_client.js"),
            str(sample_count),
            str(warmup_count),
        ]
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    return json.loads(completed.stdout)


def _verify_wasm_accuracy(node_result: dict[str, Any]) -> dict[str, Any]:
    maximum_errors = {
        "photonic_mac_absolute": 0.0,
        "coordinate_distance_km": 0.0,
        "geodesic_latency_ms": 0.0,
        "fiber_latency_ms": 0.0,
        "photonic_batch_accumulator": 0.0,
        "geodesic_batch_accumulator": 0.0,
    }

    for case in node_result["accuracy"]["photonic_mac"]:
        a, b, accumulator = case["input"]
        expected = a * b + accumulator
        maximum_errors["photonic_mac_absolute"] = max(
            maximum_errors["photonic_mac_absolute"],
            abs(case["actual"] - expected),
        )

    for case in node_result["accuracy"]["coordinate_distances"]:
        expected = haversine_distance(*case["points"])
        maximum_errors["coordinate_distance_km"] = max(
            maximum_errors["coordinate_distance_km"],
            abs(case["distance_km"] - expected),
        )

    for case in node_result["accuracy"]["geodesic_latency"]:
        expected = case["distance_km"] * case["slant_factor"] / C_LIGHT_KM_S * 1000.0
        maximum_errors["geodesic_latency_ms"] = max(
            maximum_errors["geodesic_latency_ms"],
            abs(case["actual_ms"] - expected),
        )

    for case in node_result["accuracy"]["fiber_latency"]:
        expected = (
            case["distance_km"]
            * case["routing_factor"]
            / (C_LIGHT_KM_S / case["refractive_index"])
            * 1000.0
        )
        maximum_errors["fiber_latency_ms"] = max(
            maximum_errors["fiber_latency_ms"],
            abs(case["actual_ms"] - expected),
        )

    operation_count = node_result["methodology"]["operation_count_per_batch"]
    expected_mac_batch = operation_count * 1.0004 * 0.9996
    maximum_errors["photonic_batch_accumulator"] = abs(
        node_result["wasm"]["photonic_mac_batch"]["last_result"] - expected_mac_batch
    )
    expected_geodesic_batch = sum(
        ((3900 + index) * 1.0075 / C_LIGHT_KM_S) * 1000.0
        for index in range(operation_count)
    )
    maximum_errors["geodesic_batch_accumulator"] = abs(
        node_result["wasm"]["geodesic_batch"]["last_result"] - expected_geodesic_batch
    )

    if maximum_errors["coordinate_distance_km"] > DISTANCE_TOLERANCE_KM:
        raise AssertionError("Client Haversine distance exceeded the 1e-9 km tolerance.")
    for name in ("photonic_mac_absolute", "geodesic_latency_ms", "fiber_latency_ms"):
        if maximum_errors[name] > FLOAT_TOLERANCE:
            raise AssertionError(f"{name} exceeded the 1e-9 absolute tolerance.")
    for name in ("photonic_batch_accumulator", "geodesic_batch_accumulator"):
        if maximum_errors[name] > BATCH_ACCUMULATION_TOLERANCE:
            raise AssertionError(f"{name} exceeded the 1e-8 accumulation tolerance.")

    return {
        "constants": {
            "c_km_per_s": C_LIGHT_KM_S,
            "fiber_refractive_index": DEFAULT_FIBER_INDEX_N,
            "earth_radius_km": EARTH_RADIUS_KM,
        },
        "tolerances": {
            "floating_point_absolute": FLOAT_TOLERANCE,
            "coordinate_distance_km": DISTANCE_TOLERANCE_KM,
            "batch_accumulation_absolute": BATCH_ACCUMULATION_TOLERANCE,
        },
        "maximum_errors": maximum_errors,
        "passed": True,
    }


def benchmark_wasm(sample_count: int, warmup_count: int) -> dict[str, Any]:
    """Benchmark actual warmed Node WebAssembly batch exports and verify physics."""
    result = _run_node_wasm_benchmark(sample_count, warmup_count)
    result["physical_accuracy"] = _verify_wasm_accuracy(result)
    result["threshold"] = {
        "scope": "each complete 10,000-operation batch",
        "p99_us_strictly_less_than": WASM_BATCH_P99_LIMIT_US,
    }
    result["passed"] = (
        result["wasm"]["photonic_mac_batch"]["p99_us"] < WASM_BATCH_P99_LIMIT_US
        and result["wasm"]["geodesic_batch"]["p99_us"] < WASM_BATCH_P99_LIMIT_US
    )
    return result


def run_all(
    recurrent_samples: int = 2000,
    recurrent_warmups: int = 200,
    wasm_samples: int = 100,
    wasm_warmups: int = 25,
    enforce_gates: bool = True,
) -> dict[str, Any]:
    report = {
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "processor": platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "unknown"),
        },
        "recurrent": benchmark_recurrent(recurrent_samples, recurrent_warmups),
        "wasm": benchmark_wasm(wasm_samples, wasm_warmups),
    }
    report["passed"] = report["recurrent"]["passed"] and report["wasm"]["passed"]
    if enforce_gates and not report["passed"]:
        raise AssertionError("One or more benchmark latency gates failed.")
    return report


def render_markdown_report(
    report: dict[str, Any],
    *,
    generated_at: str,
    command: str,
) -> str:
    """Render the tracked benchmark report from one exact measured result object."""
    recurrent = report["recurrent"]
    wasm = report["wasm"]
    recurrent_dist = recurrent["distribution"]
    mac = wasm["wasm"]["photonic_mac_batch"]
    geodesic = wasm["wasm"]["geodesic_batch"]
    accuracy = wasm["physical_accuracy"]
    environment = report["environment"]
    wasm_environment = wasm["environment"]
    methodology = recurrent["methodology"]
    wasm_methodology = wasm["methodology"]

    def number(value: float) -> str:
        return f"{value:.12g}"

    accuracy_rows = "\n".join(
        f"| {name.replace('_', ' ')} | {number(value)} |"
        for name, value in accuracy["maximum_errors"].items()
    )
    return f"""# Triqee Kernel Benchmark Results

Generated at `{generated_at}` by:

```text
{command}
```

## Result

Overall result: **{"PASS" if report["passed"] else "FAIL"}**.

| Kernel | Workload | p50 | p95 | p99 | Hard gate | Result |
| :--- | :--- | ---: | ---: | ---: | :--- | :--- |
| Quantized recurrent memory | {methodology["state"]["lanes"]} lanes, {methodology["state"]["update_operations_per_sample"]} updates/sample, {methodology["state"]["quantization_bits"]}-bit state/input | {number(recurrent_dist["p50_ms"])} ms | {number(recurrent_dist["p95_ms"])} ms | {number(recurrent_dist["p99_ms"])} ms | p99 < {number(recurrent["threshold"]["p99_ms_strictly_less_than"])} ms | {"PASS" if recurrent["passed"] else "FAIL"} |
| WASM photonic MAC | Exactly {wasm_methodology["operation_count_per_batch"]:,} operations/batch | {number(mac["p50_us"])} us | {number(mac["p95_us"])} us | {number(mac["p99_us"])} us | p99 < {number(wasm["threshold"]["p99_us_strictly_less_than"])} us/batch | {"PASS" if mac["p99_us"] < wasm["threshold"]["p99_us_strictly_less_than"] else "FAIL"} |
| WASM geodesic latency | Exactly {wasm_methodology["operation_count_per_batch"]:,} operations/batch | {number(geodesic["p50_us"])} us | {number(geodesic["p95_us"])} us | {number(geodesic["p99_us"])} us | p99 < {number(wasm["threshold"]["p99_us_strictly_less_than"])} us/batch | {"PASS" if geodesic["p99_us"] < wasm["threshold"]["p99_us_strictly_less_than"] else "FAIL"} |

WASM compilation took **{number(wasm["wasm"]["compile_us"])} us** and instantiation
took **{number(wasm["wasm"]["instantiate_us"])} us**. These setup costs are
reported separately and excluded from steady-state execution timing.

## Methodology

The recurrent benchmark uses `{methodology["timer"]}`, performs
{methodology["warmup_count"]} warmups, then records {methodology["sample_count"]}
measured calls to the real `TriqeeEdgeEngine.run_edge_inference` implementation.
Every measured sample performs exactly
{methodology["state"]["update_operations_per_sample"]} update operations using
lane sequence `{methodology["state"]["lane_index_sequence"]}`, so all
{methodology["state"]["lanes"]} recurrent state lanes are exercised exactly once.
The input prompt is {methodology["input"]["prompt_utf8_bytes"]} UTF-8 bytes.
Inputs and state use {methodology["state"]["quantization_levels"]} unsigned levels
({methodology["state"]["quantization_bits"]} bits).

The WASM benchmark builds the production {wasm["wasm"]["byte_size"]}-byte module,
executes it through Node WebAssembly, uses `{wasm_methodology["timer"]}`, performs
{wasm_methodology["warmup_count"]} warmups, and records
{wasm_methodology["sample_count"]} samples per kernel. Each export contains a
fixed internal loop of exactly {wasm_methodology["operation_count_per_batch"]:,}
operations. The `<250 us` invariant applies to the complete 10,000-operation
batch, matching the cockpit label. Both harnesses use
`{methodology["percentile_method"]}` percentiles and discard
{methodology["outliers_discarded"]} outliers.

## Environment

| Component | Value |
| :--- | :--- |
| OS/platform | {environment["platform"]} |
| Architecture | {environment["architecture"]} |
| Processor | {environment["processor"]} |
| Python | {environment["implementation"]} {environment["python"]} |
| Node | {wasm_environment["node"]} |
| Node platform/architecture | {wasm_environment["platform"]} / {wasm_environment["architecture"]} |
| Node CPU | {wasm_environment["cpu"]} |

Observed ranges were {number(recurrent_dist["minimum_ms"])}-
{number(recurrent_dist["maximum_ms"])} ms for the recurrent kernel,
{number(mac["minimum_us"])}-{number(mac["maximum_us"])} us for the photonic
batch, and {number(geodesic["minimum_us"])}-{number(geodesic["maximum_us"])} us
for the geodesic batch.

## Physical accuracy

Reference constants and tolerances:

| Item | Value |
| :--- | ---: |
| Speed of light | {number(accuracy["constants"]["c_km_per_s"])} km/s |
| Fiber refractive index | {number(accuracy["constants"]["fiber_refractive_index"])} |
| Earth radius | {number(accuracy["constants"]["earth_radius_km"])} km |
| Scalar absolute tolerance | {number(accuracy["tolerances"]["floating_point_absolute"])} |
| Coordinate-distance tolerance | {number(accuracy["tolerances"]["coordinate_distance_km"])} km |
| Batch-accumulation tolerance | {number(accuracy["tolerances"]["batch_accumulation_absolute"])} |

Maximum measured errors:

| Quantity | Maximum absolute error |
| :--- | ---: |
{accuracy_rows}

Accuracy result: **{"PASS" if accuracy["passed"] else "FAIL"}**. Client Haversine
checks cover identical points, Chicago-London, an antimeridian crossing, and the
north-to-south pole boundary. Scalar and complete 10,000-operation accumulator
checks are compared with deterministic Python references.

## Limitations

Latency is hardware, operating-system, and runtime sensitive. The benchmark runs
in a dedicated pinned `ubuntu-22.04`, Python 3.12, Node 24 workflow rather than
the ordinary coverage matrix. This report records the environment above; other
controlled runners remain subject to the same gates.

The WASM ABI accepts distance rather than latitude/longitude. Client-side
Haversine conversion is accuracy-tested separately and is not included in the
timed geodesic batch. Compilation, instantiation, input construction, and warmup
are excluded from steady-state timing. No mocks, fake sleeps, Python timing
proxies, or discarded outliers are used.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional path for the JSON result.")
    parser.add_argument(
        "--markdown-output",
        type=Path,
        help="Optional Markdown report rendered from this exact measured result.",
    )
    parser.add_argument("--recurrent-samples", type=int, default=2000)
    parser.add_argument("--recurrent-warmups", type=int, default=200)
    parser.add_argument("--wasm-samples", type=int, default=100)
    parser.add_argument("--wasm-warmups", type=int, default=25)
    arguments = parser.parse_args()
    report = run_all(
        recurrent_samples=arguments.recurrent_samples,
        recurrent_warmups=arguments.recurrent_warmups,
        wasm_samples=arguments.wasm_samples,
        wasm_warmups=arguments.wasm_warmups,
    )
    rendered = json.dumps(report, indent=2)
    if arguments.output:
        arguments.output.write_text(f"{rendered}\n", encoding="utf-8")
    if arguments.markdown_output:
        command = subprocess.list2cmdline(["python", *sys.argv])
        markdown = render_markdown_report(
            report,
            generated_at=datetime.now(timezone.utc).isoformat(),
            command=command,
        )
        arguments.markdown_output.write_text(markdown, encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
