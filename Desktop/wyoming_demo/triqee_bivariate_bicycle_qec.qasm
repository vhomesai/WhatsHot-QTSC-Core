// ===========================================================================
// Triqee™ Experimental QEC Prototype: [[72, 12, 6]] qLDPC Circuit IR
// Encodes k=12 logical qubits in n=72 physical data qubits + 72 syndrome ancillae
// NOTE: Static transpilation template (unexecuted compiler IR)
// ===========================================================================
OPENQASM 3.0;
include "stdgates.inc";

qubit[72] data;        // 72 Data Qubits
qubit[72] ancilla;   // 72 Syndrome Ancillae
bit[72] syndrome_r1;  // Round 1 Measurements
bit[72] syndrome_r2;  // Round 2 Fault Isolation
bit[12] logical_meas;      // 12 Logical Readouts

reset data;
reset ancilla;

// Round 1: Syndrome Parity Extraction
// X_STAB_00 (X-type)
h ancilla[0];
cx ancilla[0], data[1];
cx ancilla[0], data[2];
cx ancilla[0], data[18];
cx ancilla[0], data[39];
cx ancilla[0], data[42];
cx ancilla[0], data[48];
h ancilla[0];
syndrome_r1[0] = measure ancilla[0];

// X_STAB_01 (X-type)
h ancilla[1];
cx ancilla[1], data[2];
cx ancilla[1], data[3];
cx ancilla[1], data[19];
cx ancilla[1], data[40];
cx ancilla[1], data[43];
cx ancilla[1], data[49];
h ancilla[1];
syndrome_r1[1] = measure ancilla[1];

// X_STAB_02 (X-type)
h ancilla[2];
cx ancilla[2], data[3];
cx ancilla[2], data[4];
cx ancilla[2], data[20];
cx ancilla[2], data[41];
cx ancilla[2], data[44];
cx ancilla[2], data[50];
h ancilla[2];
syndrome_r1[2] = measure ancilla[2];

// X_STAB_03 (X-type)
h ancilla[3];
cx ancilla[3], data[4];
cx ancilla[3], data[5];
cx ancilla[3], data[21];
cx ancilla[3], data[36];
cx ancilla[3], data[45];
cx ancilla[3], data[51];
h ancilla[3];
syndrome_r1[3] = measure ancilla[3];

// X_STAB_04 (X-type)
h ancilla[4];
cx ancilla[4], data[0];
cx ancilla[4], data[5];
cx ancilla[4], data[22];
cx ancilla[4], data[37];
cx ancilla[4], data[46];
cx ancilla[4], data[52];
h ancilla[4];
syndrome_r1[4] = measure ancilla[4];

// X_STAB_05 (X-type)
h ancilla[5];
cx ancilla[5], data[0];
cx ancilla[5], data[1];
cx ancilla[5], data[23];
cx ancilla[5], data[38];
cx ancilla[5], data[47];
cx ancilla[5], data[53];
h ancilla[5];
syndrome_r1[5] = measure ancilla[5];

// X_STAB_06 (X-type)
h ancilla[6];
cx ancilla[6], data[7];
cx ancilla[6], data[8];
cx ancilla[6], data[24];
cx ancilla[6], data[45];
cx ancilla[6], data[48];
cx ancilla[6], data[54];
h ancilla[6];
syndrome_r1[6] = measure ancilla[6];

// X_STAB_07 (X-type)
h ancilla[7];
cx ancilla[7], data[8];
cx ancilla[7], data[9];
cx ancilla[7], data[25];
cx ancilla[7], data[46];
cx ancilla[7], data[49];
cx ancilla[7], data[55];
h ancilla[7];
syndrome_r1[7] = measure ancilla[7];

// X_STAB_08 (X-type)
h ancilla[8];
cx ancilla[8], data[9];
cx ancilla[8], data[10];
cx ancilla[8], data[26];
cx ancilla[8], data[47];
cx ancilla[8], data[50];
cx ancilla[8], data[56];
h ancilla[8];
syndrome_r1[8] = measure ancilla[8];

// X_STAB_09 (X-type)
h ancilla[9];
cx ancilla[9], data[10];
cx ancilla[9], data[11];
cx ancilla[9], data[27];
cx ancilla[9], data[42];
cx ancilla[9], data[51];
cx ancilla[9], data[57];
h ancilla[9];
syndrome_r1[9] = measure ancilla[9];

// X_STAB_10 (X-type)
h ancilla[10];
cx ancilla[10], data[6];
cx ancilla[10], data[11];
cx ancilla[10], data[28];
cx ancilla[10], data[43];
cx ancilla[10], data[52];
cx ancilla[10], data[58];
h ancilla[10];
syndrome_r1[10] = measure ancilla[10];

// X_STAB_11 (X-type)
h ancilla[11];
cx ancilla[11], data[6];
cx ancilla[11], data[7];
cx ancilla[11], data[29];
cx ancilla[11], data[44];
cx ancilla[11], data[53];
cx ancilla[11], data[59];
h ancilla[11];
syndrome_r1[11] = measure ancilla[11];

// X_STAB_12 (X-type)
h ancilla[12];
cx ancilla[12], data[13];
cx ancilla[12], data[14];
cx ancilla[12], data[30];
cx ancilla[12], data[51];
cx ancilla[12], data[54];
cx ancilla[12], data[60];
h ancilla[12];
syndrome_r1[12] = measure ancilla[12];

// X_STAB_13 (X-type)
h ancilla[13];
cx ancilla[13], data[14];
cx ancilla[13], data[15];
cx ancilla[13], data[31];
cx ancilla[13], data[52];
cx ancilla[13], data[55];
cx ancilla[13], data[61];
h ancilla[13];
syndrome_r1[13] = measure ancilla[13];

// X_STAB_14 (X-type)
h ancilla[14];
cx ancilla[14], data[15];
cx ancilla[14], data[16];
cx ancilla[14], data[32];
cx ancilla[14], data[53];
cx ancilla[14], data[56];
cx ancilla[14], data[62];
h ancilla[14];
syndrome_r1[14] = measure ancilla[14];

// X_STAB_15 (X-type)
h ancilla[15];
cx ancilla[15], data[16];
cx ancilla[15], data[17];
cx ancilla[15], data[33];
cx ancilla[15], data[48];
cx ancilla[15], data[57];
cx ancilla[15], data[63];
h ancilla[15];
syndrome_r1[15] = measure ancilla[15];

// X_STAB_16 (X-type)
h ancilla[16];
cx ancilla[16], data[12];
cx ancilla[16], data[17];
cx ancilla[16], data[34];
cx ancilla[16], data[49];
cx ancilla[16], data[58];
cx ancilla[16], data[64];
h ancilla[16];
syndrome_r1[16] = measure ancilla[16];

// X_STAB_17 (X-type)
h ancilla[17];
cx ancilla[17], data[12];
cx ancilla[17], data[13];
cx ancilla[17], data[35];
cx ancilla[17], data[50];
cx ancilla[17], data[59];
cx ancilla[17], data[65];
h ancilla[17];
syndrome_r1[17] = measure ancilla[17];

// X_STAB_18 (X-type)
h ancilla[18];
cx ancilla[18], data[0];
cx ancilla[18], data[19];
cx ancilla[18], data[20];
cx ancilla[18], data[57];
cx ancilla[18], data[60];
cx ancilla[18], data[66];
h ancilla[18];
syndrome_r1[18] = measure ancilla[18];

// X_STAB_19 (X-type)
h ancilla[19];
cx ancilla[19], data[1];
cx ancilla[19], data[20];
cx ancilla[19], data[21];
cx ancilla[19], data[58];
cx ancilla[19], data[61];
cx ancilla[19], data[67];
h ancilla[19];
syndrome_r1[19] = measure ancilla[19];

// X_STAB_20 (X-type)
h ancilla[20];
cx ancilla[20], data[2];
cx ancilla[20], data[21];
cx ancilla[20], data[22];
cx ancilla[20], data[59];
cx ancilla[20], data[62];
cx ancilla[20], data[68];
h ancilla[20];
syndrome_r1[20] = measure ancilla[20];

// X_STAB_21 (X-type)
h ancilla[21];
cx ancilla[21], data[3];
cx ancilla[21], data[22];
cx ancilla[21], data[23];
cx ancilla[21], data[54];
cx ancilla[21], data[63];
cx ancilla[21], data[69];
h ancilla[21];
syndrome_r1[21] = measure ancilla[21];

// X_STAB_22 (X-type)
h ancilla[22];
cx ancilla[22], data[4];
cx ancilla[22], data[18];
cx ancilla[22], data[23];
cx ancilla[22], data[55];
cx ancilla[22], data[64];
cx ancilla[22], data[70];
h ancilla[22];
syndrome_r1[22] = measure ancilla[22];

// X_STAB_23 (X-type)
h ancilla[23];
cx ancilla[23], data[5];
cx ancilla[23], data[18];
cx ancilla[23], data[19];
cx ancilla[23], data[56];
cx ancilla[23], data[65];
cx ancilla[23], data[71];
h ancilla[23];
syndrome_r1[23] = measure ancilla[23];

// X_STAB_24 (X-type)
h ancilla[24];
cx ancilla[24], data[6];
cx ancilla[24], data[25];
cx ancilla[24], data[26];
cx ancilla[24], data[36];
cx ancilla[24], data[63];
cx ancilla[24], data[66];
h ancilla[24];
syndrome_r1[24] = measure ancilla[24];

// X_STAB_25 (X-type)
h ancilla[25];
cx ancilla[25], data[7];
cx ancilla[25], data[26];
cx ancilla[25], data[27];
cx ancilla[25], data[37];
cx ancilla[25], data[64];
cx ancilla[25], data[67];
h ancilla[25];
syndrome_r1[25] = measure ancilla[25];

// X_STAB_26 (X-type)
h ancilla[26];
cx ancilla[26], data[8];
cx ancilla[26], data[27];
cx ancilla[26], data[28];
cx ancilla[26], data[38];
cx ancilla[26], data[65];
cx ancilla[26], data[68];
h ancilla[26];
syndrome_r1[26] = measure ancilla[26];

// X_STAB_27 (X-type)
h ancilla[27];
cx ancilla[27], data[9];
cx ancilla[27], data[28];
cx ancilla[27], data[29];
cx ancilla[27], data[39];
cx ancilla[27], data[60];
cx ancilla[27], data[69];
h ancilla[27];
syndrome_r1[27] = measure ancilla[27];

// X_STAB_28 (X-type)
h ancilla[28];
cx ancilla[28], data[10];
cx ancilla[28], data[24];
cx ancilla[28], data[29];
cx ancilla[28], data[40];
cx ancilla[28], data[61];
cx ancilla[28], data[70];
h ancilla[28];
syndrome_r1[28] = measure ancilla[28];

// X_STAB_29 (X-type)
h ancilla[29];
cx ancilla[29], data[11];
cx ancilla[29], data[24];
cx ancilla[29], data[25];
cx ancilla[29], data[41];
cx ancilla[29], data[62];
cx ancilla[29], data[71];
h ancilla[29];
syndrome_r1[29] = measure ancilla[29];

// X_STAB_30 (X-type)
h ancilla[30];
cx ancilla[30], data[12];
cx ancilla[30], data[31];
cx ancilla[30], data[32];
cx ancilla[30], data[36];
cx ancilla[30], data[42];
cx ancilla[30], data[69];
h ancilla[30];
syndrome_r1[30] = measure ancilla[30];

// X_STAB_31 (X-type)
h ancilla[31];
cx ancilla[31], data[13];
cx ancilla[31], data[32];
cx ancilla[31], data[33];
cx ancilla[31], data[37];
cx ancilla[31], data[43];
cx ancilla[31], data[70];
h ancilla[31];
syndrome_r1[31] = measure ancilla[31];

// X_STAB_32 (X-type)
h ancilla[32];
cx ancilla[32], data[14];
cx ancilla[32], data[33];
cx ancilla[32], data[34];
cx ancilla[32], data[38];
cx ancilla[32], data[44];
cx ancilla[32], data[71];
h ancilla[32];
syndrome_r1[32] = measure ancilla[32];

// X_STAB_33 (X-type)
h ancilla[33];
cx ancilla[33], data[15];
cx ancilla[33], data[34];
cx ancilla[33], data[35];
cx ancilla[33], data[39];
cx ancilla[33], data[45];
cx ancilla[33], data[66];
h ancilla[33];
syndrome_r1[33] = measure ancilla[33];

// X_STAB_34 (X-type)
h ancilla[34];
cx ancilla[34], data[16];
cx ancilla[34], data[30];
cx ancilla[34], data[35];
cx ancilla[34], data[40];
cx ancilla[34], data[46];
cx ancilla[34], data[67];
h ancilla[34];
syndrome_r1[34] = measure ancilla[34];

// X_STAB_35 (X-type)
h ancilla[35];
cx ancilla[35], data[17];
cx ancilla[35], data[30];
cx ancilla[35], data[31];
cx ancilla[35], data[41];
cx ancilla[35], data[47];
cx ancilla[35], data[68];
h ancilla[35];
syndrome_r1[35] = measure ancilla[35];

// Z_STAB_00 (Z-type)
cx data[3], ancilla[36];
cx data[24], ancilla[36];
cx data[30], ancilla[36];
cx data[40], ancilla[36];
cx data[41], ancilla[36];
cx data[54], ancilla[36];
syndrome_r1[36] = measure ancilla[36];

// Z_STAB_01 (Z-type)
cx data[4], ancilla[37];
cx data[25], ancilla[37];
cx data[31], ancilla[37];
cx data[36], ancilla[37];
cx data[41], ancilla[37];
cx data[55], ancilla[37];
syndrome_r1[37] = measure ancilla[37];

// Z_STAB_02 (Z-type)
cx data[5], ancilla[38];
cx data[26], ancilla[38];
cx data[32], ancilla[38];
cx data[36], ancilla[38];
cx data[37], ancilla[38];
cx data[56], ancilla[38];
syndrome_r1[38] = measure ancilla[38];

// Z_STAB_03 (Z-type)
cx data[0], ancilla[39];
cx data[27], ancilla[39];
cx data[33], ancilla[39];
cx data[37], ancilla[39];
cx data[38], ancilla[39];
cx data[57], ancilla[39];
syndrome_r1[39] = measure ancilla[39];

// Z_STAB_04 (Z-type)
cx data[1], ancilla[40];
cx data[28], ancilla[40];
cx data[34], ancilla[40];
cx data[38], ancilla[40];
cx data[39], ancilla[40];
cx data[58], ancilla[40];
syndrome_r1[40] = measure ancilla[40];

// Z_STAB_05 (Z-type)
cx data[2], ancilla[41];
cx data[29], ancilla[41];
cx data[35], ancilla[41];
cx data[39], ancilla[41];
cx data[40], ancilla[41];
cx data[59], ancilla[41];
syndrome_r1[41] = measure ancilla[41];

// Z_STAB_06 (Z-type)
cx data[0], ancilla[42];
cx data[9], ancilla[42];
cx data[30], ancilla[42];
cx data[46], ancilla[42];
cx data[47], ancilla[42];
cx data[60], ancilla[42];
syndrome_r1[42] = measure ancilla[42];

// Z_STAB_07 (Z-type)
cx data[1], ancilla[43];
cx data[10], ancilla[43];
cx data[31], ancilla[43];
cx data[42], ancilla[43];
cx data[47], ancilla[43];
cx data[61], ancilla[43];
syndrome_r1[43] = measure ancilla[43];

// Z_STAB_08 (Z-type)
cx data[2], ancilla[44];
cx data[11], ancilla[44];
cx data[32], ancilla[44];
cx data[42], ancilla[44];
cx data[43], ancilla[44];
cx data[62], ancilla[44];
syndrome_r1[44] = measure ancilla[44];

// Z_STAB_09 (Z-type)
cx data[3], ancilla[45];
cx data[6], ancilla[45];
cx data[33], ancilla[45];
cx data[43], ancilla[45];
cx data[44], ancilla[45];
cx data[63], ancilla[45];
syndrome_r1[45] = measure ancilla[45];

// Z_STAB_10 (Z-type)
cx data[4], ancilla[46];
cx data[7], ancilla[46];
cx data[34], ancilla[46];
cx data[44], ancilla[46];
cx data[45], ancilla[46];
cx data[64], ancilla[46];
syndrome_r1[46] = measure ancilla[46];

// Z_STAB_11 (Z-type)
cx data[5], ancilla[47];
cx data[8], ancilla[47];
cx data[35], ancilla[47];
cx data[45], ancilla[47];
cx data[46], ancilla[47];
cx data[65], ancilla[47];
syndrome_r1[47] = measure ancilla[47];

// Z_STAB_12 (Z-type)
cx data[0], ancilla[48];
cx data[6], ancilla[48];
cx data[15], ancilla[48];
cx data[52], ancilla[48];
cx data[53], ancilla[48];
cx data[66], ancilla[48];
syndrome_r1[48] = measure ancilla[48];

// Z_STAB_13 (Z-type)
cx data[1], ancilla[49];
cx data[7], ancilla[49];
cx data[16], ancilla[49];
cx data[48], ancilla[49];
cx data[53], ancilla[49];
cx data[67], ancilla[49];
syndrome_r1[49] = measure ancilla[49];

// Z_STAB_14 (Z-type)
cx data[2], ancilla[50];
cx data[8], ancilla[50];
cx data[17], ancilla[50];
cx data[48], ancilla[50];
cx data[49], ancilla[50];
cx data[68], ancilla[50];
syndrome_r1[50] = measure ancilla[50];

// Z_STAB_15 (Z-type)
cx data[3], ancilla[51];
cx data[9], ancilla[51];
cx data[12], ancilla[51];
cx data[49], ancilla[51];
cx data[50], ancilla[51];
cx data[69], ancilla[51];
syndrome_r1[51] = measure ancilla[51];

// Z_STAB_16 (Z-type)
cx data[4], ancilla[52];
cx data[10], ancilla[52];
cx data[13], ancilla[52];
cx data[50], ancilla[52];
cx data[51], ancilla[52];
cx data[70], ancilla[52];
syndrome_r1[52] = measure ancilla[52];

// Z_STAB_17 (Z-type)
cx data[5], ancilla[53];
cx data[11], ancilla[53];
cx data[14], ancilla[53];
cx data[51], ancilla[53];
cx data[52], ancilla[53];
cx data[71], ancilla[53];
syndrome_r1[53] = measure ancilla[53];

// Z_STAB_18 (Z-type)
cx data[6], ancilla[54];
cx data[12], ancilla[54];
cx data[21], ancilla[54];
cx data[36], ancilla[54];
cx data[58], ancilla[54];
cx data[59], ancilla[54];
syndrome_r1[54] = measure ancilla[54];

// Z_STAB_19 (Z-type)
cx data[7], ancilla[55];
cx data[13], ancilla[55];
cx data[22], ancilla[55];
cx data[37], ancilla[55];
cx data[54], ancilla[55];
cx data[59], ancilla[55];
syndrome_r1[55] = measure ancilla[55];

// Z_STAB_20 (Z-type)
cx data[8], ancilla[56];
cx data[14], ancilla[56];
cx data[23], ancilla[56];
cx data[38], ancilla[56];
cx data[54], ancilla[56];
cx data[55], ancilla[56];
syndrome_r1[56] = measure ancilla[56];

// Z_STAB_21 (Z-type)
cx data[9], ancilla[57];
cx data[15], ancilla[57];
cx data[18], ancilla[57];
cx data[39], ancilla[57];
cx data[55], ancilla[57];
cx data[56], ancilla[57];
syndrome_r1[57] = measure ancilla[57];

// Z_STAB_22 (Z-type)
cx data[10], ancilla[58];
cx data[16], ancilla[58];
cx data[19], ancilla[58];
cx data[40], ancilla[58];
cx data[56], ancilla[58];
cx data[57], ancilla[58];
syndrome_r1[58] = measure ancilla[58];

// Z_STAB_23 (Z-type)
cx data[11], ancilla[59];
cx data[17], ancilla[59];
cx data[20], ancilla[59];
cx data[41], ancilla[59];
cx data[57], ancilla[59];
cx data[58], ancilla[59];
syndrome_r1[59] = measure ancilla[59];

// Z_STAB_24 (Z-type)
cx data[12], ancilla[60];
cx data[18], ancilla[60];
cx data[27], ancilla[60];
cx data[42], ancilla[60];
cx data[64], ancilla[60];
cx data[65], ancilla[60];
syndrome_r1[60] = measure ancilla[60];

// Z_STAB_25 (Z-type)
cx data[13], ancilla[61];
cx data[19], ancilla[61];
cx data[28], ancilla[61];
cx data[43], ancilla[61];
cx data[60], ancilla[61];
cx data[65], ancilla[61];
syndrome_r1[61] = measure ancilla[61];

// Z_STAB_26 (Z-type)
cx data[14], ancilla[62];
cx data[20], ancilla[62];
cx data[29], ancilla[62];
cx data[44], ancilla[62];
cx data[60], ancilla[62];
cx data[61], ancilla[62];
syndrome_r1[62] = measure ancilla[62];

// Z_STAB_27 (Z-type)
cx data[15], ancilla[63];
cx data[21], ancilla[63];
cx data[24], ancilla[63];
cx data[45], ancilla[63];
cx data[61], ancilla[63];
cx data[62], ancilla[63];
syndrome_r1[63] = measure ancilla[63];

// Z_STAB_28 (Z-type)
cx data[16], ancilla[64];
cx data[22], ancilla[64];
cx data[25], ancilla[64];
cx data[46], ancilla[64];
cx data[62], ancilla[64];
cx data[63], ancilla[64];
syndrome_r1[64] = measure ancilla[64];

// Z_STAB_29 (Z-type)
cx data[17], ancilla[65];
cx data[23], ancilla[65];
cx data[26], ancilla[65];
cx data[47], ancilla[65];
cx data[63], ancilla[65];
cx data[64], ancilla[65];
syndrome_r1[65] = measure ancilla[65];

// Z_STAB_30 (Z-type)
cx data[18], ancilla[66];
cx data[24], ancilla[66];
cx data[33], ancilla[66];
cx data[48], ancilla[66];
cx data[70], ancilla[66];
cx data[71], ancilla[66];
syndrome_r1[66] = measure ancilla[66];

// Z_STAB_31 (Z-type)
cx data[19], ancilla[67];
cx data[25], ancilla[67];
cx data[34], ancilla[67];
cx data[49], ancilla[67];
cx data[66], ancilla[67];
cx data[71], ancilla[67];
syndrome_r1[67] = measure ancilla[67];

// Z_STAB_32 (Z-type)
cx data[20], ancilla[68];
cx data[26], ancilla[68];
cx data[35], ancilla[68];
cx data[50], ancilla[68];
cx data[66], ancilla[68];
cx data[67], ancilla[68];
syndrome_r1[68] = measure ancilla[68];

// Z_STAB_33 (Z-type)
cx data[21], ancilla[69];
cx data[27], ancilla[69];
cx data[30], ancilla[69];
cx data[51], ancilla[69];
cx data[67], ancilla[69];
cx data[68], ancilla[69];
syndrome_r1[69] = measure ancilla[69];

// Z_STAB_34 (Z-type)
cx data[22], ancilla[70];
cx data[28], ancilla[70];
cx data[31], ancilla[70];
cx data[52], ancilla[70];
cx data[68], ancilla[70];
cx data[69], ancilla[70];
syndrome_r1[70] = measure ancilla[70];

// Z_STAB_35 (Z-type)
cx data[23], ancilla[71];
cx data[29], ancilla[71];
cx data[32], ancilla[71];
cx data[53], ancilla[71];
cx data[69], ancilla[71];
cx data[70], ancilla[71];
syndrome_r1[71] = measure ancilla[71];

logical_meas[0] = measure data[0];
logical_meas[1] = measure data[6];
logical_meas[2] = measure data[12];
logical_meas[3] = measure data[18];
logical_meas[4] = measure data[24];
logical_meas[5] = measure data[30];
logical_meas[6] = measure data[36];
logical_meas[7] = measure data[42];
logical_meas[8] = measure data[48];
logical_meas[9] = measure data[54];
logical_meas[10] = measure data[60];
logical_meas[11] = measure data[66];