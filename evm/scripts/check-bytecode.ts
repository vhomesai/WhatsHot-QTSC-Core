import hre from "hardhat";
import {
  BASE_SEPOLIA_CHAIN_ID,
  CONTRACT_NAME,
  DETERMINISTIC_DEPLOYMENT_PROXY,
  readDeployment,
} from "./lib/config.js";
import {
  assertRuntimeMatch,
  flattenReferences,
  type ByteRange,
} from "./lib/bytecode.js";
import { buildDeterministicDeployment } from "./lib/deterministic.js";

interface ArtifactReferences {
  linkReferences: Record<string, Record<string, ByteRange[]>>;
  deployedLinkReferences: Record<string, Record<string, ByteRange[]>>;
  immutableReferences: Record<string, ByteRange[]>;
}

const { ethers, networkName } = await hre.network.getOrCreate();
const network = await ethers.provider.getNetwork();
if (
  networkName !== "baseSepolia" ||
  network.chainId !== BASE_SEPOLIA_CHAIN_ID
) {
  throw new Error("Bytecode checks are restricted to Base Sepolia");
}

const metadata = readDeployment();
if (
  metadata.chainId !== Number(BASE_SEPOLIA_CHAIN_ID) ||
  metadata.network !== "base-sepolia" ||
  metadata.deploymentMethod !== "deterministic-deployment-proxy" ||
  metadata.factory.toLowerCase() !==
    DETERMINISTIC_DEPLOYMENT_PROXY.toLowerCase()
) {
  throw new Error("Deployment metadata does not describe the approved path");
}

const artifact = await hre.artifacts.readArtifact(CONTRACT_NAME);
const references = artifact as typeof artifact & ArtifactReferences;
const creationLinks = flattenReferences(
  references.linkReferences,
);
const runtimeLinks = flattenReferences(
  references.deployedLinkReferences,
);
if (creationLinks.length > 0 || runtimeLinks.length > 0) {
  throw new Error(
    "Linked libraries require explicit reviewed library addresses; none are configured for QTSC",
  );
}

const encodedArguments = ethers.AbiCoder.defaultAbiCoder().encode(
  ["address", "address", "address"],
  [
    metadata.constructorArguments.initialOwner,
    metadata.constructorArguments.initialEscrowTreasury,
    metadata.constructorArguments.initialOperationalTreasury,
  ],
);
const deterministic = buildDeterministicDeployment(
  ethers,
  metadata.factory,
  metadata.salt,
  artifact.bytecode,
  encodedArguments,
);
const { initCode } = deterministic;
if (ethers.keccak256(artifact.bytecode) !== metadata.creationBytecodeHash) {
  throw new Error("Recorded creation-bytecode hash does not match the artifact");
}
if (ethers.keccak256(initCode) !== metadata.initCodeHash) {
  throw new Error(
    "Constructor arguments plus creation bytecode do not match the recorded init-code hash",
  );
}

const predictedAddress = deterministic.predictedAddress;
if (predictedAddress.toLowerCase() !== metadata.address.toLowerCase()) {
  throw new Error("Recorded contract address is not the CREATE2 result");
}

const transaction = await ethers.provider.getTransaction(
  metadata.transactionHash,
);
if (transaction === null) {
  throw new Error("Recorded deployment transaction was not found");
}
if (
  transaction.to?.toLowerCase() !== metadata.factory.toLowerCase() ||
  transaction.data.toLowerCase() !==
    deterministic.proxyCalldata.toLowerCase()
) {
  throw new Error(
    "Deployment transaction does not contain the recorded salt and exact constructor init code",
  );
}

const actualRuntime = await ethers.provider.getCode(metadata.address);
if (actualRuntime === "0x") {
  throw new Error("No runtime bytecode exists at the recorded address");
}
const immutableReferences = Object.values(
  references.immutableReferences,
).flat();
assertRuntimeMatch(
  artifact.deployedBytecode,
  actualRuntime,
  immutableReferences,
);
if (ethers.keccak256(actualRuntime) !== metadata.runtimeBytecodeHash) {
  throw new Error("Recorded runtime-bytecode hash does not match on-chain code");
}

console.log(`Creation bytecode: ${metadata.creationBytecodeHash}`);
console.log(`Init code: ${metadata.initCodeHash}`);
console.log(`Runtime bytecode: ${metadata.runtimeBytecodeHash}`);
console.log(`Immutable ranges accounted for: ${immutableReferences.length}`);
console.log("Base Sepolia bytecode proof passed");
