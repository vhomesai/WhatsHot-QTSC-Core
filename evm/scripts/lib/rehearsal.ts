import type { Interface } from "ethers";
import type { Topology } from "./config.js";

export interface PlannedAction {
  id: string;
  description: string;
  data: string;
}

export function buildRehearsalActions(
  tokenInterface: Interface,
  topology: Topology,
  tokenAddress: string,
  amount: bigint,
): PlannedAction[] {
  return [
    {
      id: "01-pause",
      description: "Pause QTSC through the Owner Safe",
      data: tokenInterface.encodeFunctionData("pause"),
    },
    {
      id: "02-unpause",
      description: "Unpause QTSC through the Owner Safe",
      data: tokenInterface.encodeFunctionData("unpause"),
    },
    {
      id: "03-update-treasuries",
      description:
        "Temporarily set Escrow to the Owner Safe to prove treasury governance",
      data: tokenInterface.encodeFunctionData("setTreasuries", [
        topology.ownerSafe,
        topology.operationsSafe,
      ]),
    },
    {
      id: "04-restore-treasuries",
      description: "Restore the exact Escrow and Operations topology",
      data: tokenInterface.encodeFunctionData("setTreasuries", [
        topology.escrowSafe,
        topology.operationsSafe,
      ]),
    },
    {
      id: "05-deposit",
      description:
        "Deposit 100 QTSC from the Owner Safe into the token contract",
      data: tokenInterface.encodeFunctionData("transfer", [
        tokenAddress,
        amount,
      ]),
    },
    {
      id: "06-harvest",
      description: "Execute the manual 25/75 harvest through the Owner Safe",
      data: tokenInterface.encodeFunctionData("executeHarvestSweep", [amount]),
    },
  ];
}
