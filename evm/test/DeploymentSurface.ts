import { expect } from "chai";
import fs from "node:fs";
import path from "node:path";

describe("Mainnet deployment surface", function () {
  const read = (relativePath: string) =>
    fs.readFileSync(path.resolve(relativePath), "utf8");

  it("keeps the browser Mainnet UI read-only", function () {
    const source = read("deployer/main.ts");
    const html = read("deployer/index.html");
    const forbidden = [
      "createWalletClient",
      "deployContract",
      "sendTransaction",
      "writeContract",
      "requestAddresses",
      "eth_sendTransaction",
      "wallet_switchEthereumChain",
    ];

    for (const capability of forbidden) {
      expect(source).not.to.include(capability);
      expect(html).not.to.include(capability);
    }
    expect(html).to.include("Deployment is disabled");
    expect(html).not.to.include('id="deploy"');
    expect(html).not.to.include('id="confirmation"');
  });

  it("keeps the legacy direct EOA script as a non-broadcasting tombstone", function () {
    const source = read("scripts/deploy.ts");
    expect(source).to.include("Direct EOA deployment is permanently disabled");
    expect(source).not.to.include("deployContract");
    expect(source).not.to.include("sendTransaction");
    expect(source).not.to.include("ethers.deployContract");
  });

  it("exposes no Mainnet deployment npm command", function () {
    const packageJson = JSON.parse(read("package.json")) as {
      scripts: Record<string, string>;
    };
    const scriptText = Object.entries(packageJson.scripts)
      .map(([name, command]) => `${name} ${command}`)
      .join("\n");

    expect(scriptText).not.to.match(/deploy.*mainnet/i);
    expect(packageJson.scripts["preflight:mainnet-readonly"]).to.include(
      "vite deployer",
    );
  });
});
