import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";

const [wasmPath, clientPath, sampleArg = "100", warmupArg = "25"] = process.argv.slice(2);
if (!wasmPath || !clientPath) {
    throw new Error("Usage: node wasm_benchmark.mjs WASM_PATH CLIENT_PATH [SAMPLES] [WARMUPS]");
}

const sampleCount = Number.parseInt(sampleArg, 10);
const warmupCount = Number.parseInt(warmupArg, 10);
if (!Number.isInteger(sampleCount) || sampleCount < 1 ||
    !Number.isInteger(warmupCount) || warmupCount < 0) {
    throw new Error("Sample count must be positive and warmup count must be non-negative.");
}

function nearestRank(sortedValues, percentile) {
    const rank = Math.max(1, Math.ceil((percentile / 100) * sortedValues.length));
    return sortedValues[rank - 1];
}

function summarize(values) {
    const sorted = [...values].sort((a, b) => a - b);
    return {
        minimum_us: sorted[0],
        p50_us: nearestRank(sorted, 50),
        p95_us: nearestRank(sorted, 95),
        p99_us: nearestRank(sorted, 99),
        maximum_us: sorted[sorted.length - 1],
    };
}

function measureBatch(fn, args) {
    const samples = [];
    let checksum = 0;
    let lastResult = 0;
    for (let i = 0; i < sampleCount; i++) {
        const started = process.hrtime.bigint();
        const result = fn(...args);
        const finished = process.hrtime.bigint();
        samples.push(Number(finished - started) / 1000);
        checksum += result;
        lastResult = result;
    }
    return { ...summarize(samples), last_result: lastResult, checksum };
}

const wasmBytes = fs.readFileSync(wasmPath);
let started = process.hrtime.bigint();
const module = await WebAssembly.compile(wasmBytes);
let finished = process.hrtime.bigint();
const compileUs = Number(finished - started) / 1000;

started = process.hrtime.bigint();
const instance = await WebAssembly.instantiate(module);
finished = process.hrtime.bigint();
const instantiateUs = Number(finished - started) / 1000;
const kernel = instance.exports;

const requiredExports = [
    "geodesic_rf_latency",
    "fiber_optical_latency",
    "photonic_mac",
    "qber_rate",
    "photonic_mac_batch_10000",
    "geodesic_rf_latency_batch_10000",
];
for (const exportName of requiredExports) {
    if (typeof kernel[exportName] !== "function") {
        throw new Error(`Missing WASM export: ${exportName}`);
    }
}

for (let i = 0; i < warmupCount; i++) {
    kernel.photonic_mac_batch_10000(1.0004, 0.9996, 0);
    kernel.geodesic_rf_latency_batch_10000(3900, 1.0075);
}

const require = createRequire(import.meta.url);
const { TriqeeEdgeClient } = require(path.resolve(clientPath));
const edgeClient = new TriqeeEdgeClient("BENCHMARK_NODE", "NODE_JS");
const coordinateCases = [
    { name: "same-point", points: [0, 0, 0, 0] },
    { name: "chicago-london", points: [41.8781, -87.6298, 51.5074, -0.1278] },
    { name: "antimeridian", points: [10, 179.9, 10, -179.9] },
    { name: "north-south-poles", points: [90, 0, -90, 180] },
];

const result = {
    methodology: {
        timer: "process.hrtime.bigint",
        sample_count: sampleCount,
        warmup_count: warmupCount,
        operation_count_per_batch: 10000,
        percentile_method: "nearest-rank",
        outliers_discarded: 0,
        setup_excluded: ["file read", "WASM compile", "WASM instantiate", "warmup"],
    },
    environment: {
        node: process.version,
        platform: process.platform,
        architecture: process.arch,
        cpu: os.cpus()[0]?.model ?? "unknown",
    },
    wasm: {
        byte_size: wasmBytes.byteLength,
        compile_us: compileUs,
        instantiate_us: instantiateUs,
        exports: requiredExports,
        photonic_mac_batch: measureBatch(
            kernel.photonic_mac_batch_10000,
            [1.0004, 0.9996, 0],
        ),
        geodesic_batch: measureBatch(
            kernel.geodesic_rf_latency_batch_10000,
            [3900, 1.0075],
        ),
    },
    accuracy: {
        photonic_mac: [
            { input: [0, 0, 0], actual: kernel.photonic_mac(0, 0, 0) },
            { input: [1.25, -2, 3.5], actual: kernel.photonic_mac(1.25, -2, 3.5) },
            { input: [1.0004, 0.9996, 0], actual: kernel.photonic_mac(1.0004, 0.9996, 0) },
        ],
        coordinate_distances: coordinateCases.map(({ name, points }) => ({
            name,
            points,
            distance_km: edgeClient.computeHaversineDistanceKm(...points),
        })),
        geodesic_latency: [0, 0.001, 3900, 20015.086796020572].map((distanceKm) => ({
            distance_km: distanceKm,
            slant_factor: 1.0075,
            actual_ms: kernel.geodesic_rf_latency(distanceKm, 1.0075),
        })),
        fiber_latency: [0, 3900, 20015.086796020572].map((distanceKm) => ({
            distance_km: distanceKm,
            routing_factor: 1.22,
            refractive_index: 1.4682,
            actual_ms: kernel.fiber_optical_latency(distanceKm, 1.22, 1.4682),
        })),
    },
};

process.stdout.write(`${JSON.stringify(result)}\n`);
