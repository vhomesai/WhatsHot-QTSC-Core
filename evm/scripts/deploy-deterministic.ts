import hre from "hardhat";
import {
  BASE_SEPOLIA_CHAIN_ID,
  CONTRACT_NAME,
  DETERMINISTIC_DEPLOYMENT_PROXY,
  SEPOLIA_CONFIRMATION,
  deploymentFile,
  requireBytes32,
  requireTopology,
  writeJson,
  type DeploymentMetadata,
} from "./lib/config.js";
import { buildDeterministicDeployment } from "./lib/deterministic.js";
import { validateTopologySafes } from "./lib/safe.js";

const { ethers, networkName } = await hre.network.getOrCreate();
const network = await ethers.provider.getNetwork();
if (
  networkName !== "baseSepolia" ||
  network.chainId !== BASE_SEPOLIA_CHAIN_ID
) {
  throw new Error("Deterministic deployment is restricted to Base Sepolia");
}

const topology = requireTopology(ethers);
await validateTopologySafes(ethers, ethers.provider, topology);

const salt = requireBytes32(ethers, "QTSC_DEPLOYMENT_SALT");
const proxyCode = await ethers.provider.getCode(
  DETERMINISTIC_DEPLOYMENT_PROXY,
);
if (proxyCode === "0x") {
  throw new Error(
    "The deterministic deployment proxy is not deployed on Base Sepolia",
  );
}

const factory = await ethers.getContractFactory(CONTRACT_NAME);
const constructorArguments = [
  topology.ownerSafe,
  topology.escrowSafe,
  topology.operationsSafe,
] as const;
const deploymentTransaction = await factory.getDeployTransaction(
  ...constructorArguments,
);
if (deploymentTransaction.data === undefined) {
  throw new Error("Hardhat did not produce contract initialization bytecode");
}
const artifact = await hre.artifacts.readArtifact(CONTRACT_NAME);
const encodedArguments = ethers.AbiCoder.defaultAbiCoder().encode(
  ["address", "address", "address"],
  constructorArguments,
);
const deterministic = buildDeterministicDeployment(
  ethers,
  DETERMINISTIC_DEPLOYMENT_PROXY,
  salt,
  artifact.bytecode,
  encodedArguments,
);
if (deterministic.initCode.toLowerCase() !== deploymentTransaction.data.toLowerCase()) {
  throw new Error("Artifact and contract factory produced different init code");
}
const { initCode, initCodeHash, predictedAddress, proxyCalldata } =
  deterministic;
console.log(`Network: Base Sepolia (${network.chainId})`);
console.log(`Deterministic proxy: ${DETERMINISTIC_DEPLOYMENT_PROXY}`);
console.log(`Salt: ${salt}`);
console.log(`Predicted token: ${predictedAddress}`);
console.log(`Owner Safe: ${topology.ownerSafe}`);
console.log(`Escrow Safe: ${topology.escrowSafe}`);
console.log(`Operations Safe: ${topology.operationsSafe}`);

if ((await ethers.provider.getCode(predictedAddress)) !== "0x") {
  throw new Error(
    `Code already exists at ${predictedAddress}; run bytecode:base-sepolia against its reviewed metadata instead of rebroadcasting`,
  );
}
if (
  process.env.QTSC_SEPOLIA_DEPLOY_CONFIRMATION !== SEPOLIA_CONFIRMATION
) {
  throw new Error(
    `Preview only; set QTSC_SEPOLIA_DEPLOY_CONFIRMATION=${SEPOLIA_CONFIRMATION} after reviewing every value to permit the Base Sepolia broadcast`,
  );
}

const [deployer] = await ethers.getSigners();
const transaction = await deployer.sendTransaction({
  to: DETERMINISTIC_DEPLOYMENT_PROXY,
  data: proxyCalldata,
});
const receipt = await transaction.wait();
if (receipt === null || receipt.status !== 1) {
  throw new Error(`Base Sepolia deployment failed: ${transaction.hash}`);
}

const runtimeBytecode = await ethers.provider.getCode(predictedAddress);
if (runtimeBytecode === "0x") {
  throw new Error(
    `Deployment transaction succeeded but ${predictedAddress} has no code`,
  );
}

const metadata: DeploymentMetadata = {
  schemaVersion: 1,
  network: "base-sepolia",
  chainId: 84532,
  contract: CONTRACT_NAME,
  address: predictedAddress,
  transactionHash: transaction.hash,
  blockNumber: receipt.blockNumber,
  deployer: deployer.address,
  deploymentMethod: "deterministic-deployment-proxy",
  factory: DETERMINISTIC_DEPLOYMENT_PROXY,
  salt,
  constructorArguments: {
    initialOwner: topology.ownerSafe,
    initialEscrowTreasury: topology.escrowSafe,
    initialOperationalTreasury: topology.operationsSafe,
  },
  initCodeHash,
  creationBytecodeHash: ethers.keccak256(artifact.bytecode),
  runtimeBytecodeHash: ethers.keccak256(runtimeBytecode),
  compiler: {
    version: "0.8.28",
    optimizerEnabled: true,
    optimizerRuns: 1000,
    buildProfile: "production",
  },
  explorerVerification: {
    status: "not-attempted",
  },
};
writeJson(deploymentFile(), metadata);

console.log(`Deployed ${CONTRACT_NAME} at ${predictedAddress}`);
console.log(`Transaction: ${transaction.hash}`);
console.log(`Metadata: ${deploymentFile()}`);
