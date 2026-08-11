import fs from "node:fs";
import { verifyContract } from "@nomicfoundation/hardhat-verify/verify";
import hre from "hardhat";
import {
  BASE_SEPOLIA_CHAIN_ID,
  CONTRACT_FQN,
  assertBaseSepolia,
  deploymentFile,
  readDeployment,
} from "./lib/config.js";

const { ethers, networkName } = await hre.network.getOrCreate();
const network = await ethers.provider.getNetwork();
assertBaseSepolia(networkName, network.chainId);

const metadata = readDeployment();
if ((await ethers.provider.getCode(metadata.address)) === "0x") {
  throw new Error("The metadata address has no code on Base Sepolia");
}

await verifyContract(
  {
    address: metadata.address,
    constructorArgs: [
      metadata.constructorArguments.initialOwner,
      metadata.constructorArguments.initialEscrowTreasury,
      metadata.constructorArguments.initialOperationalTreasury,
    ],
    contract: CONTRACT_FQN,
    provider: "etherscan",
  },
  hre,
);

metadata.explorerVerification = {
  status: "verified",
  provider: "etherscan",
};
fs.writeFileSync(
  deploymentFile(),
  `${JSON.stringify(metadata, null, 2)}\n`,
  "utf8",
);
console.log(`Verified ${metadata.address} using the Etherscan/BaseScan API`);
