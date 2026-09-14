import { describe, expect, it } from "vitest";
import type { Alarm, PanelDetail, PanelSummary } from "../api/types";
import {
  AXIS_HOURS,
  axisFraction,
  effectivePrio,
  fleetHeadline,
  layoutAxisRows,
  panelStatement,
  primaryAlarm,
  sortWorklist,
  type AxisGeometry,
} from "./worklist";

const panel = (over: Partial<PanelSummary>): PanelSummary => ({
  pano_id: "ADM-00001", name: "Test", risk_score: 0, risk_mode: "HYP-NORMAL", top_alarm: null, top_prio: null,
  ttl_h: null, last_seen: "2026-09-14T10:00:00Z", comms_ok: true, ...over,
});
const alarm = (over: Partial<Alarm>): Alarm => ({
  id: "1", pano_id: "ADM-00001", code: "ALM-K-WARN", prio: "P3", state: "active", raised_at: "2026-09-14T09:00:00Z", ...over,
});
const detail = (over: Partial<PanelDetail> = {}): PanelDetail => ({
  pano_id: "ADM-00001", ts: "2026-09-14T10:00:00Z", points: [{ pt: "GIRIS_L1", t_c: 40, dt_c: 15 }], env: {}, elec: {}, health: {}, ...over,
});

describe("effectivePrio", () => {
  it("normal pano iş listesine girmez", () => expect(effectivePrio(panel({}))).toBeNull());
  it("bilgi önceliği iş listesine girmez", () => expect(effectivePrio(panel({ top_prio: "INFO" }))).toBeNull());
  it("haberleşmesi kopan pano alarmsız da sistem önceliği alır", () => expect(effectivePrio(panel({ comms_ok: false }))).toBe("SYS"));
  it("haberleşme kopsa da mevcut alarm önceliği korunur", () => expect(effectivePrio(panel({ comms_ok: false, top_prio: "P1" }))).toBe("P1"));
});

describe("sortWorklist", () => {
  it("önce öncelik, sonra sınıra kalan süre, sonra risk; normal panolar dışarıda", () => {
    const list = sortWorklist([
      panel({ pano_id: "ADM-00005", top_prio: "P3", ttl_h: 50 }),
      panel({ pano_id: "ADM-00004", top_prio: "P2", ttl_h: null, risk_score: 90 }),
      panel({ pano_id: "ADM-00003", top_prio: "P2", ttl_h: 100, risk_score: 10 }),
      panel({ pano_id: "ADM-00002", comms_ok: false }),
      panel({ pano_id: "ADM-00001", top_prio: "P1" }),
      panel({ pano_id: "ADM-00006" }),
    ]);
    expect(list.map((p) => p.pano_id)).toEqual(["ADM-00001", "ADM-00003", "ADM-00004", "ADM-00002", "ADM-00005"]);
  });
});

describe("axisFraction", () => {
  it("uçlar", () => {
    expect(axisFraction(0)).toBe(0);
    expect(axisFraction(AXIS_HOURS)).toBe(1);
  });
  it("pencere dışını kırpar", () => {
    expect(axisFraction(-5)).toBe(0);
    expect(axisFraction(AXIS_HOURS * 3)).toBe(1);
  });
  it("yakın gelecek eksenin daha büyük kısmını alır", () => expect(axisFraction(24)).toBeGreaterThan(0.5));
});

describe("layoutAxisRows", () => {
  // 1000 px eksen: kullanilabilir alan 100..900 px, kart 200 px
  const geometry: AxisGeometry = { trackPx: 1000, startPx: 100, endPadPx: 100, cardPx: 200, rows: 3 };

  it("birbirinden uzak kartlar aynı satırda kalır", () => expect(layoutAxisRows([0, 0.5, 1], geometry)).toEqual([0, 0, 0]));
  it("yakın kartlar alt satırlara iner", () => expect(layoutAxisRows([0.5, 0.55, 0.6], geometry)).toEqual([0, 1, 2]));
  it("boşalan satır yeniden kullanılır", () => expect(layoutAxisRows([0.1, 0.15, 0.5], geometry)).toEqual([0, 1, 0]));
  it("satır kalmazsa en az çakışan satıra koyar", () => expect(layoutAxisRows([0.5, 0.5, 0.5, 0.5], geometry)).toEqual([0, 1, 2, 0]));
  it("genişlik ölçülmeden önce de satır sınırını aşmaz", () =>
    expect(Math.max(...layoutAxisRows([0, 0.2, 0.4, 0.6, 0.8], { ...geometry, trackPx: 0 }))).toBeLessThan(geometry.rows));
});

describe("fleetHeadline", () => {
  it("boş liste", () => expect(fleetHeadline([])).toBe("Tüm panolar normal çalışıyor."));
  it("şimdi ve yaklaşan", () =>
    expect(fleetHeadline([panel({ top_prio: "P1" }), panel({ top_prio: "P2", ttl_h: 146 })])).toBe(
      "1 pano şimdi ilgi bekliyor, 1 pano önümüzdeki 14 günde sınıra ulaşıyor.",
    ));
  it("yalnızca pencere dışı süre", () => expect(fleetHeadline([panel({ top_prio: "P3", ttl_h: AXIS_HOURS + 1 })])).toBe("1 pano izlemede."));
});

describe("primaryAlarm", () => {
  it("en acil öncelik kazanır", () => expect(primaryAlarm([alarm({ id: "a", prio: "P3" }), alarm({ id: "b", prio: "P1" })])?.id).toBe("b"));
  it("aynı öncelikte onaysız önce", () =>
    expect(primaryAlarm([alarm({ id: "a", prio: "P2", state: "acked" }), alarm({ id: "b", prio: "P2" })])?.id).toBe("b"));
  it("temizlenmiş alarm seçilmez", () => expect(primaryAlarm([alarm({ state: "cleared" })])).toBeNull());
  it("girdiyi değiştirmez", () => {
    const input = [alarm({ id: "a", prio: "P3" }), alarm({ id: "b", prio: "P1" })];
    primaryAlarm(input);
    expect(input.map((a) => a.id)).toEqual(["a", "b"]);
  });
});

describe("panelStatement", () => {
  it("noktalı ve süreli alarm", () =>
    expect(panelStatement(detail(), alarm({ ttl_h: 146, reason: { point: "DSYA3_L2" } }))).toBe(
      "DSYA-3 L2 bağlantısı, yük değişmezse yaklaşık 6 gün sonra sıcaklık sınırını aşacak.",
    ));
  it("süresiz alarm Türkçe metnini kullanır", () =>
    expect(panelStatement(detail(), alarm({ code: "ALM-COMMS-LOST", prio: "SYS" }))).toBe("Merkez bağlantısı koptu."));
  it("alarm yok", () => expect(panelStatement(detail(), null)).toBe("Pano normal çalışıyor."));
  it("hiç veri yok", () => expect(panelStatement(detail({ points: [] }), null)).toBe("Bu panodan henüz veri gelmedi."));
});
