"""
Triqee CLI Entrypoint
"""

import sys
from .router import ArbitrageRouter
from . import __version__, __doi__

def main():
    print(f"Triqee Sovereign Quantum SDK v{__version__}")
    print(f"CERN Zenodo DOI: {__doi__}")
    print("Commands: route, quantvault, health")
    if len(sys.argv) > 1 and sys.argv[1] == "route":
        router = ArbitrageRouter()
        dec = router.route(16, 120, "Dense QUBO")
        print(f"Default 16Q QUBO Route: {dec.selected_modality} (Depth {dec.estimated_circuit_depth}, {dec.swap_overhead} SWAPs)")
    else:
        print("Run 'triqee route' for default arbitrage routing.")

if __name__ == "__main__":
    main()
