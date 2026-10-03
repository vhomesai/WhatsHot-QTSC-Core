# Triqee Kernel Benchmark Results

Generated at `2026-10-03T15:30:45.481675+00:00` by:

```text
python benchmarks\run_benchmarks.py --markdown-output BENCHMARK_RESULTS.md
```

## Result

Overall result: **PASS**.

| Kernel | Workload | p50 | p95 | p99 | Hard gate | Result |
| :--- | :--- | ---: | ---: | ---: | :--- | :--- |
| Quantized recurrent memory | 64 lanes, 64 updates/sample, 4-bit state/input | 0.056 ms | 0.1445 ms | 0.2724 ms | p99 < 12 ms | PASS |
| WASM photonic MAC | Exactly 10,000 operations/batch | 31.4 us | 61.6 us | 102.4 us | p99 < 250 us/batch | PASS |
| WASM geodesic latency | Exactly 10,000 operations/batch | 29.3 us | 34.5 us | 55.1 us | p99 < 250 us/batch | PASS |

WASM compilation took **7234.2 us** and instantiation
took **500.2 us**. These setup costs are
reported separately and excluded from steady-state execution timing.

## Methodology

The recurrent benchmark uses `time.perf_counter_ns`, performs
200 warmups, then records 2000
measured calls to the real `TriqeeEdgeEngine.run_edge_inference` implementation.
Every measured sample performs exactly
64 update operations using
lane sequence `0..63 exactly once`, so all
64 recurrent state lanes are exercised exactly once.
The input prompt is 62 UTF-8 bytes.
Inputs and state use 16 unsigned levels
(4 bits).

The WASM benchmark builds the production 380-byte module,
executes it through Node WebAssembly, uses `process.hrtime.bigint`, performs
25 warmups, and records
100 samples per kernel. Each export contains a
fixed internal loop of exactly 10,000
operations. The `<250 us` invariant applies to the complete 10,000-operation
batch, matching the cockpit label. Both harnesses use
`nearest-rank` percentiles and discard
0 outliers.

## Environment

| Component | Value |
| :--- | :--- |
| OS/platform | Windows-10-10.0.19045-SP0 |
| Architecture | AMD64 |
| Processor | Intel64 Family 6 Model 126 Stepping 5, GenuineIntel |
| Python | CPython 3.12.5 |
| Node | v24.19.0 |
| Node platform/architecture | win32 / x64 |
| Node CPU | Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz |

Observed ranges were 0.0539-
0.8188 ms for the recurrent kernel,
26.7-128.9 us for the photonic
batch, and 27.5-58.5 us
for the geodesic batch.

## Physical accuracy

Reference constants and tolerances:

| Item | Value |
| :--- | ---: |
| Speed of light | 299792.458 km/s |
| Fiber refractive index | 1.4682 |
| Earth radius | 6371 km |
| Scalar absolute tolerance | 1e-09 |
| Coordinate-distance tolerance | 1e-09 km |
| Batch-accumulation tolerance | 1e-08 |

Maximum measured errors:

| Quantity | Maximum absolute error |
| :--- | ---: |
| photonic mac absolute | 0 |
| coordinate distance km | 9.09494701773e-13 |
| geodesic latency ms | 0 |
| fiber latency ms | 3.5527136788e-15 |
| photonic batch accumulator | 9.18589648791e-10 |
| geodesic batch accumulator | 0 |

Accuracy result: **PASS**. Client Haversine
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
