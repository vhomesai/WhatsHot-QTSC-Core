OPENQASM 3.0;
include "stdgates.inc";

// 4realsy QSIR: 5-Qubit Entangled GHZ Core on 156Q Heavy-Hex Lattice
qubit[5] q;
bit[5] c;

// Layer 1: Macroscopic superposition
h q[0];

// Layer 2: Entanglement cascade
cx q[0], q[1];
cx q[1], q[2];
cx q[2], q[3];
cx q[3], q[4];

// Layer 3: Measurement validation
barrier q;
c[0] = measure q[0];
c[1] = measure q[1];
c[2] = measure q[2];
c[3] = measure q[3];
c[4] = measure q[4];
