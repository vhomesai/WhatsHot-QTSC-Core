import { expect } from "chai";
import {
  assertRuntimeMatch,
  flattenReferences,
  maskByteRanges,
} from "../scripts/lib/bytecode.js";

describe("bytecode comparison helpers", function () {
  it("masks immutable byte ranges before comparison", function () {
    const expected = "0x600111226002";
    const actual = "0x6001aabb6002";
    expect(maskByteRanges(expected, [{ start: 2, length: 2 }])).to.equal(
      "0x600100006002",
    );
    expect(() =>
      assertRuntimeMatch(expected, actual, [{ start: 2, length: 2 }]),
    ).not.to.throw();
  });

  it("rejects differences outside immutable ranges", function () {
    expect(() =>
      assertRuntimeMatch("0x60016002", "0x60026002", []),
    ).to.throw("does not match");
  });

  it("flattens compiler link and immutable reference maps", function () {
    expect(
      flattenReferences({
        "Library.sol": {
          Library: [{ start: 10, length: 20 }],
        },
      }),
    ).to.deep.equal([{ start: 10, length: 20 }]);
  });
});
