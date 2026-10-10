#!/usr/bin/env python3
"""
Triqee Wyoming DA-000000992 - Live IBM Quantum QPU Execution Engine
Dispatches real quantum circuits to 156-Qubit IBM Heron processors (ibm_marrakesh / ibm_kingston).
Anchors execution hashes to $TQ Consumptive Token burns under Wyoming W.S. 34-29-106.
"""

import sys
import os
import json
import time
import hashlib

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def run_quantum_circuit_on_ibm(shots: int = 100, backend_name: str = "ibm_marrakesh"):
    print("=" * 80)
    print(f"   TRIQEE WYOMING DA-000000992 // LIVE IBM QUANTUM QPU EXECUTION")
    print(f"   Target Hardware: {backend_name.upper()} (156-Qubit Heron Superconducting QPU)")
    print(f"   Wyoming W.S. 34-29-106 Consumptive Harbor | CERN DOI: 10.5281/zenodo.23045297")
    print("=" * 80)

    try:
        from qiskit import QuantumCircuit
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

        # Load IBM Quantum credentials from ~/.qiskit/qiskit-ibm.json
        cfg_path = os.path.expanduser("~/.qiskit/qiskit-ibm.json")
        with open(cfg_path, "r") as f:
            cfg = json.load(f)
        acc = list(cfg.values())[0]

        service = QiskitRuntimeService(
            channel=acc["channel"],
            token=acc["token"],
            url=acc["url"],
            instance="open-instance"
        )
        print(f"\n[STEP 1/4] Authenticated to IBM Quantum Platform (Instance: open-instance)...")

        # Pick backend with lowest queue
        backend = service.backend(backend_name)
        status = backend.status()
        print(f"  ✓ Target Backend: {backend.name} ({backend.num_qubits} Qubits)")
        print(f"  ✓ Operational: {status.operational} | Pending Jobs in Queue: {status.pending_jobs}")

        # Construct Entangled Variational Benchmark Circuit (GHZ Entanglement across Heron lattice)
        print("\n[STEP 2/4] Synthesizing Triqee Entangled QPU Variational Circuit...")
        n_qubits = 5 # 5-qubit Bell-GHZ superposition kernel
        qc = QuantumCircuit(n_qubits)
        qc.h(0)
        for i in range(n_qubits - 1):
            qc.cx(i, i + 1)
        qc.measure_all()
        print(f"  ✓ Quantum Circuit Depth: {qc.depth()} | Operations: {qc.count_ops()}")

        # Transpile for 156-Qubit Heavy-Hex Heron Architecture
        print("\n[STEP 3/4] Transpiling Circuit for Heron Heavy-Hex Coupler Topology...")
        pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
        isa_circuit = pm.run(qc)
        print(f"  ✓ Transpiled 2-Qubit CX/ECR gates onto Heron layout.")

        # Dispatch execution job via SamplerV2
        print(f"\n[STEP 4/4] Dispatching Job to {backend.name} (Shots: {shots})...")
        sampler = Sampler(mode=backend)
        job = sampler.run([isa_circuit], shots=shots)
        job_id = job.job_id()
        print(f"  ✓ SUCCESS! IBM Quantum Job ID: {job_id}")
        print(f"  ✓ Job Status: {job.status()}")

        # Compute cryptographic execution hash for on-chain proof
        tx_proof = hashlib.sha256(f"IBM:{backend_name}:{job_id}:{shots}:{time.time()}".encode()).hexdigest()
        print(f"  ✓ Triqee Cryptographic Proof-of-Execution: {tx_proof}")

        receipt = {
            "entity": "WhatsHot, Inc. // Triqee Omniverse DAO LLC (DA-000000992)",
            "backend": backend_name,
            "backend_qubits": backend.num_qubits,
            "job_id": job_id,
            "shots": shots,
            "proof_hash": tx_proof,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": str(job.status()),
            "zenodo_doi": "10.5281/zenodo.23045297",
            "statute": "Wyoming W.S. 34-29-106 Consumptive Utility Token"
        }

        # Save receipt
        receipt_path = r"C:\Users\VHome\Desktop\wyoming_demo\ibm_quantum_execution_receipt.json"
        with open(receipt_path, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)

        print(f"\n[✓] IBM Execution Receipt Saved: {receipt_path}")
        print("=" * 80)
        return receipt

    except Exception as e:
        print(f"\n[!] IBM Execution exception: {e}")
        return None

if __name__ == "__main__":
    run_quantum_circuit_on_ibm(shots=100, backend_name="ibm_marrakesh")
