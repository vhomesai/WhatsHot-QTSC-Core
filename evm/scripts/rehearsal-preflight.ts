import hre from "hardhat";
import {
  BASE_SEPOLIA_CHAIN_ID,
  requireTopology,
} from "./lib/config.js";
import { validateTopologySafes } from "./lib/safe.js";

const { ethers, networkName } = await hre.network.getOrCreate();
const network = await ethers.provider.getNetwork();
if (
  networkName !== "baseSepolia" ||
  network.chainId !== BASE_SEPOLIA_CHAIN_ID
) {
  throw new Error("Safe rehearsal preflight is restricted to Base Sepolia");
}

const topology = requireTopology(ethers);
await validateTopologySafes(ethers, ethers.provider, topology);

console.log("Base Sepolia topology preflight passed:");
console.log(`Owner Safe: ${topology.ownerSafe}`);
console.log(`Escrow Safe: ${topology.escrowSafe}`);
console.log(`Operations Safe: ${topology.operationsSafe}`);
console.log("Each Safe has the production owner set and a 2-of-3 threshold");
