import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { ADVICE_TEXT, ALARM_TEXT, HYP_TEXT, adviceText, panoTypeText, pointLabel, signalLabel, unitText } from "./labels";

// Sozluk sozlesmeden kopmasin: yeni kod eklenirse bu test Turkce metni ister.
const contract = readFileSync(new URL("../../../contracts/alarm-codes.yaml", import.meta.url), "utf8");
const alarmCodes = [...contract.matchAll(/^\s*- code: (ALM-[A-Z0-9-]+)\s*$/gm)].map((m) => m[1]);
const hypCodes = [...contract.matchAll(/^\s*code: (HYP-[A-Z-]+)\s*$/gm)].map((m) => m[1]);
const advices = [...contract.matchAll(/^\s*advice: "(.*)"\s*$/gm)].map((m) => m[1]).filter((a) => a !== "-");

describe("sözleşme ile sözlük eşleşmesi", () => {
  it("sözleşmedeki kodlar okunabiliyor", () => {
    expect(alarmCodes.length).toBeGreaterThanOrEqual(20);
    expect(hypCodes.length).toBeGreaterThanOrEqual(8);
  });
  it("her alarm kodunun Türkçe metni var", () => expect(alarmCodes.filter((c) => !(c in ALARM_TEXT))).toEqual([]));
  it("sözlükte sözleşmede olmayan alarm kodu yok", () => expect(Object.keys(ALARM_TEXT).filter((c) => !alarmCodes.includes(c))).toEqual([]));
  it("her hipotezin Türkçe adı var", () => expect(hypCodes.filter((c) => !(c in HYP_TEXT))).toEqual([]));
  it("her önerinin Türkçe karşılığı var", () => expect(advices.filter((a) => !(a in ADVICE_TEXT))).toEqual([]));
  it("Türkçe metinler eşik sayısı içermez (kural 10)", () => {
    const withNumbers = Object.entries(ALARM_TEXT).filter(([, text]) => /\d+\s*(K|°C|degC|%)/.test(text));
    expect(withNumbers).toEqual([]);
  });
});

describe("pointLabel", () => {
  it("giriş noktası", () => expect(pointLabel("GIRIS_N")).toBe("Giriş N"));
  it("DSYA noktası", () => expect(pointLabel("DSYA3_L2")).toBe("DSYA-3 L2"));
  it("bilinmeyen nokta olduğu gibi", () => expect(pointLabel("XYZ")).toBe("XYZ"));
});

describe("signalLabel", () => {
  it("bağlantı noktası alanı", () => expect(signalLabel("t_conn.DSYA3_L2.k_ratio")).toBe("DSYA-3 L2 ısıl direnç indeksi"));
  it("faz dizisi 0 tabanlı indeks", () => expect(signalLabel("elec.i_ph.1")).toBe("L2 faz akımı"));
  it("ortam alanı", () => expect(signalLabel("env.td_margin_k")).toBe("Çiy noktası marjı"));
  it("bilinmeyen etiket olduğu gibi", () => expect(signalLabel("pd.pps")).toBe("pd.pps"));
});

describe("küçük dönüştürücüler", () => {
  it("birim", () => {
    expect(unitText("K/K0")).toBe("K/K₀");
    expect(unitText(undefined)).toBe("");
  });
  it("öneri: bilinmeyen metin olduğu gibi, '-' boş", () => {
    expect(adviceText("serbest metin")).toBe("serbest metin");
    expect(adviceText("-")).toBeNull();
  });
  it("pano tipi", () => expect(panoTypeText("1600kVA-dahili")).toBe("1600 kVA dahili"));
});
