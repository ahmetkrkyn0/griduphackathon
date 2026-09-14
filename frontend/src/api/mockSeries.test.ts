import { describe, expect, it } from "vitest";
import { bucketStarts, seriesPoint, stepToMs } from "./mockSeries";

describe("stepToMs", () => {
  it("saniye/dakika/saat/gün", () => {
    expect(stepToMs("30s")).toBe(30_000);
    expect(stepToMs("15m")).toBe(15 * 60_000);
    expect(stepToMs("2h")).toBe(2 * 3_600_000);
    expect(stepToMs("1d")).toBe(86_400_000);
  });
  it("tanınmayan biçim 1 dakikaya düşer", () => expect(stepToMs("garbage")).toBe(60_000));
});

describe("bucketStarts", () => {
  it("adıma hizalı kovalar, bitiş dahil değil", () => {
    const buckets = bucketStarts(1_030, 5_030, 1_000);
    expect(buckets).toEqual([1000, 2000, 3000, 4000, 5000]);
  });
  it("aralık adımdan küçükse tek kova", () => expect(bucketStarts(0, 500, 1000)).toEqual([0]));
});

describe("seriesPoint (belirlenimlilik)", () => {
  it("aynı girdi her zaman aynı değeri üretir", () => {
    const a = seriesPoint("ADM-00014", "t_conn.DSYA3_L2.k_ratio", 1_726_300_000_000);
    const b = seriesPoint("ADM-00014", "t_conn.DSYA3_L2.k_ratio", 1_726_300_000_000);
    expect(a).toBe(b);
  });

  it("gevşek bağlantı rampası zamanla artar (K/K₀)", () => {
    const now = Date.now();
    const early = seriesPoint("ADM-00014", "t_conn.DSYA3_L2.k_ratio", now - 13 * 86_400_000)!;
    const late = seriesPoint("ADM-00014", "t_conn.DSYA3_L2.k_ratio", now - 1 * 86_400_000)!;
    expect(late).toBeGreaterThan(early);
    expect(early).toBeGreaterThanOrEqual(0.95);
    expect(late).toBeLessThanOrEqual(1.7);
  });

  it("bilinmeyen etiket grubu için null", () => expect(seriesPoint("ADM-00014", "pd.pps", Date.now())).toBeNull());

  it("sıcaklık = ortam + ΔT tutarlılığı", () => {
    const t = Date.now();
    const dt = seriesPoint("ADM-00057", "t_conn.GIRIS_N.dt_c", t)!;
    const tc = seriesPoint("ADM-00057", "t_conn.GIRIS_N.t_c", t)!;
    expect(tc).toBeCloseTo(24.1 + dt, 1);
  });
});
