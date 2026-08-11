import path from "node:path";
import hre from "hardhat";
import {
  BASE_SEPOLIA_CHAIN_ID,
  CONTRACT_NAME,
  assertBaseSepolia,
  readDeployment,
  requireTopology,
  writeJson,
} from "./lib/config.js";
import { buildRehearsalActions } from "./lib/rehearsal.js";
import { validateTopologySafes } from "./lib/safe.js";

const { ethers, networkName } = await hre.network.getOrCreate();
const network = await ethers.provider.getNetwork();
assertBaseSepolia(networkName, network.chainId);

const topology = requireTopology(ethers);
await validateTopologySafes(ethers, ethers.provider, topology);
const deployment = readDeployment();
const token = await ethers.getContractAt(CONTRACT_NAME, deployment.address);
if (
  (await token.owner()).toLowerCase() !== topology.ownerSafe.toLowerCase() ||
  (await token.escrowTreasury()).toLowerCase() !==
    topology.escrowSafe.toLowerCase() ||
  (await token.operationalTreasury()).toLowerCase() !==
    topology.operationsSafe.toLowerCase()
) {
  throw new Error("The deployed token does not use the exact rehearsal topology");
}
if (await token.paused()) {
  throw new Error("The token must be unpaused before generating the rehearsal");
}
if ((await token.balanceOf(deployment.address)) !== 0n) {
  throw new Error(
    "The token contract must have zero deposited QTSC before the rehearsal",
  );
}

const amount = ethers.parseEther("100");
if ((await token.balanceOf(topology.ownerSafe)) < amount) {
  throw new Error("Owner Safe needs at least 100 QTSC for the deposit step");
}

const actions = buildRehearsalActions(
  token.interface,
  topology,
  deployment.address,
  amount,
);

const outputDirectory = path.resolve(
  process.env.QTSC_REHEARSAL_OUTPUT_DIR ?? "rehearsal-output",
);
for (const action of actions) {
  writeJson(path.join(outputDirectory, `${action.id}.json`), {
    version: "1.0",
    chainId: BASE_SEPOLIA_CHAIN_ID.toString(),
    createdAt: Date.now(),
    meta: {
      name: `QTSC Base Sepolia: ${action.id}`,
      description: action.description,
      txBuilderVersion: "1.18.0",
      createdFromSafeAddress: topology.ownerSafe,
      createdFromOwnerAddress: "",
    },
    transactions: [
      {
        to: deployment.address,
        value: "0",
        data: action.data,
        contractMethod: null,
        contractInputsValues: null,
      },
    ],
  });
}

writeJson(path.join(outputDirectory, "rehearsal-plan.json"), {
  schemaVersion: 1,
  chainId: Number(BASE_SEPOLIA_CHAIN_ID),
  contract: deployment.address,
  ownerSafe: topology.ownerSafe,
  escrowSafe: topology.escrowSafe,
  operationsSafe: topology.operationsSafe,
  productionOwners: topology.productionOwners,
  safeThreshold: 2,
  harvestAmount: amount.toString(),
  balancesBefore: {
    owner: (await token.balanceOf(topology.ownerSafe)).toString(),
    escrow: (await token.balanceOf(topology.escrowSafe)).toString(),
    operations: (await token.balanceOf(topology.operationsSafe)).toString(),
    contract: "0",
  },
  actions: actions.map(action => ({
    id: action.id,
    description: action.description,
    transactionBuilderFile: `${action.id}.json`,
  })),
});
writeJson(path.join(outputDirectory, "rehearsal-results.json"), {
  plan: "rehearsal-plan.json",
  transactionHashes: Object.fromEntries(
    actions.map(action => [action.id, null]),
  ),
});

console.log(`Wrote six separate Safe transactions to ${outputDirectory}`);
console.log(
  "Execute them in numeric order with two Safe owner confirmations each, then record each transaction hash in rehearsal-results.json",
);
