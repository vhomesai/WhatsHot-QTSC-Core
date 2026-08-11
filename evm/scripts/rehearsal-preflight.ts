import hre from "hardhat";
import {
  assertBaseSepolia,
  requireTopology,
} from "./lib/config.js";
import { validateTopologySafes } from "./lib/safe.js";

const { ethers, networkName } = await hre.network.getOrCreate();
const network = await ethers.provider.getNetwork();
assertBaseSepolia(networkName, network.chainId);

const topology = requireTopology(ethers);
await validateTopologySafes(ethers, ethers.provider, topology);

console.log("Base Sepolia topology preflight passed:");
console.log(`Owner Safe: ${topology.ownerSafe}`);
console.log(`Escrow Safe: ${topology.escrowSafe}`);
console.log(`Operations Safe: ${topology.operationsSafe}`);
console.log("Each Safe has the production owner set and a 2-of-3 threshold");
