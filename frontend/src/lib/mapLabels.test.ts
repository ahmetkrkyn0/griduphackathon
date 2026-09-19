import { describe, expect, it } from "vitest";
import { layoutMapLabels } from "./mapLabels";

describe("regional map labels", () => {
  const cluster = [
    { x: 320, y: 220, text: "Bornova" },
    { x: 304, y: 223, text: "Karşıyaka" },
    { x: 293, y: 213, text: "Çiğli" },
    { x: 311, y: 242, text: "Buca" },
    { x: 347, y: 200, text: "Yunusemre" },
  ];

  it.each([1, 1.4, 3, 6])("keeps labels clear of each other and all markers at %sx zoom", (scale) => {
    const points = cluster.map((p) => ({ ...p, x: 450 + (p.x - 320) * scale, y: 310 + (p.y - 220) * scale }));
    const labels = layoutMapLabels(points, 900, 620);
    labels.forEach((a, i) => {
      for (const b of labels.slice(i + 1)) {
        expect(a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y).toBe(false);
      }
      for (const p of points) {
        expect(p.x > a.x - 10 && p.x < a.x + a.width + 10 && p.y > a.y - 10 && p.y < a.y + a.height + 10).toBe(false);
      }
    });
  });

  it("keeps labels inside the viewport near every edge", () => {
    const points = [{ x: 12, y: 12, text: "Merkezefendi" }, { x: 888, y: 12, text: "Pamukkale" }, { x: 12, y: 608, text: "Kuşadası" }, { x: 888, y: 608, text: "Yunusemre" }];
    for (const label of layoutMapLabels(points, 900, 620)) {
      expect(label.x).toBeGreaterThanOrEqual(8);
      expect(label.y).toBeGreaterThanOrEqual(8);
      expect(label.x + label.width).toBeLessThanOrEqual(892);
      expect(label.y + label.height).toBeLessThanOrEqual(612);
    }
  });
});
