import { describe, expect, it } from "vitest";
import { ago, measure, num, ttlText } from "./format";

describe("num", () => {
  it("Türkçe ondalık ayırıcı kullanır", () => expect(num(1.64, 2)).toBe("1,64"));
  it("binlik ayırıcı nokta", () => expect(num(2410, 0)).toBe("2.410"));
  it("eksik değer tire", () => {
    expect(num(null)).toBe("–");
    expect(num(Number.NaN)).toBe("–");
  });
});

describe("measure", () => {
  it("küçük oranı iki haneyle", () => expect(measure(0.8)).toBe("0,80"));
  it("tamsayıyı ondalıksız", () => expect(measure(2410)).toBe("2.410"));
  it("büyük ondalığı tek haneyle", () => expect(measure(34.25)).toBe("34,3"));
});

describe("ttlText", () => {
  it("48 saatin altında saat", () => expect(ttlText(30)).toBe("30 saat"));
  it("48 saat ve üstünde gün", () => expect(ttlText(146)).toBe("6 gün"));
  it("bir saatten az", () => expect(ttlText(0.4)).toBe("1 saatten az"));
  it("bilinmiyorsa null", () => expect(ttlText(null)).toBeNull());
});

describe("ago", () => {
  const now = Date.parse("2026-09-14T10:00:00Z");
  it("saniye", () => expect(ago("2026-09-14T09:59:50Z", now)).toBe("10 sn önce"));
  it("dakika", () => expect(ago("2026-09-14T09:53:00Z", now)).toBe("7 dk önce"));
  it("saat", () => expect(ago("2026-09-14T07:00:00Z", now)).toBe("3 sa önce"));
  it("gün", () => expect(ago("2026-09-11T10:00:00Z", now)).toBe("3 gün önce"));
  it("saat kayması gelecekte gösterse de negatif olmaz", () => expect(ago("2026-09-14T10:00:05Z", now)).toBe("0 sn önce"));
});
