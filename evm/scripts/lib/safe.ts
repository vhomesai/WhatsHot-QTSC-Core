import type { Contract, Provider } from "ethers";
import type { ethers as EthersNamespace } from "ethers";
import type { Topology } from "./config.js";

const SAFE_ABI = [
  "function getOwners() view returns (address[])",
  "function getThreshold() view returns (uint256)",
];

type Ethers = typeof EthersNamespace;

export async function validateSafe(
  ethers: Ethers,
  provider: Provider,
  label: string,
  address: string,
  expectedOwners: string[],
): Promise<void> {
  if ((await provider.getCode(address)) === "0x") {
    throw new Error(`${label} is not a deployed contract on Base Sepolia`);
  }

  const safe = new ethers.Contract(address, SAFE_ABI, provider) as Contract;
  const threshold = (await safe.getThreshold()) as bigint;
  const owners = ((await safe.getOwners()) as string[]).map(owner =>
    ethers.getAddress(owner).toLowerCase(),
  );
  const expected = expectedOwners.map(owner => owner.toLowerCase()).sort();
  const actual = owners.sort();

  if (
    threshold !== 2n ||
    actual.length !== 3 ||
    actual.some((owner, index) => owner !== expected[index])
  ) {
    throw new Error(
      `${label} must be a 2-of-3 Safe with the production owner set`,
    );
  }
}

export async function validateTopologySafes(
  ethers: Ethers,
  provider: Provider,
  topology: Topology,
): Promise<void> {
  await validateSafe(
    ethers,
    provider,
    "Owner Safe",
    topology.ownerSafe,
    topology.productionOwners,
  );
  await validateSafe(
    ethers,
    provider,
    "Escrow Safe",
    topology.escrowSafe,
    topology.productionOwners,
  );
  await validateSafe(
    ethers,
    provider,
    "Operations Safe",
    topology.operationsSafe,
    topology.productionOwners,
  );
}
