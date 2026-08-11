import type { ethers as EthersNamespace } from "ethers";
import fs from "node:fs";
import path from "node:path";

export const BASE_SEPOLIA_CHAIN_ID = 84532n;
export const DETERMINISTIC_DEPLOYMENT_PROXY =
  "0x4e59b44847b379578588920cA78FbF26c0B4956C";
export const CONTRACT_NAME = "QTSCKernelToken";
export const CONTRACT_FQN =
  "contracts/QTSCKernelToken.sol:QTSCKernelToken";
export const SEPOLIA_CONFIRMATION = "DEPLOY_QTSC_TO_BASE_SEPOLIA";

export interface Topology {
  ownerSafe: string;
  escrowSafe: string;
  operationsSafe: string;
  productionOwners: string[];
}

export interface DeploymentMetadata {
  schemaVersion: 1;
  network: "base-sepolia";
  chainId: 84532;
  contract: typeof CONTRACT_NAME;
  address: string;
  transactionHash: string;
  blockNumber: number;
  deployer: string;
  deploymentMethod: "deterministic-deployment-proxy";
  factory: string;
  salt: string;
  constructorArguments: {
    initialOwner: string;
    initialEscrowTreasury: string;
    initialOperationalTreasury: string;
  };
  initCodeHash: string;
  creationBytecodeHash: string;
  runtimeBytecodeHash: string;
  compiler: {
    version: "0.8.28";
    optimizerEnabled: true;
    optimizerRuns: 1000;
    buildProfile: "production";
  };
  explorerVerification: {
    status: "not-attempted" | "verified";
    provider?: "etherscan";
  };
}

type Ethers = typeof EthersNamespace;

export function assertBaseSepolia(
  networkName: string,
  chainId: bigint,
): void {
  if (
    networkName !== "baseSepolia" ||
    chainId !== BASE_SEPOLIA_CHAIN_ID
  ) {
    throw new Error(
      `Base Mainnet and all non-Sepolia networks are disabled; received ${networkName} (${chainId})`,
    );
  }
}

export function requireAddress(
  ethers: Ethers,
  name: string,
): string {
  const value = process.env[name];
  if (
    value === undefined ||
    !ethers.isAddress(value) ||
    value === ethers.ZeroAddress
  ) {
    throw new Error(`${name} must be a non-zero EVM address`);
  }
  return ethers.getAddress(value);
}

export function requireBytes32(ethers: Ethers, name: string): string {
  const value = process.env[name];
  if (value === undefined || !ethers.isHexString(value, 32)) {
    throw new Error(`${name} must be a 32-byte 0x-prefixed hex value`);
  }
  return value.toLowerCase();
}

export function requireTopology(ethers: Ethers): Topology {
  const ownerSafe = requireAddress(ethers, "QTSC_OWNER_SAFE");
  const escrowSafe = requireAddress(ethers, "QTSC_ESCROW_SAFE");
  const operationsSafe = requireAddress(ethers, "QTSC_OPERATIONS_SAFE");
  const safes = [ownerSafe, escrowSafe, operationsSafe];
  if (new Set(safes.map(address => address.toLowerCase())).size !== 3) {
    throw new Error("Owner, Escrow, and Operations Safes must be distinct");
  }

  const rawOwners = process.env.QTSC_PRODUCTION_SAFE_OWNERS;
  if (rawOwners === undefined) {
    throw new Error(
      "QTSC_PRODUCTION_SAFE_OWNERS must contain the three production owners",
    );
  }
  const owners = rawOwners.split(",").map(owner => owner.trim());
  if (
    owners.length !== 3 ||
    new Set(owners.map(owner => owner.toLowerCase())).size !== 3
  ) {
    throw new Error(
      "QTSC_PRODUCTION_SAFE_OWNERS must contain three unique addresses",
    );
  }

  return {
    ownerSafe,
    escrowSafe,
    operationsSafe,
    productionOwners: owners.map((owner, index) => {
      if (
        !ethers.isAddress(owner) ||
        owner.toLowerCase() === ethers.ZeroAddress
      ) {
        throw new Error(
          `QTSC_PRODUCTION_SAFE_OWNERS has an invalid address at index ${index}`,
        );
      }
      return ethers.getAddress(owner);
    }),
  };
}

export function deploymentFile(): string {
  return path.resolve(
    process.env.QTSC_DEPLOYMENT_FILE ??
      "deployments/base-sepolia-rehearsal.json",
  );
}

export function readDeployment(): DeploymentMetadata {
  const file = deploymentFile();
  if (!fs.existsSync(file)) {
    throw new Error(
      `Deployment metadata not found at ${file}; deploy or provide the reviewed file`,
    );
  }
  return JSON.parse(fs.readFileSync(file, "utf8")) as DeploymentMetadata;
}

export function writeJson(file: string, value: unknown): void {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, {
    encoding: "utf8",
    flag: "wx",
  });
}
