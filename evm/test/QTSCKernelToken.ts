import { expect } from "chai";
import hre from "hardhat";

describe("QTSCKernelToken", function () {
  async function deployFixture() {
    const { ethers } = await hre.network.create();
    const [owner, escrow, operations, user, outsider] =
      await ethers.getSigners();
    const token = await ethers.deployContract("QTSCKernelToken", [
      owner.address,
      escrow.address,
      operations.address,
    ]);
    await token.waitForDeployment();

    return { ethers, token, owner, escrow, operations, user, outsider };
  }

  it("mints the fixed initial supply to the configured owner", async function () {
    const { ethers, token, owner } = await deployFixture();
    const initialSupply = ethers.parseEther("100000000");

    expect(await token.name()).to.equal("QTSC Ternary Kernel Token");
    expect(await token.symbol()).to.equal("QTSC");
    expect(await token.decimals()).to.equal(18);
    expect(await token.owner()).to.equal(owner.address);
    expect(await token.INITIAL_SUPPLY()).to.equal(initialSupply);
    expect(await token.totalSupply()).to.equal(initialSupply);
    expect(await token.balanceOf(owner.address)).to.equal(initialSupply);
  });

  it("rejects zero-address deployment parameters", async function () {
    const { ethers } = await hre.network.create();
    const [owner, escrow, operations] = await ethers.getSigners();
    const tokenFactory = await ethers.getContractFactory("QTSCKernelToken");

    await expect(
      tokenFactory.deploy(
        ethers.ZeroAddress,
        escrow.address,
        operations.address,
      ),
    ).to.be.revertedWithCustomError(tokenFactory, "OwnableInvalidOwner");
    await expect(
      tokenFactory.deploy(
        owner.address,
        ethers.ZeroAddress,
        operations.address,
      ),
    ).to.be.revertedWithCustomError(tokenFactory, "InvalidAddress");
  });

  it("burns tokens without allowing replacement minting", async function () {
    const { ethers, token, owner } = await deployFixture();
    const amount = ethers.parseEther("10");
    const supplyBefore = await token.totalSupply();

    await token.burn(amount);

    expect(await token.totalSupply()).to.equal(supplyBefore - amount);
    expect(await token.balanceOf(owner.address)).to.equal(supplyBefore - amount);
  });

  it("distributes deposited tokens 25/75 between treasuries", async function () {
    const { ethers, token, escrow, operations } = await deployFixture();
    const deposit = ethers.parseEther("100");
    await token.transfer(await token.getAddress(), deposit);

    await expect(token.executeHarvestSweep(deposit))
      .to.emit(token, "HarvestSweepExecuted")
      .withArgs(
        deposit,
        ethers.parseEther("25"),
        ethers.parseEther("75"),
      );

    expect(await token.balanceOf(escrow.address)).to.equal(
      ethers.parseEther("25"),
    );
    expect(await token.balanceOf(operations.address)).to.equal(
      ethers.parseEther("75"),
    );
    expect(await token.balanceOf(await token.getAddress())).to.equal(0);
  });

  it("rejects unauthorized, zero, and underfunded harvest sweeps", async function () {
    const { ethers, token, outsider } = await deployFixture();
    const outsiderToken = await ethers.getContractAt(
      "QTSCKernelToken",
      await token.getAddress(),
      outsider,
    );

    await expect(
      outsiderToken.executeHarvestSweep(1),
    ).to.be.revertedWithCustomError(token, "OwnableUnauthorizedAccount");
    await expect(token.executeHarvestSweep(0)).to.be.revertedWithCustomError(
      token,
      "InvalidAmount",
    );
    await expect(token.executeHarvestSweep(ethers.parseEther("1")))
      .to.be.revertedWithCustomError(token, "InsufficientHarvestBalance")
      .withArgs(0, ethers.parseEther("1"));
  });

  it("lets only the owner update non-zero treasury addresses", async function () {
    const { ethers, token, user, outsider } = await deployFixture();
    const outsiderToken = await ethers.getContractAt(
      "QTSCKernelToken",
      await token.getAddress(),
      outsider,
    );

    await expect(
      outsiderToken.setTreasuries(user.address, outsider.address),
    ).to.be.revertedWithCustomError(token, "OwnableUnauthorizedAccount");
    await expect(token.setTreasuries(user.address, outsider.address))
      .to.emit(token, "TreasuriesUpdated");

    expect(await token.escrowTreasury()).to.equal(user.address);
    expect(await token.operationalTreasury()).to.equal(outsider.address);
  });

  it("pauses transfers, burns, and harvests until the owner unpauses", async function () {
    const { ethers, token, user, outsider } = await deployFixture();
    const outsiderToken = await ethers.getContractAt(
      "QTSCKernelToken",
      await token.getAddress(),
      outsider,
    );
    const deposit = ethers.parseEther("3");
    await token.transfer(await token.getAddress(), deposit);
    await token.pause();

    await expect(token.transfer(user.address, 1)).to.be.revertedWithCustomError(
      token,
      "EnforcedPause",
    );
    await expect(token.burn(1)).to.be.revertedWithCustomError(
      token,
      "EnforcedPause",
    );
    await expect(
      token.executeHarvestSweep(deposit),
    ).to.be.revertedWithCustomError(token, "EnforcedPause");
    await expect(outsiderToken.unpause()).to.be.revertedWithCustomError(
      token,
      "OwnableUnauthorizedAccount",
    );

    await token.unpause();
    const balanceBefore = await token.balanceOf(user.address);
    await (await token.transfer(user.address, 1)).wait();
    expect(await token.balanceOf(user.address)).to.equal(balanceBefore + 1n);
  });
});
