import { describe, expect, it } from "vitest";
import { joinSpatial, linearFit } from "./analysisData";
describe("3D measurement evidence", () => {
  it("joins only exact finite samples, preserves zero and sorts by time", () => {
    expect(
      joinSpatial(
        [
          [3, 20],
          [1, 0],
          [2, 10],
          [4, NaN],
          [5, 30],
        ],
        [
          [1, 0],
          [2, null],
          [3, 4],
          [4, 5],
          [6, 3],
        ],
        [
          [1, 1],
          [2, 1.2],
          [3, 2],
          [4, 1],
          [5, 1],
        ],
      ),
    ).toEqual([
      [0, 0, 1, 1],
      [20, 4, 2, 3],
    ]);
  });
  it("does not infer values from nearby timestamps", () =>
    expect(joinSpatial([[100, 12]], [[101, 3]], [[100, 1]])).toEqual([]));
  it("returns no evidence for empty input", () =>
    expect(joinSpatial([], [], [])).toEqual([]));
});
describe("regression", () => {
  it("fits a known relationship while excluding invalid values", () =>
    expect(
      linearFit([
        [1, 3],
        [2, 5],
        [3, 7],
        [NaN, 2],
      ]),
    ).toEqual({ m: 2, b: 1 }));
  it("does not invent a slope for constant loads or a single sample", () => {
    expect(
      linearFit([
        [3, 2],
        [3, 4],
      ]),
    ).toBeNull();
    expect(linearFit([[1, 2]])).toBeNull();
  });
});
