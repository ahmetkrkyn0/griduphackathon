import { describe, expect, it } from "vitest";
import {
  insidePolygons,
  interiorLabel,
  labelFits,
  normalizeMapSearch,
  prepareLabelCandidates,
  placePreparedLabel,
  type MapPolygon,
} from "./mapGeometry";
import territories from "../data/ilce-sinirlari.json";

const square = (left: number, top: number, size: number) => [
  { x: left, y: top },
  { x: left + size, y: top },
  { x: left + size, y: top + size },
  { x: left, y: top + size },
  { x: left, y: top },
];

describe("district geometry and label containment", () => {
  it("reuses prepared geometry across zooms while keeping the full label on land", () => {
    const polygon = [square(0, 0, 24)];
    const candidates = prepareLabelCandidates([polygon]);
    expect(placePreparedLabel(candidates, 45, 11, 1, [])).toBeNull();
    for (const scale of [2.1, 2.7, 4, 6]) {
      const point = placePreparedLabel(candidates, 45, 11, scale, []);
      expect(point).not.toBeNull();
      expect(labelFits(point!, 45 / scale, 11 / scale, polygon)).toBe(true);
    }
  });

  it("prepared positions respect holes and panel markers at arbitrary zoom", () => {
    const polygon = [square(0, 0, 100), square(40, 40, 20)];
    const candidates = prepareLabelCandidates([polygon]);
    const dot = candidates[0];
    const point = placePreparedLabel(candidates, 35, 11, 1.7, [dot]);
    expect(point).not.toBeNull();
    expect(labelFits(point!, 35 / 1.7, 11 / 1.7, polygon)).toBe(true);
    expect(
      Math.abs(point!.x - dot.x) >= 24.5 / 1.7 ||
        Math.abs(point!.y - dot.y) >= 12.5 / 1.7,
    ).toBe(true);
  });
  it("matches Turkish names with spacing and ASCII keyboard variants", () => {
    expect(normalizeMapSearch("Yunus Emre")).toBe(
      normalizeMapSearch("Yunusemre"),
    );
    expect(normalizeMapSearch("İZMİR Çiğli")).toBe(
      normalizeMapSearch("izmir cigli"),
    );
    expect(normalizeMapSearch("Aydın")).toBe(normalizeMapSearch("aydin"));
  });
  it("excludes holes and supports separate islands", () => {
    const polygons = [
      [square(0, 0, 100), square(40, 40, 20)],
      [square(200, 0, 30)],
    ];
    expect(insidePolygons({ x: 50, y: 50 }, polygons)).toBe(false);
    expect(insidePolygons({ x: 210, y: 10 }, polygons)).toBe(true);
    expect(insidePolygons({ x: 150, y: 10 }, polygons)).toBe(false);
  });

  it("rejects a label that encloses a hole despite all corners being on land", () => {
    expect(
      labelFits({ x: 50, y: 50 }, 60, 60, [
        square(0, 0, 100),
        square(40, 40, 20),
      ]),
    ).toBe(false);
  });

  it("fits wide labels in narrow land without requiring an oversized enclosing circle", () => {
    const polygon: MapPolygon = [
      [
        { x: 0, y: 0 },
        { x: 150, y: 0 },
        { x: 150, y: 35 },
        { x: 0, y: 35 },
        { x: 0, y: 0 },
      ],
    ];
    const label = interiorLabel([polygon], 100, 14);
    expect(label).not.toBeNull();
    expect(labelFits(label!, 100, 14, polygon)).toBe(true);
  });

  it("defers labels that cannot fit and avoids marker hit areas", () => {
    expect(interiorLabel([[square(0, 0, 20)]], 40, 12)).toBeNull();
    const label = interiorLabel([[square(0, 0, 100)]], 35, 12, [
      { x: 50, y: 50 },
    ]);
    expect(label).not.toBeNull();
    expect(
      Math.abs(label!.x - 50) >= 28.5 || Math.abs(label!.y - 50) >= 17,
    ).toBe(true);
  });

  it("keeps the corrected Yunusemre demo coordinate within its actual district", () => {
    const geom = territories.Yunusemre.geom;
    const polygons = [
      geom.coordinates.map((ring) => ring.map(([x, y]) => ({ x, y }))),
    ];
    expect(insidePolygons({ x: 27.4023208, y: 38.6148669 }, polygons)).toBe(
      true,
    );
    expect(insidePolygons({ x: 27.44, y: 38.617 }, polygons)).toBe(false);
  });
});
