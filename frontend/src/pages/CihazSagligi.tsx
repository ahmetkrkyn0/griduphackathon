import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { ago, num } from "../lib/format";
import { useFleet } from "../state/fleet";
import { Icon } from "../components/Icon";

// API'de toplu "cihaz sagligi" ucu yok (yalnizca pano-basina detay); bu yuzden gorunen
// panolar sirayla, sinirli eszamanlilikla cekilir. Kalici cozum icin bkz.
// contracts/changes/2026-09-14-fleet-health-bulk.md (3 onay bekliyor).
const CONCURRENCY = 6;

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

async function withConcurrency<T, R>(
  items: T[],
  limit: number,
  fn: (item: T) => Promise<R>,
): Promise<R[]> {
  const out: R[] = new Array(items.length);
  let i = 0;
  async function worker() {
    while (i < items.length) {
      const idx = i++;
      out[idx] = await fn(items[idx]);
    }
  }
  await Promise.all(
    Array.from({ length: Math.min(limit, items.length) }, worker),
  );
  return out;
}

/** TC3: cihaz sagligi — dugum/pano bazinda RSSI, yedek guc, tampon, yazilim surumu. */
export function CihazSagligi() {
  const { panels } = useFleet();
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadedCount, setLoadedCount] = useState(0);
  const cancelled = useRef(false);
  const [query, setQuery] = useState("");
  const [onlyAttention, setOnlyAttention] = useState(false);

  const load = async () => {
    cancelled.current = false;
    setLoading(true);
    setLoadedCount(0);
    const results = await withConcurrency(panels, CONCURRENCY, async (p) => {
      try {
        const d = await api.panel(p.pano_id);
        if (!cancelled.current) setLoadedCount((c) => c + 1);
        return {
          pano_id: p.pano_id,
          name: p.name,
          commsOk: p.comms_ok,
          lastSeen: p.last_seen,
          nodesOk: d.health.nodes_ok ?? null,
          nodesTotal: d.health.nodes_total ?? null,
          rssi: d.health.rssi_dbm ?? null,
          vbak: d.health.vbak_pct ?? null,
          buffered: d.health.buffered ?? null,
          fw: d.health.fw ?? null,
          baselineDay: d.health.baseline_day ?? null,
        } satisfies Row;
      } catch {
        return {
          pano_id: p.pano_id,
          name: p.name,
          commsOk: p.comms_ok,
          lastSeen: p.last_seen,
          nodesOk: null,
          nodesTotal: null,
          rssi: null,
          vbak: null,
          buffered: null,
          fw: null,
          baselineDay: null,
          error: "alınamadı",
        } satisfies Row;
      }
    });
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
    !r.commsOk ||
    !!r.error ||
    (r.nodesOk != null && r.nodesTotal != null && r.nodesOk < r.nodesTotal) ||
    (r.rssi != null && r.rssi < -90) ||
    (r.vbak != null && r.vbak < 40) ||
    (r.buffered ?? 0) > 0;
  const isWarn = (r: Row) =>
    !isBad(r) &&
    ((r.rssi != null && r.rssi < -80) || (r.vbak != null && r.vbak < 70));

  const sorted = [...rows]
    .filter(
      (r) =>
        (!onlyAttention || isBad(r) || isWarn(r)) &&
        `${r.name} ${r.pano_id}`
          .toLocaleLowerCase("tr")
          .includes(query.toLocaleLowerCase("tr")),
    )
    .sort(
      (a, b) =>
        Number(isBad(b)) - Number(isBad(a)) ||
        Number(isWarn(b)) - Number(isWarn(a)),
    );

  return (
    <main className="page">
      <div className="hero">
        <h1>Cihaz sağlığı</h1>
        <p>
          Sensör düğümleri, hücresel sinyal, yedek enerji ve tampon durumu —
          sessiz arıza kendisi bir alarmdır.
        </p>
      </div>
      <div className="console-filters">
        <label className="field-search">
          <Icon name="search" size={16} />
          <input
            aria-label="Cihazlarda ara"
            placeholder="Pano veya kimlik ara"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <button
          aria-pressed={onlyAttention}
          onClick={() => setOnlyAttention(!onlyAttention)}
        >
          İnceleme gerekenler ·{" "}
          {rows.filter((r) => isBad(r) || isWarn(r)).length}
        </button>
        <button onClick={() => void load()} disabled={loading}>
          {loading ? "Yenileniyor…" : "Verileri yenile"}
        </button>
        <span className="dim small">
          {sorted.length} / {panels.length} pano
        </span>
      </div>
      {loading && (
        <p className="dim small">
          Yükleniyor… ({loadedCount} / {panels.length})
        </p>
      )}

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
                  <Link to={`/pano/${r.pano_id}`}>{r.name}</Link>{" "}
                  <span className="dim small">{r.pano_id}</span>
                </td>
                <td className="r">
                  {r.error
                    ? "–"
                    : r.nodesOk != null
                      ? `${r.nodesOk} / ${r.nodesTotal}`
                      : "–"}
                </td>
                <td className="r">
                  {r.rssi != null ? `${num(r.rssi, 0)} dBm` : "–"}
                </td>
                <td className="r">
                  {r.vbak != null ? `%${num(r.vbak, 0)}` : "–"}
                </td>
                <td className="r">{r.buffered != null ? r.buffered : "–"}</td>
                <td>{r.fw ?? "–"}</td>
                <td className="r">
                  {r.baselineDay != null ? `${r.baselineDay}. gün` : "–"}
                </td>
                <td className="r">
                  {r.commsOk ? (
                    ago(r.lastSeen)
                  ) : (
                    <span className="tag-bad">{ago(r.lastSeen)}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="dim small" style={{ marginTop: 12 }}>
        Düğüm ve iletişim değerleri son sorgulama anını gösterir. Güncel durumu
        almak için verileri yenileyin.
      </p>
    </main>
  );
}
