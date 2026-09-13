import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { ConnPoint } from "../api/types";
import { PANEL_MM, phaseGroup, pointPos } from "./panelGeometry";

// Cizim sozlesmedeki nokta listesinden kopmasin.
const modbusMap = readFileSync(new URL("../../../contracts/modbus-map.yaml", import.meta.url), "utf8");
const contractPoints = [...new Set(modbusMap.match(/\b(?:GIRIS_(?:L[123]|N)|DSYA\d_L[123])\b/g) ?? [])];

describe("pointPos", () => {
  it("sözleşmedeki 25 noktanın hepsini çizime yerleştirir", () => {
    expect(contractPoints).toHaveLength(25);
    expect(contractPoints.filter((pt) => pointPos(pt) === null)).toEqual([]);
  });

  it("noktalar gövdenin içinde ve üst üste binmiyor", () => {
    const keys = contractPoints.map((pt) => {
      const pos = pointPos(pt)!;
      expect(pos.x).toBeGreaterThan(0);
      expect(pos.x).toBeLessThan(PANEL_MM.width);
      expect(pos.y).toBeGreaterThan(0);
      expect(pos.y).toBeLessThan(PANEL_MM.height);
      return `${pos.x},${pos.y}`;
    });
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("bilinmeyen nokta için null", () => expect(pointPos("DSYA3_L4")).toBeNull());
});

describe("phaseGroup", () => {
  const pts = (ids: string[]): ConnPoint[] => ids.map((pt) => ({ pt, t_c: 0, dt_c: 0 }));

  it("aynı çıkışın fazları L1-L2-L3 sırasıyla", () =>
    expect(phaseGroup(pts(["DSYA3_L3", "DSYA2_L1", "DSYA3_L1", "DSYA3_L2"]), "DSYA3_L2").map((p) => p.pt)).toEqual([
      "DSYA3_L1",
      "DSYA3_L2",
      "DSYA3_L3",
    ]));

  it("giriş grubunda nötr sonda", () =>
    expect(phaseGroup(pts(["GIRIS_N", "GIRIS_L2", "GIRIS_L1", "DSYA1_L1"]), "GIRIS_N").map((p) => p.pt)).toEqual([
      "GIRIS_L1",
      "GIRIS_L2",
      "GIRIS_N",
    ]));
});
