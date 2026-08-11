import fs from "node:fs";
import path from "node:path";
import type { TransactionReceipt } from "ethers";
import hre from "hardhat";
import {
  BASE_SEPOLIA_CHAIN_ID,
  CONTRACT_NAME,
  assertBaseSepolia,
  requireTopology,
} from "./lib/config.js";
import { validateTopologySafes } from "./lib/safe.js";

const actionIds = [
  "01-pause",
  "02-unpause",
  "03-update-treasuries",
  "04-restore-treasuries",
  "05-deposit",
  "06-harvest",
] as const;

interface RehearsalPlan {
  chainId: number;
  contract: string;
  ownerSafe: string;
  escrowSafe: string;
  operationsSafe: string;
  productionOwners: string[];
  safeThreshold: number;
  harvestAmount: string;
  balancesBefore: {
    owner: string;
    escrow: string;
    operations: string;
    contract: string;
  };
}

interface RehearsalResults {
  plan: string;
  transactionHashes: Record<(typeof actionIds)[number], string | null>;
}

const { ethers, networkName } = await hre.network.getOrCreate();
const network = await ethers.provider.getNetwork();
assertBaseSepolia(networkName, network.chainId);
const topology = requireTopology(ethers);
await validateTopologySafes(ethers, ethers.provider, topology);

const resultsFile = path.resolve(
  process.env.QTSC_REHEARSAL_RESULTS ??
    "rehearsal-output/rehearsal-results.json",
);
const results = JSON.parse(
  fs.readFileSync(resultsFile, "utf8"),
) as RehearsalResults;
const plan = JSON.parse(
  fs.readFileSync(path.resolve(path.dirname(resultsFile), results.plan), "utf8"),
) as RehearsalPlan;
if (
  plan.chainId !== Number(BASE_SEPOLIA_CHAIN_ID) ||
  plan.ownerSafe.toLowerCase() !== topology.ownerSafe.toLowerCase() ||
  plan.escrowSafe.toLowerCase() !== topology.escrowSafe.toLowerCase() ||
  plan.operationsSafe.toLowerCase() !== topology.operationsSafe.toLowerCase()
) {
  throw new Error("Rehearsal plan does not match the current exact topology");
}

const token = await ethers.getContractAt(CONTRACT_NAME, plan.contract);
const receipts: TransactionReceipt[] = [];
for (const id of actionIds) {
  const hash = results.transactionHashes[id];
  if (hash === null || !ethers.isHexString(hash, 32)) {
    throw new Error(`Record the confirmed Base Sepolia hash for ${id}`);
  }
  const receipt = await ethers.provider.getTransactionReceipt(hash);
  if (receipt === null || receipt.status !== 1) {
    throw new Error(`${id} has no successful Base Sepolia receipt`);
  }
  const transaction = await ethers.provider.getTransaction(hash);
  if (
    transaction?.to?.toLowerCase() !== topology.ownerSafe.toLowerCase()
  ) {
    throw new Error(`${id} was not executed through the Owner Safe`);
  }
  receipts.push(receipt);
}
for (let index = 1; index < receipts.length; index += 1) {
  const previous = receipts[index - 1];
  const current = receipts[index];
  if (
    current.blockNumber < previous.blockNumber ||
    (current.blockNumber === previous.blockNumber &&
      current.index <= previous.index)
  ) {
    throw new Error("Rehearsal transactions were not executed in plan order");
  }
}

function parsedEvents(receiptIndex: number, name: string) {
  return receipts[receiptIndex].logs
    .filter(log => log.address.toLowerCase() === plan.contract.toLowerCase())
    .flatMap(log => {
      try {
        const parsed = token.interface.parseLog(log);
        return parsed?.name === name ? [parsed] : [];
      } catch {
        return [];
      }
    });
}

const pauseEvents = parsedEvents(0, "Paused");
if (
  pauseEvents.length !== 1 ||
  pauseEvents[0].args.account.toLowerCase() !==
    topology.ownerSafe.toLowerCase()
) {
  throw new Error("Pause transaction did not emit exactly one Paused event");
}
const unpauseEvents = parsedEvents(1, "Unpaused");
if (
  unpauseEvents.length !== 1 ||
  unpauseEvents[0].args.account.toLowerCase() !==
    topology.ownerSafe.toLowerCase()
) {
  throw new Error("Unpause transaction did not emit exactly one Unpaused event");
}
const updates = [
  parsedEvents(2, "TreasuriesUpdated"),
  parsedEvents(3, "TreasuriesUpdated"),
];
if (
  updates[0].length !== 1 ||
  updates[0][0].args.previousEscrowTreasury.toLowerCase() !==
    topology.escrowSafe.toLowerCase() ||
  updates[0][0].args.newEscrowTreasury.toLowerCase() !==
    topology.ownerSafe.toLowerCase() ||
  updates[0][0].args.previousOperationalTreasury.toLowerCase() !==
    topology.operationsSafe.toLowerCase() ||
  updates[0][0].args.newOperationalTreasury.toLowerCase() !==
    topology.operationsSafe.toLowerCase() ||
  updates[1].length !== 1 ||
  updates[1][0].args.previousEscrowTreasury.toLowerCase() !==
    topology.ownerSafe.toLowerCase() ||
  updates[1][0].args.newEscrowTreasury.toLowerCase() !==
    topology.escrowSafe.toLowerCase() ||
  updates[1][0].args.previousOperationalTreasury.toLowerCase() !==
    topology.operationsSafe.toLowerCase() ||
  updates[1][0].args.newOperationalTreasury.toLowerCase() !==
    topology.operationsSafe.toLowerCase()
) {
  throw new Error("Treasury update and restoration events are incorrect");
}
const amount = BigInt(plan.harvestAmount);
const deposits = parsedEvents(4, "Transfer");
if (
  deposits.length !== 1 ||
  deposits[0].args.from.toLowerCase() !== topology.ownerSafe.toLowerCase() ||
  deposits[0].args.to.toLowerCase() !== plan.contract.toLowerCase() ||
  deposits[0].args.value !== amount
) {
  throw new Error("Token deposit event is incorrect");
}
const harvests = parsedEvents(5, "HarvestSweepExecuted");
if (
  harvests.length !== 1 ||
  harvests[0].args.amount !== amount ||
  harvests[0].args.escrowShare !== amount / 4n ||
  harvests[0].args.operationalShare !== (amount * 3n) / 4n
) {
  throw new Error("Harvest event does not prove the exact 25/75 split");
}

const initialSupply = await token.INITIAL_SUPPLY();
if (
  (await token.owner()).toLowerCase() !== topology.ownerSafe.toLowerCase() ||
  (await token.escrowTreasury()).toLowerCase() !==
    topology.escrowSafe.toLowerCase() ||
  (await token.operationalTreasury()).toLowerCase() !==
    topology.operationsSafe.toLowerCase() ||
  (await token.paused()) ||
  (await token.balanceOf(plan.contract)) !==
    BigInt(plan.balancesBefore.contract) ||
  (await token.balanceOf(topology.ownerSafe)) !==
    BigInt(plan.balancesBefore.owner) - amount ||
  (await token.balanceOf(topology.escrowSafe)) !==
    BigInt(plan.balancesBefore.escrow) + amount / 4n ||
  (await token.balanceOf(topology.operationsSafe)) !==
    BigInt(plan.balancesBefore.operations) + (amount * 3n) / 4n ||
  (await token.totalSupply()) !== initialSupply
) {
  throw new Error("Final QTSC topology or token state invariant failed");
}

console.log("Exact-topology Base Sepolia rehearsal passed");
console.log("All six actions were executed through the 2-of-3 Owner Safe");
