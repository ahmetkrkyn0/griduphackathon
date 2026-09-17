import { describe, expect, it } from "vitest";
import { chartTicks, linePath, nearestSample } from "./chartMath";

describe("chart scales and missing measurements", () => {
  it.each([
    [1.05, 1.61],
    [-10, 14],
    [600, 930],
    [0, 0],
    [42, 42],
  ])("creates finite, ascending ticks covering %s to %s", (min, max) => {
    const ticks = chartTicks([min, max]);
    expect(ticks[0]).toBeLessThanOrEqual(min);
    expect(ticks.at(-1)).toBeGreaterThanOrEqual(max);
    expect(ticks.every(Number.isFinite)).toBe(true);
    expect(ticks.every((v, i) => !i || v > ticks[i - 1])).toBe(true);
    expect(ticks.length).toBeLessThanOrEqual(8);
  });
  it("ignores nonfinite values and can include a zero baseline", () => {
    expect(chartTicks([NaN, Infinity])).toEqual([0, 0.25, 0.5, 0.75, 1]);
    expect(chartTicks([120, 220], true)[0]).toBe(0);
  });
  it("breaks paths across unavailable measurements instead of connecting a false trend", () => {
    const path = linePath(
      [
        [0, 1],
        [1, 2],
        [2, null],
        [3, 4],
      ],
      (v) => v,
      (v) => v,
    );
    expect(path.match(/M/g)).toHaveLength(2);
    expect(path.match(/L/g)).toHaveLength(1);
    expect(path).not.toMatch(/NaN|null/);
  });
  it("keeps a missing nearest sample missing instead of replacing it with a valid neighbor", () => {
    expect(
      nearestSample(
        [
          [100, 1],
          [200, null],
          [300, 3],
        ],
        210,
      ),
    ).toEqual([200, null]);
    expect(nearestSample([], 210)).toBeNull();
  });
});
