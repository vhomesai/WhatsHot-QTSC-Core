export interface ByteRange {
  start: number;
  length: number;
}

export function flattenReferences(
  references: Record<string, Record<string, ByteRange[]>>,
): ByteRange[] {
  return Object.values(references).flatMap(file =>
    Object.values(file).flat(),
  );
}

export function maskByteRanges(bytecode: string, ranges: ByteRange[]): string {
  const bytes = bytecode.startsWith("0x") ? bytecode.slice(2) : bytecode;
  const chars = bytes.split("");
  for (const { start, length } of ranges) {
    chars.fill("0", start * 2, (start + length) * 2);
  }
  return `0x${chars.join("")}`;
}

export function assertRuntimeMatch(
  expected: string,
  actual: string,
  immutableReferences: ByteRange[],
): void {
  const normalizedExpected = maskByteRanges(expected.toLowerCase(), immutableReferences);
  const normalizedActual = maskByteRanges(actual.toLowerCase(), immutableReferences);
  if (normalizedExpected !== normalizedActual) {
    throw new Error(
      "On-chain runtime bytecode does not match the production-profile artifact",
    );
  }
}
