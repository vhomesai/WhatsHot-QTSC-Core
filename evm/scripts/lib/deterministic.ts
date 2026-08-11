import type { ethers as EthersNamespace } from "ethers";

type Ethers = typeof EthersNamespace;

export interface DeterministicDeployment {
  initCode: string;
  initCodeHash: string;
  predictedAddress: string;
  proxyCalldata: string;
}

export function buildDeterministicDeployment(
  ethers: Ethers,
  factory: string,
  salt: string,
  creationBytecode: string,
  encodedConstructorArguments: string,
): DeterministicDeployment {
  const initCode = ethers.concat([
    creationBytecode,
    encodedConstructorArguments,
  ]);
  const initCodeHash = ethers.keccak256(initCode);
  return {
    initCode,
    initCodeHash,
    predictedAddress: ethers.getCreate2Address(factory, salt, initCodeHash),
    proxyCalldata: ethers.concat([salt, initCode]),
  };
}
