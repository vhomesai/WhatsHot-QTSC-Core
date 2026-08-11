import { expect } from "chai";
import hre from "hardhat";
import {
  DETERMINISTIC_DEPLOYMENT_PROXY,
  assertBaseSepolia,
  type Topology,
} from "../scripts/lib/config.js";
import { buildDeterministicDeployment } from "../scripts/lib/deterministic.js";
import { buildRehearsalActions } from "../scripts/lib/rehearsal.js";

describe("deployment and rehearsal tooling", function () {
  it("unconditionally rejects Base Mainnet chain ID 8453", function () {
    expect(() => assertBaseSepolia("baseMainnet", 8453n)).to.throw(
      "Base Mainnet and all non-Sepolia networks are disabled",
    );
    expect(() => assertBaseSepolia("baseSepolia", 8453n)).to.throw(
      "Base Mainnet and all non-Sepolia networks are disabled",
    );
  });

  it("accepts only the configured Base Sepolia network", function () {
    expect(() => assertBaseSepolia("baseSepolia", 84532n)).not.to.throw();
    expect(() => assertBaseSepolia("hardhat", 84532n)).to.throw(
      "Base Mainnet and all non-Sepolia networks are disabled",
    );
  });

  it("builds CREATE2 proxy calldata from salt and exact init code", async function () {
    const { ethers } = await hre.network.create();
    const salt = ethers.id("qtsc-reviewed-release");
    const creationBytecode = "0x60006000";
    const constructorArguments = ethers.AbiCoder.defaultAbiCoder().encode(
      ["uint256"],
      [7n],
    );
    const deployment = buildDeterministicDeployment(
      ethers,
      DETERMINISTIC_DEPLOYMENT_PROXY,
      salt,
      creationBytecode,
      constructorArguments,
    );

    expect(deployment.initCode).to.equal(
      ethers.concat([creationBytecode, constructorArguments]),
    );
    expect(deployment.proxyCalldata).to.equal(
      ethers.concat([salt, deployment.initCode]),
    );
    expect(deployment.predictedAddress).to.equal(
      ethers.getCreate2Address(
        DETERMINISTIC_DEPLOYMENT_PROXY,
        salt,
        deployment.initCodeHash,
      ),
    );
  });

  it("builds six ordered, manual Owner Safe rehearsal transactions", async function () {
    const { ethers } = await hre.network.create();
    const [owner, escrow, operations, signerA, signerB, signerC] =
      await ethers.getSigners();
    const topology: Topology = {
      ownerSafe: owner.address,
      escrowSafe: escrow.address,
      operationsSafe: operations.address,
      productionOwners: [signerA.address, signerB.address, signerC.address],
    };
    const tokenFactory = await ethers.getContractFactory("QTSCKernelToken");
    const amount = ethers.parseEther("100");
    const actions = buildRehearsalActions(
      tokenFactory.interface,
      topology,
      owner.address,
      amount,
    );

    expect(actions.map(action => action.id)).to.deep.equal([
      "01-pause",
      "02-unpause",
      "03-update-treasuries",
      "04-restore-treasuries",
      "05-deposit",
      "06-harvest",
    ]);
    expect(
      tokenFactory.interface.parseTransaction({ data: actions[5].data })?.args
        .amount,
    ).to.equal(amount);
    expect(
      tokenFactory.interface.parseTransaction({ data: actions[3].data })?.args
        .newEscrowTreasury,
    ).to.equal(topology.escrowSafe);
  });
});
