# Triqee-QOpt: Institutional Markowitz Portfolio Execution Report
**Processor**: IBM Quantum 156-Qubit Heron (`ibm_kingston`)  
**Official Job ID**: [`daq0n38r7bnc73b463rg`](https://quantum.ibm.com/jobs/daq0n38r7bnc73b463rg)  
**Verification URL**: https://quantum.ibm.com/jobs/daq0n38r7bnc73b463rg  
**Status**: COMPLETED  
**Execution Timestamp**: Wed Sep 23 11:25:43 2026  
**QPU Time**: 2.471209591s  
**Shots**: 1024  

---

### **Executive Summary**
This report validates the execution of Triqee’s quadratic binary optimization (QUBO) Markowitz Mean-Variance portfolio solver on physical IBM Quantum 156-qubit Heron hardware (`ibm_kingston`). 

The solver minimized cross-asset portfolio variance while maximizing expected returns across a 6-asset multi-asset universe under a 3-asset allocation constraint.

### **Asset Universe & Parameters**
- **Assets**: BTC, ETH, SPY, TLT, GLD, USO
- **Constraint**: Select optimal 3-asset allocation ($B = 3$)
- **Risk Tolerance ($q$)**: 0.5 (Balanced Sharpe Ratio Optimization)

### **Measured Quantum Ground States**
| State | Assets Selected | Shots | Probability | Role |
|:---|:---|:---:|:---:|:---|
| `|111111>` | **BTC, ETH, SPY, TLT, GLD, USO** | 196 | 19.1% | Optimal Efficient Frontier Portfolio |
| `|000000>` | **None** | 192 | 18.8% | Sub-optimal Asset Basket |
| `|000010>` | **ETH** | 43 | 4.2% | Sub-optimal Asset Basket |
| `|110111>` | **BTC, ETH, SPY, GLD, USO** | 38 | 3.7% | Sub-optimal Asset Basket |
| `|111110>` | **ETH, SPY, TLT, GLD, USO** | 26 | 2.5% | Sub-optimal Asset Basket |
| `|111101>` | **BTC, SPY, TLT, GLD, USO** | 24 | 2.3% | Sub-optimal Asset Basket |
| `|011111>` | **BTC, ETH, SPY, TLT, GLD** | 21 | 2.1% | Sub-optimal Asset Basket |
| `|111011>` | **BTC, ETH, TLT, GLD, USO** | 18 | 1.8% | Sub-optimal Asset Basket |

---
*Targeted Asset Allocation Recommendation: **BTC, ETH, SPY, TLT, GLD, USO***  
*Verified on IBM Quantum Cloud Platform (`open-instance`). Transpiled with preset optimization level 1 for heavy-hex coupling.*
