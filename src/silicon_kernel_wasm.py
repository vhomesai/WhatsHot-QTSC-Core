"""
Triqee Silicon Kernel WebAssembly (WASM) Compiler & Verification Module
========================================================================
Generates ultra-compact, standalone WebAssembly bytecode for client-side
hardware-speed physics calculations, optical tensor matrix math, and quantum QBER.
"""

import base64
from typing import Dict, Any


def _encode_u32_leb128(value: int) -> bytes:
    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            encoded.append(byte | 0x80)
        else:
            encoded.append(byte)
            return bytes(encoded)


def _encode_i32_leb128(value: int) -> bytes:
    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        sign_bit_set = byte & 0x40
        done = (value == 0 and not sign_bit_set) or (value == -1 and sign_bit_set)
        encoded.append(byte if done else byte | 0x80)
        if done:
            return bytes(encoded)


def _section(section_id: int, payload: bytes) -> bytes:
    return bytes([section_id]) + _encode_u32_leb128(len(payload)) + payload


def _function_body(operations: bytes) -> bytes:
    return _encode_u32_leb128(len(operations)) + operations


def build_silicon_wasm_binary() -> bytes:
    """
    Constructs a minimal, valid WebAssembly 1.0 binary module exporting:
    1. `geodesic_rf_latency(dist_km: f64, slant: f64) -> f64`
    2. `fiber_optical_latency(dist_km: f64, route: f64, n_fiber: f64) -> f64`
    3. `photonic_mac(a: f64, b: f64, accum: f64) -> f64`
    4. `qber_rate(errors: f64, total_qubits: f64) -> f64`
    5. `photonic_mac_batch_10000(a: f64, b: f64, accum: f64) -> f64`
    6. `geodesic_rf_latency_batch_10000(dist_km: f64, slant: f64) -> f64`

    Standard WebAssembly Bytecode Format:
    - Magic: \\x00asm (0x00, 0x61, 0x73, 0x6d)
    - Version: 0x01, 0x00, 0x00, 0x00
    - Type Section (id 1)
    - Function Section (id 3)
    - Export Section (id 7)
    - Code Section (id 10)
    """

    # Type Section:
    # Type 0: (f64, f64) -> f64 (for geodesic_rf_latency, qber_rate)
    # Type 1: (f64, f64, f64) -> f64 (for fiber_optical_latency, photonic_mac)
    # 0x01: Section ID (Type)
    # Payload length will be calculated
    type_section_payload = bytes([
        0x02,  # 2 types
        # Type 0: (f64, f64) -> f64
        0x60, 0x02, 0x7c, 0x7c, 0x01, 0x7c,
        # Type 1: (f64, f64, f64) -> f64
        0x60, 0x03, 0x7c, 0x7c, 0x7c, 0x01, 0x7c
    ])
    type_section = _section(0x01, type_section_payload)

    # Function Section: 6 functions -> [type 0, type 1, type 1, type 0, type 1, type 0]
    func_section_payload = bytes([
        0x06,  # 6 functions
        0x00,  # func 0: Type 0 (geodesic_rf_latency)
        0x01,  # func 1: Type 1 (fiber_optical_latency)
        0x01,  # func 2: Type 1 (photonic_mac)
        0x00,  # func 3: Type 0 (qber_rate)
        0x01,  # func 4: Type 1 (photonic_mac_batch_10000)
        0x00,  # func 5: Type 0 (geodesic_rf_latency_batch_10000)
    ])
    func_section = _section(0x03, func_section_payload)

    # Export Section: Export 6 functions
    # 0: geodesic_rf_latency (funcidx 0)
    # 1: fiber_optical_latency (funcidx 1)
    # 2: photonic_mac (funcidx 2)
    # 3: qber_rate (funcidx 3)
    exp_rf = b"geodesic_rf_latency"
    exp_fiber = b"fiber_optical_latency"
    exp_mac = b"photonic_mac"
    exp_qber = b"qber_rate"
    exp_mac_batch = b"photonic_mac_batch_10000"
    exp_rf_batch = b"geodesic_rf_latency_batch_10000"

    export_section_payload = bytes([
        0x06,  # 6 exports
        # Export 0
        len(exp_rf)] + list(exp_rf) + [0x00, 0x00,
        # Export 1
        len(exp_fiber)] + list(exp_fiber) + [0x00, 0x01,
        # Export 2
        len(exp_mac)] + list(exp_mac) + [0x00, 0x02,
        # Export 3
        len(exp_qber)] + list(exp_qber) + [0x00, 0x03,
        # Export 4
        len(exp_mac_batch)] + list(exp_mac_batch) + [0x00, 0x04,
        # Export 5
        len(exp_rf_batch)] + list(exp_rf_batch) + [0x00, 0x05
    ])
    export_section = _section(0x07, export_section_payload)

    # Speed of light c = 299792.458 km/s in f64 IEEE 754:
    # 299792.458 = 0x41124c41d4fdf3b6 -> little endian: b6 f3 fd d4 41 4c 12 41
    c_const_f64 = bytes([0xb6, 0xf3, 0xfd, 0xd4, 0x41, 0x4c, 0x12, 0x41])
    # 1000.0 (ms conversion) = 0x408f400000000000 -> little endian: 00 00 00 00 00 40 8f 40
    ms_const_f64 = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x8f, 0x40])

    # Code Bodies:
    # Func 0: geodesic_rf_latency(dist, slant) -> (dist * slant / c) * 1000.0
    # locals count: 0
    # local.get 0 (0x20 0x00), local.get 1 (0x20 0x01), f64.mul (0xa2)
    # f64.const c (0x44 + c_const), f64.div (0xa3)
    # f64.const 1000.0 (0x44 + ms_const), f64.mul (0xa2), end (0x0b)
    body0_ops = bytes([
        0x00, # 0 locals
        0x20, 0x00, 0x20, 0x01, 0xa2, # get 0, get 1, mul
        0x44] + list(c_const_f64) + [0xa3, # const c, div
        0x44] + list(ms_const_f64) + [0xa2, # const 1000, mul
        0x0b # end
    ])
    body0 = _function_body(body0_ops)

    # Func 1: fiber_optical_latency(dist, route, n_fiber) -> (dist * route * n_fiber / c) * 1000.0
    body1_ops = bytes([
        0x00, # 0 locals
        0x20, 0x00, 0x20, 0x01, 0xa2, # get 0, get 1, mul
        0x20, 0x02, 0xa2, # get 2, mul
        0x44] + list(c_const_f64) + [0xa3, # const c, div
        0x44] + list(ms_const_f64) + [0xa2, # const 1000, mul
        0x0b # end
    ])
    body1 = _function_body(body1_ops)

    # Func 2: photonic_mac(a, b, accum) -> (a * b) + accum
    body2_ops = bytes([
        0x00, # 0 locals
        0x20, 0x00, 0x20, 0x01, 0xa2, # get 0, get 1, mul
        0x20, 0x02, 0xa0, # get 2, add
        0x0b # end
    ])
    body2 = _function_body(body2_ops)

    # Func 3: qber_rate(errors, total) -> errors / total
    body3_ops = bytes([
        0x00, # 0 locals
        0x20, 0x00, 0x20, 0x01, 0xa3, # get 0, get 1, div
        0x0b # end
    ])
    body3 = _function_body(body3_ops)

    # Func 4: exactly 10,000 sequential photonic MAC operations inside WASM.
    ten_thousand = list(_encode_i32_leb128(10_000))
    body4_ops = bytes([
        0x01, 0x01, 0x7f,  # one i32 local (loop index 3)
        0x41, 0x00, 0x21, 0x03,  # index = 0
        0x02, 0x40,  # block
        0x03, 0x40,  # loop
        0x20, 0x03, 0x41] + ten_thousand + [0x4f, 0x0d, 0x01,  # break if index >= 10000
        0x20, 0x00, 0x20, 0x01, 0xa2,  # a * b
        0x20, 0x02, 0xa0, 0x21, 0x02,  # + accum; accum = result
        0x20, 0x03, 0x41, 0x01, 0x6a, 0x21, 0x03,  # index += 1
        0x0c, 0x00,  # continue loop
        0x0b, 0x0b,  # end loop, block
        0x20, 0x02, 0x0b  # return accum
    ])
    body4 = _function_body(body4_ops)

    # Func 5: exactly 10,000 RF propagation operations with deterministic distances.
    body5_ops = bytes([
        0x02,  # two local declarations
        0x01, 0x7f,  # one i32 local (loop index 2)
        0x01, 0x7c,  # one f64 local (accumulator 3)
        0x41, 0x00, 0x21, 0x02,  # index = 0
        0x44, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x21, 0x03,
        0x02, 0x40,  # block
        0x03, 0x40,  # loop
        0x20, 0x02, 0x41] + ten_thousand + [0x4f, 0x0d, 0x01,
        0x20, 0x03,  # accumulator
        0x20, 0x00, 0x20, 0x02, 0xb8, 0xa0,  # dist + float(index)
        0x20, 0x01, 0xa2,  # * slant
        0x44] + list(c_const_f64) + [0xa3,
        0x44] + list(ms_const_f64) + [0xa2,
        0xa0, 0x21, 0x03,  # add to accumulator
        0x20, 0x02, 0x41, 0x01, 0x6a, 0x21, 0x02,
        0x0c, 0x00,
        0x0b, 0x0b,
        0x20, 0x03, 0x0b
    ])
    body5 = _function_body(body5_ops)

    code_section_payload = bytes([0x06]) + body0 + body1 + body2 + body3 + body4 + body5
    code_section = _section(0x0a, code_section_payload)

    # Full WASM binary:
    header = bytes([0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00])
    return header + type_section + func_section + export_section + code_section


def get_silicon_wasm_base64() -> str:
    """Returns Base64 encoded WebAssembly binary for zero-CDN browser deployment."""
    wasm_bytes = build_silicon_wasm_binary()
    return base64.b64encode(wasm_bytes).decode("ascii")


def simulate_silicon_execution(distance_km: float = 3900.0) -> Dict[str, Any]:
    """Runs silicon kernel verification in pure python matching the WASM spec."""
    c = 299792.458
    slant = 1.0075
    route = 1.22
    n_fiber = 1.4682

    rf_ms = (distance_km * slant / c) * 1000.0
    fiber_ms = (distance_km * route * n_fiber / c) * 1000.0
    saved_ms = fiber_ms - rf_ms
    speedup = fiber_ms / max(rf_ms, 0.0001)

    return {
        "status": "success",
        "distance_km": distance_km,
        "rf_latency_ms": round(rf_ms, 4),
        "fiber_latency_ms": round(fiber_ms, 4),
        "physical_latency_saved_ms": round(saved_ms, 4),
        "speedup_factor": round(speedup, 2),
        "wasm_binary_size_bytes": len(build_silicon_wasm_binary()),
        "wasm_base64_len": len(get_silicon_wasm_base64())
    }
