import {
  createPublicClient,
  getAddress,
  http,
  type Address,
} from "viem";
import { base } from "viem/chains";

const OWNER_SAFE = getAddress("0x8411C2cD2Ea76513629215b09599B59d9f3cBD11");
const ESCROW_SAFE = getAddress("0x952989A45f223F90401aFd0e55D97d5a2c53DFD1");
const OPERATIONS_SAFE = getAddress("0xDcE19137ebFBe359eb19E1F74349877FC7152FC1");
const EXPECTED_OWNERS = [
  getAddress("0x53e9F5a5a59D35cBe12a0f42201ef2a743cA8C31"),
  getAddress("0xF61962f979AB878f39091Ef37467F5dA4441ac7e"),
  getAddress("0xe6da093634067f2477fAd10178C063cBf22754a5"),
].map(owner => owner.toLowerCase()).sort();
const SAFE_ABI = [
  {
    inputs: [],
    name: "getOwners",
    outputs: [{ internalType: "address[]", name: "", type: "address[]" }],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [],
    name: "getThreshold",
    outputs: [{ internalType: "uint256", name: "", type: "uint256" }],
    stateMutability: "view",
    type: "function",
  },
] as const;

const publicClient = createPublicClient({
  chain: base,
  transport: http("https://mainnet.base.org"),
});
const checksButton =
  document.querySelector<HTMLButtonElement>("#run-checks")!;
const status = document.querySelector<HTMLPreElement>("#status")!;

document.querySelector("#owner-safe")!.textContent = OWNER_SAFE;
document.querySelector("#escrow-safe")!.textContent = ESCROW_SAFE;
document.querySelector("#operations-safe")!.textContent = OPERATIONS_SAFE;

function delay(milliseconds: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, milliseconds));
}

async function withRetry<T>(operation: () => Promise<T>): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt < 5; attempt += 1) {
    try {
      const value = await operation();
      await delay(600);
      return value;
    } catch (error) {
      lastError = error;
      await delay(1_000 * (attempt + 1));
    }
  }
  throw lastError;
}

async function validateSafe(label: string, address: Address): Promise<void> {
  const code = await withRetry(() => publicClient.getCode({ address }));
  if (code === undefined) {
    throw new Error(`${label} is not deployed`);
  }

  const threshold = await withRetry(() =>
    publicClient.readContract({
      address,
      abi: SAFE_ABI,
      functionName: "getThreshold",
    }),
  );
  const owners = (
    await withRetry(() =>
      publicClient.readContract({
        address,
        abi: SAFE_ABI,
        functionName: "getOwners",
      }),
    )
  ).map(owner => owner.toLowerCase()).sort();

  if (
    threshold !== 2n ||
    owners.length !== 3 ||
    owners.some((owner, index) => owner !== EXPECTED_OWNERS[index])
  ) {
    throw new Error(`${label} is not the expected 2-of-3 Safe`);
  }
}

checksButton.addEventListener("click", async () => {
  checksButton.disabled = true;
  try {
    const chainId = await withRetry(() => publicClient.getChainId());
    if (chainId !== base.id) {
      throw new Error(`Read-only RPC returned unexpected chain ID ${chainId}`);
    }

    status.textContent = "Validating Owner Safe...";
    await validateSafe("Owner Safe", OWNER_SAFE);
    status.textContent += "\nValidating Escrow Safe...";
    await validateSafe("Escrow Safe", ESCROW_SAFE);
    status.textContent += "\nValidating Operations Safe...";
    await validateSafe("Operations Safe", OPERATIONS_SAFE);
    status.textContent +=
      "\nAll production Safes match the expected 2-of-3 topology." +
      "\nDeployment remains disabled.";
  } catch (error) {
    status.textContent = error instanceof Error ? error.message : String(error);
  } finally {
    checksButton.disabled = false;
  }
});
