# QTSC EVM operations

This module contains the neutral `QTSCKernelToken` implementation and the tooling needed to prove a Base Sepolia rehearsal. Nothing in this module authorizes or performs a Base Mainnet broadcast.

## Deployment policy

The canonical deployment path is the deterministic deployment proxy at:

```text
0x4e59b44847b379578588920cA78FbF26c0B4956C
```

The earlier direct-EOA deployment script conflicted with the stated deterministic-factory requirement. It has been replaced. The deployment script now:

1. Refuses every network except Base Sepolia (`84532`).
2. Validates three distinct deployed Safes.
3. Validates the production three-owner set and a 2-of-3 threshold on every Safe.
4. Builds the constructor init code from the production compiler artifact.
5. Derives and displays the deterministic address through the proxy.
6. Requires the exact Sepolia confirmation phrase before broadcasting.
7. Writes factual deployment metadata only after a successful receipt and code check.

There is no Base Mainnet network, command, RPC URL, confirmation phrase, or deploy script in this repository. A future Mainnet procedure must be added only after every blocker below is independently cleared and reviewed.

## Deterministic build

Requirements: Node.js 22 and npm.

```powershell
cd evm
npm ci
npm run compile
npm test
npm run typecheck
```

Production compilation is pinned to Solidity `0.8.28`, optimizer enabled with 1,000 runs. Dependencies and compiler packages are pinned by `package-lock.json`.

## Required Base Sepolia inputs

Copy the names from `.env.example` into the current shell. Do not commit `.env`, keys, API credentials, Safe addresses, transaction hashes, or generated rehearsal files.

| Input | Requirement |
|---|---|
| `BASE_SEPOLIA_RPC_URL` | Trusted Base Sepolia RPC |
| `DEPLOYER_PRIVATE_KEY` | Funded testnet-only deployer key |
| `ETHERSCAN_API_KEY` | Etherscan V2/BaseScan-compatible verification key |
| `QTSC_OWNER_SAFE` | Base Sepolia Owner Safe |
| `QTSC_ESCROW_SAFE` | Different Base Sepolia Escrow Safe |
| `QTSC_OPERATIONS_SAFE` | Different Base Sepolia Operations Safe |
| `QTSC_PRODUCTION_SAFE_OWNERS` | Three full production owner addresses, comma-separated |
| `QTSC_DEPLOYMENT_SALT` | Reviewed, stable `bytes32` salt |

All three Safes must be deployed on Base Sepolia, use the exact production owner set, and have threshold 2. The scripts reject abbreviated, zero, duplicate, undeployed, wrong-owner, and wrong-threshold inputs.

## Exact-topology rehearsal

### 1. Fund and deploy the testnet topology

User action is required:

1. Create three distinct Base Sepolia Safes named for Owner, Escrow, and Operations.
2. Configure each with the exact three production owners and threshold 2-of-3.
3. Fund only the testnet deployer and Safes with enough Base Sepolia ETH.
4. Export the required values in the local shell.

Run the read-only check:

```powershell
npm run rehearsal:preflight
```

Run the deployment command once without the confirmation variable. It prints
the factory, salt, predicted address, and all three Safes, then stops before
broadcasting:

```powershell
npm run deploy:base-sepolia
```

Review every printed value, then explicitly set:

```powershell
$env:QTSC_SEPOLIA_DEPLOY_CONFIRMATION = "DEPLOY_QTSC_TO_BASE_SEPOLIA"
npm run deploy:base-sepolia
```

This is the only command that broadcasts a deployment. It is Base Sepolia-only.

### 2. Prove bytecode and verify source

```powershell
npm run bytecode:base-sepolia
npm run verify:base-sepolia
```

`bytecode:base-sepolia` proves all of the following:

- the production artifact's creation-bytecode hash;
- ABI-encoded constructor arguments and resulting init-code hash;
- the deterministic proxy calldata (`salt || init code`);
- the CREATE2-derived address;
- the exact on-chain runtime bytecode and recorded hash;
- linked-library references (the script stops unless explicit library addresses are introduced);
- compiler-reported immutable ranges, which are masked only at their exact offsets.

`verify:base-sepolia` uses the maintained `@nomicfoundation/hardhat-verify` plugin and Etherscan V2/BaseScan. It updates metadata to `verified` only after the provider reports success. A command run, metadata file, or this document is not evidence of explorer verification by itself.

### 3. Execute the manual 2-of-3 Safe workflow

Generate six separate Safe Transaction Builder files:

```powershell
npm run rehearsal:plan
```

Import and execute each numbered file from `rehearsal-output/` through the **Owner Safe**, in order. Each transaction requires confirmations from two production owners:

1. Pause.
2. Unpause.
3. Temporarily update Escrow to the Owner Safe.
4. Restore the exact Escrow and Operations Safes.
5. Deposit 100 QTSC from the Owner Safe into the token contract.
6. Manually execute the 100 QTSC harvest, producing 25 QTSC for Escrow and 75 QTSC for Operations.

Do not batch, reorder, or automate these actions. Record each successful Base Sepolia transaction hash in `rehearsal-output/rehearsal-results.json`, then run:

```powershell
npm run rehearsal:check
```

The checker validates transaction order, successful receipts, execution through the Owner Safe, pause/unpause events, both treasury updates, deposit event, exact 25/75 harvest event, restored topology, unpaused state, and zero residual deposited balance.

## Evidence and metadata

`deployments/base-sepolia.json` is created only by a successful deterministic deployment. Commit it after reviewing every full address and transaction hash. Generated Safe transaction files and locally entered results remain gitignored.

Do not copy the previous Sepolia record into this directory: that deployment used the same address for Escrow and Operations and therefore is not evidence of the required three-Safe topology.

## Remaining Mainnet blockers

Base Mainnet remains blocked until all of these are complete:

- an independent professional security audit, with findings resolved and a final report;
- a successful exact-topology Base Sepolia rehearsal proven by the checker;
- successful Base Sepolia source verification;
- reviewed deployment and bytecode metadata;
- explicit human approval of a separately reviewed Mainnet procedure.

AI review, unit tests, bytecode matching, and a testnet rehearsal do **not** replace the independent professional audit.

Harvesting remains manual and Owner-Safe-only. Unattended harvest automation is intentionally absent.
