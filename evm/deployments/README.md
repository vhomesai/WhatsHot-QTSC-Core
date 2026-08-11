# Deployment evidence

`base-sepolia.json` is the imported historical deployment record. Its Escrow
and Operations addresses are identical, so it **does not qualify** as the
required exact three-Safe rehearsal and must not be represented as one.

The deterministic deployment script creates
`base-sepolia-rehearsal.json` only after a successful transaction, receipt, and
on-chain code check using three distinct validated Safes. Review and commit
that generated file as evidence. Never hand-author a successful status.
