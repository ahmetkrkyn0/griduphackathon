import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { ago, num } from "../lib/format";
import { useFleet } from "../state/fleet";

// 18 Eylul 2026: bu ekran gorunen her pano icin AYRI GET /panels/{id} cagiriyordu
// (sinirli eszamanlilikla, 6). Artik tek istek: GET /fleet/health
// (contracts/changes/2026-09-14-fleet-health-bulk.md kabul edildi, openapi v1.1.0).
// Ucun pano-basina uctan farkli bir sey sormadigi backend'de kilitli:
// test_fleet_health_matches_panel_detail.

interface Row {
  pano_id: string;
  name: string;
  nodesOk: number | null;
  nodesTotal: number | null;
  rssi: number | null;
  vbak: number | null;
  buffered: number | null;
  fw: string | null;
  lastSeen: string;
  commsOk: boolean;
  baselineDay: number | null;
  error?: string;
}

/** TC3: cihaz sagligi — dugum/pano bazinda RSSI, yedek guc, tampon, yazilim surumu. */
export function CihazSagligi() {
  const { panels } = useFleet();
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);
  const cancelled = useRef(false);

  const load = async () => {
    cancelled.current = false;
    setLoading(true);
    let results: Row[];
    try {
      results = (await api.fleetHealth()).map((h) => ({
        pano_id: h.pano_id, name: h.name, commsOk: h.comms_ok, lastSeen: h.last_seen,
        nodesOk: h.nodes_ok, nodesTotal: h.nodes_total,
        rssi: h.rssi_dbm, vbak: h.vbak_pct,
        buffered: h.buffered, fw: h.fw,
        baselineDay: h.baseline_day,
      }));
    } catch {
      // Tek istek: ya hepsi gelir ya hicbiri. Filo listesinden bilinen alanlarla
      // (ad, haberlesme, son gorulme) satirlar yine cizilir ki ekran bos kalmasin.
      results = panels.map((p) => ({
        pano_id: p.pano_id, name: p.name, commsOk: p.comms_ok, lastSeen: p.last_seen,
        nodesOk: null, nodesTotal: null, rssi: null, vbak: null, buffered: null, fw: null, baselineDay: null,
        error: "alınamadı",
      }));
    }
    if (!cancelled.current) {
      setRows(results);
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    return () => {
      cancelled.current = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [panels.length]);

  const isBad = (r: Row) =>
    !r.commsOk || !!r.error || (r.nodesOk != null && r.nodesTotal != null && r.nodesOk < r.nodesTotal) || (r.rssi != null && r.rssi < -90) || (r.vbak != null && r.vbak < 40) || (r.buffered ?? 0) > 0;
  const isWarn = (r: Row) => !isBad(r) && ((r.rssi != null && r.rssi < -80) || (r.vbak != null && r.vbak < 70));

  const sorted = [...rows].sort((a, b) => Number(isBad(b)) - Number(isBad(a)) || Number(isWarn(b)) - Number(isWarn(a)));

  return (
    <main className="page">
      <div className="hero">
        <h1>Cihaz sağlığı</h1>
        <p>Sensör düğümleri, hücresel sinyal, yedek enerji ve tampon durumu — sessiz arıza kendisi bir alarmdır.</p>
      </div>
      {loading && <p className="dim small">Yükleniyor…</p>}

      <div className="tbl-wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th>Pano</th>
              <th className="r">Düğümler</th>
              <th className="r">Hücresel sinyal</th>
              <th className="r">Yedek güç</th>
              <th className="r">Tampon</th>
              <th>Yazılım</th>
              <th className="r">Taban öğrenme</th>
              <th className="r">Son veri</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr key={r.pano_id} className={isBad(r) ? "sel" : undefined}>
                <td>
                  <Link to={`/pano/${r.pano_id}`}>{r.name}</Link> <span className="dim small">{r.pano_id}</span>
                </td>
                <td className="r">{r.error ? "–" : r.nodesOk != null ? `${r.nodesOk} / ${r.nodesTotal}` : "–"}</td>
                <td className="r">{r.rssi != null ? `${num(r.rssi, 0)} dBm` : "–"}</td>
                <td className="r">{r.vbak != null ? `%${num(r.vbak, 0)}` : "–"}</td>
                <td className="r">{r.buffered != null ? r.buffered : "–"}</td>
                <td>{r.fw ?? "–"}</td>
                <td className="r">{r.baselineDay != null ? `${r.baselineDay}. gün` : "–"}</td>
                <td className="r">{r.commsOk ? ago(r.lastSeen) : <span className="tag-bad">{ago(r.lastSeen)}</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="dim small" style={{ marginTop: 12 }}>
        Bu tablo tüm filoyu <strong>tek istekte</strong> çeker (<code>GET /api/v1/fleet/health</code>). Önceki sürümde
        görünen her pano için ayrı bir detay isteği atılıyordu; 18 Eylül'de toplu uç eklendi (
        <code>contracts/changes/2026-09-14-fleet-health-bulk.md</code>). “–” işareti <em>veri gelmedi</em> demektir,
        sıfır demek değildir.
      </p>
    </main>
  );
}
