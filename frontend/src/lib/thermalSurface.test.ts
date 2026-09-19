import { describe, expect, it } from "vitest";
import { thermalSurface } from "./thermalSurface";
describe("illustrative thermal surface", () => {
  it("fits the known steady-state relationship within observed ranges", () => {
    const result = thermalSurface([
      [100, 10, 1, 1],
      [200, 80, 2, 2],
      [150, 33.75, 1.5, 3],
    ])!;
    expect(result.k0).toBeCloseTo(0.001);
    expect(result.data).toHaveLength(825);
    for (const [current, ratio, delta] of result.data) {
      expect(current).toBeGreaterThanOrEqual(100);
      expect(current).toBeLessThanOrEqual(200);
      expect(ratio).toBeGreaterThanOrEqual(1);
      expect(ratio).toBeLessThanOrEqual(2);
      expect(delta).toBeCloseTo(0.001 * ratio * current * current);
    }
  });
  it("does not construct a surface from inadequate or degenerate evidence", () => {
    expect(thermalSurface([])).toBeNull();
    expect(
      thermalSurface([
        [0, 1, 1, 1],
        [NaN, 1, 2, 2],
        [10, 1, 0, 3],
      ]),
    ).toBeNull();
    expect(
      thermalSurface([
        [100, 10, 1, 1],
        [100, 11, 1, 2],
        [100, 12, 1, 3],
      ]),
    ).toBeNull();
  });
});
