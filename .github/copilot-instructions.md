# GitHub Copilot Custom Instructions for Triqee™ Sovereign Superintelligence (SI)

You are assisting with the development, testing, and mathematical verification of the **Triqee™ Sovereign Superintelligence (SI) & Cockpit** codebase.

## 🌌 Core Domain & Physics Grounding Invariants
All mathematical, physical, and quantum calculations MUST strictly obey the following exact physical constants:
1. **Speed of Light in Vacuum / Free-Space RF**:
   $$c = 299,792.458\text{ km/s}$$ (Never approximate to $300,000\text{ km/s}$).
2. **Optical Fiber Refractive Index**:
   $$n_{\text{fiber}} = 1.4682$$ (Standard Corning SMF-28 fused silica).
3. **Earth Radius for Haversine Great-Circle Calculations**:
   $$R_{\text{Earth}} = 6,371.0\text{ km}$$.
4. **Relativistic Geodesic Advantage**:
   $$\Delta t = \left( \frac{d \cdot f_{\text{route}} \cdot n_{\text{fiber}}}{c} \right) - \left( \frac{d \cdot f_{\text{slant}}}{c} \right)$$
5. **Photonic Energy Efficiency**:
   OptoTensor™ operates at $0.04\text{ fJ/MAC}$ modulation efficiency at $100\text{ GHz}$.
6. **Quantum QPU Backend Topologies**:
   - **IBM Heron**: 156 Qubits, Heavy-Hex lattice, superconducting transmon.
   - **IonQ Forte**: 36 Algorithmic Qubits, All-to-All trapped-ion connectivity (0% SWAP overhead).
   - **Rigetti Ankaa**: 84 Qubits, Square lattice tunable couplers.
   - **QuEra Aquila**: 256 Neutral atoms, Rydberg Hamiltonian simulation.

## 📜 Statutory & Compliance Invariants
- **Wyoming Token Law**: Wyoming W.S. § 34-29-106 (Open Blockchain Consumptive Utility Token).
- **CERN Zenodo DOI**: `10.5281/zenodo.23045297`.
- **Settlement Layer**: Base Layer 2 (Coinbase L2 Ethereum Rollup).

## 💻 Architecture & Code Guidelines
1. **Zero External CDN Dependencies**: All UI styling and JavaScript must remain 100% self-contained inside single-file distributions (`triqee_si_chatbot.html`).
2. **Audio & Silicon Acceleration**: Use the native Web Audio API for polyphonic synthesis and WebAssembly (WASM 1.0 bytecode) for sub-$250\text{ µs}$ client-side tensor ops.
3. **Backend Stack**: Python 3.12+, FastAPI REST, SQLite3 parameterized transactions (`db_manager.py`), Pytest (`100% pass rate across all test suites`).
4. **Markdown & LaTeX Safety**: Never leave unescaped `$` currency symbols in prose; use `\$` or wrap in backticks.
