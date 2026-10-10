# Triqee Quantum Labs: Hardware Execution Report
**Processor**: IBM Quantum 156-Qubit Heron (`ibm_marrakesh`)  
**Official Job ID**: [`dapu6pb18flc739mtlj0`](https://quantum.ibm.com/jobs/dapu6pb18flc739mtlj0)  
**Verification URL**: https://quantum.ibm.com/jobs/dapu6pb18flc739mtlj0  
**Status**: COMPLETED  
**Execution Timestamp**: Wed Sep 23 08:35:39 2026  
**Shots**: 1024  

## Problem Formulation: Same-Game Parlay (SGP) Covariance QUBO
- **Leg 0**: Wyoming Cowboys (-3.5 Spread)
- **Leg 1**: Game Total (Over 48.5)
- **Leg 2**: QB Passing Yards (Over 225.5)
- **Leg 3**: RB Anytime Touchdown

### Empirical Gaussian Copula Covariances Mapped to Ising Couplings ($J_{ij}$):
- $J_{0,1} = +0.35$ (Spread & Total)
- $J_{1,2} = +0.55$ (Total & Passing Yards)
- $J_{0,3} = +0.24$ (Spread & Rushing TD)
- $J_{2,3} = -0.18$ (Passing Yards & Rushing TD Cannibalization)

## Measured Quantum Ground States
| State | Shots | Probability | Hedging Action |
|:---|:---:|:---:|:---|
| `|1111>` | 158 | 15.4% | Optimal Balanced Risk Vector |
| `|0111>` | 153 | 14.9% | Sub-optimal Portfolio |
| `|0100>` | 104 | 10.2% | Sub-optimal Portfolio |
| `|0101>` | 89 | 8.7% | Sub-optimal Portfolio |
| `|0000>` | 79 | 7.7% | Sub-optimal Portfolio |
| `|0110>` | 76 | 7.4% | Sub-optimal Portfolio |
| `|1101>` | 58 | 5.7% | Sub-optimal Portfolio |
| `|1000>` | 54 | 5.3% | Sub-optimal Portfolio |

---
*Verified on IBM Quantum Cloud Runtime (`open-instance`). Transpiled with preset optimization level 1 for heavy-hex coupling.*
