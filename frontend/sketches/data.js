// Sketch icin sahte veri. Alan adlari contracts/openapi.yaml ile uyumlu tutuldu
// (PanelSummary, PanelDetail, ConnPoint, Alarm). Gercek uygulamada API'den gelir.
// Esikler burada YOK: nokta rengi API'nin verdigi ConnPoint.state'ten okunur (kural 10).

(function () {
  const phaseLabel = (pt) => {
    if (pt.startsWith("GIRIS_")) return "Giriş " + pt.slice(6);
    const m = pt.match(/^DSYA(\d)_(L\d)$/);
    return m ? `DSYA-${m[1]} ${m[2]}` : pt;
  };

  // 25 olcum noktasi: 4 giris + 7 DSYA x 3 faz. DSYA-6/7 yedek (yuksuz).
  const points = [];
  const girisDt = { L1: 28.4, L2: 29.1, L3: 27.6, N: 9.8 };
  for (const p of ["L1", "L2", "L3", "N"]) {
    points.push({ pt: "GIRIS_" + p, t_c: +(24.1 + girisDt[p]).toFixed(1), dt_c: girisDt[p], k_ratio: 1.02, ttl_h: null, q: 0, state: "normal" });
  }
  const dsyaBase = [19.2, 22.8, 21.4, 17.6, 15.9, 1.8, 1.6];
  for (let d = 1; d <= 7; d++) {
    for (const [i, p] of ["L1", "L2", "L3"].entries()) {
      const dt = +(dsyaBase[d - 1] + [0.4, -0.3, 0.1][i]).toFixed(1);
      points.push({ pt: `DSYA${d}_${p}`, t_c: +(24.1 + dt).toFixed(1), dt_c: dt, k_ratio: d >= 6 ? null : 1.0 + i * 0.02, ttl_h: null, q: 0, state: "normal" });
    }
  }
  const s1 = points.find((x) => x.pt === "DSYA3_L2");
  Object.assign(s1, { t_c: 58.4, dt_c: 34.3, k_ratio: 1.64, ttl_h: 146, state: "alarm" });
  points.forEach((x) => (x.label = phaseLabel(x.pt)));

  window.MOCK = {
    phaseLabel,
    kpi: {
      panels_total: 1000,
      comms_ok_pct: 99.4,
      alarms_per_100_panels_per_day: 3.1,
      p95_end_to_end_ms: 606,
      normal_count: 994,
    },

    // Operatorun is listesi: aciliyete gore sirali (P1 > zaman sinirli > digerleri)
    worklist: [
      { pano_id: "GDZ-00231", name: "Bornova DM-3", il: "İzmir", prio: "P1", code: "ALM-PROT-HEALTH",
        headline: "Ark koruması X2:4 dedektörü arızalı, pano korumasız",
        since_min: 3, ttl_h: null, acked: false, next: "2 dk sonra sesli arama" },
      { pano_id: "GDZ-00410", name: "Karşıyaka TM-9", il: "İzmir", prio: "SYS", code: "ALM-COMMS-LOST",
        headline: "7 dakikadır veri gelmiyor",
        since_min: 7, ttl_h: null, acked: false, next: "arıza alarmı değil, cihaz kontrolü" },
      { pano_id: "ADM-00102", name: "Merkezefendi TM-7", il: "Denizli", prio: "P2", code: "ALM-DEW-ALM",
        headline: "Çiy noktası marjı 0,8 K, yoğuşma riski",
        since_min: 18, ttl_h: null, acked: true, next: "ısıtıcı otomatik açıldı" },
      { pano_id: "ADM-00014", name: "Efeler TM-14", il: "Aydın", prio: "P2", code: "ALM-K-ALM",
        headline: "DSYA-3 L2 bağlantısı gevşiyor",
        since_min: 41, ttl_h: 146, acked: false, next: "6 gün sonra 70 K sınırı" },
      { pano_id: "GDZ-00088", name: "Yunusemre TM-21", il: "Manisa", prio: "P2", code: "ALM-I-OVER",
        headline: "Üç fazda akım anma değerinin üstünde, arıza değil aşırı yük",
        since_min: 66, ttl_h: null, acked: true, next: "yük aktarma önerisi" },
      { pano_id: "ADM-00057", name: "Bodrum TM-2", il: "Muğla", prio: "P3", code: "ALM-TTL-14D",
        headline: "Giriş N bağlantısı ısınma eğiliminde",
        since_min: 320, ttl_h: 290, acked: false, next: "planlı bakıma eklenecek" },
    ],

    // Secili pano detayi (PanelDetail)
    detail: {
      pano_id: "ADM-00014",
      name: "Efeler TM-14",
      il: "Aydın",
      pano_type: "1600 kVA dahili",
      ts_age_s: 10,
      risk_score: 72,
      risk_mode: "HYP-LOOSE-CONN",
      baseline_day: 42,
      points,
      env: { t_low_c: 24.1, rh_low_pct: 61, td_low_c: 16.1, td_margin_k: 7.9, t_up_c: 31.8, rh_up_pct: 44, dt_air_k: 7.7, door_open: false },
      elec: { i_ph: [612, 655, 598], i_n: 48, u_ph: [229.8, 231.2, 230.4], thd_i: [6.1, 6.8, 5.9], cosphi: 0.96, unbal_pct: 4.6, mpr_comm_ok: true },
      tvoc: { trips: 0, prot_health_ok: true, comm_ok: true, last_trip_at: null },
      health: { nodes_ok: 25, nodes_total: 25, rssi_dbm: -71, vbak_pct: 100, buffered: 0, fw: "0.3.1", maint_mode: false },
      alarm: {
        id: "42", event_id: "EVT-17", code: "ALM-K-ALM", prio: "P2", state: "active", raised_min: 41,
        escalation_level: 0, notified: ["sms", "whatsapp"],
        reason: {
          signals: [
            { tag: "DSYA-3 L2 ısıl direnç indeksi", value: 1.64, threshold: 1.6, unit: "K/K₀" },
            { tag: "DSYA-3 faz farkı (L2 − L3)", value: 12.8, threshold: 15, unit: "K" },
          ],
          layer: "L1", point: "DSYA3_L2", basis: "Isıl direnç indeksi, 42 günlük taban",
        },
        advice: "Planlı bakımda DSYA-3 L2 kablo pabucunda tork kontrolü ve temas yüzeyi temizliği. O zamana kadar fider yükünü %80'in altında tutun.",
        ttl_h: 146,
      },
      // K/K0 gecmisi (son 14 gun, gunluk) — trend mini grafigi icin
      k_history: [1.01, 1.02, 1.02, 1.05, 1.08, 1.11, 1.16, 1.21, 1.27, 1.33, 1.40, 1.47, 1.55, 1.64],
    },
  };

  // Sure bicimleme: saat -> "6 gün" / "18 saat"
  window.MOCK.fmtTtl = (h) => {
    if (h == null) return null;
    if (h < 48) return `${Math.round(h)} saat`;
    return `${Math.round(h / 24)} gün`;
  };
  window.MOCK.fmtSince = (m) => (m < 60 ? `${m} dk önce` : `${Math.floor(m / 60)} sa ${m % 60} dk önce`);
  window.MOCK.num = (v, d = 1) => v.toLocaleString("tr-TR", { minimumFractionDigits: d, maximumFractionDigits: d });
})();
