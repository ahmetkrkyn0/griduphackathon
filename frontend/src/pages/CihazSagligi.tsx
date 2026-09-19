import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { ago, num } from "../lib/format";
import { useFleet } from "../state/fleet";
import { Icon } from "../components/Icon";

// Toplu "cihaz sagligi" ucu (contracts/changes/2026-09-14-fleet-health-bulk.md,
// openapi v1.1.0). 18 Eylul 2026 oncesinde bu ekran gorunen her pano icin AYRI
// GET /panels/{id} cagiriyordu; artik tek istek yetiyor: GET /api/v1/fleet/health.
// Ucun pano-basina uctan farkli bir sey sormadigi backend'de kilitli:
// test_fleet_health_matches_panel_detail.
//
// Uc LIMIT PARAMETRESI ALMIYOR (backend/app/api/views.py -> panel_health): cagriya
// ?limit= eklenmez, filo tek seferde doner.
//
// Geriye donuk uyum: toplu uc yoksa ya da hata dondururse tek tek (eszamanlilik 6)
// cekilir; eski bir backend'e bakan arayuz de bos kalmaz.
const CONCURRENCY = 6;

interface Row {
  pano_id: string;
  name: string;
  nodesOk: number | null;
  nodesTotal: number | null;
  rssi: number | null;
  vbak: number | null;
  buffered: number | null;
  /** Bakim kipi: true ise saha ekibi panoda calisiyor olabilir. null = bilinmiyor. */
  maintMode: boolean | null;
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
  const [usedBulk, setUsedBulk] = useState(false);
  const cancelled = useRef(false);
  const [query, setQuery] = useState("");
  const [onlyAttention, setOnlyAttention] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(50);

  const load = async () => {
    cancelled.current = false;
    setLoading(true);
    setLoadedCount(0);

    // 1. Oncelikle yuksek verimli toplu filo ucunu dene. Cagri PARAMETRESIZ:
    //    backend ?limit= kabul etmiyor, tum filo tek istekte doner.
    //    `?.()` ucu tanimlamayan bir `api` nesnesinde sessizce undefined dondurur
    //    (Api.fleetHealth opsiyonel), `catch` ise hata dondurenlerde ayni sonucu verir;
    //    iki durumda da asagidaki pano-basina geri-uyum yoluna dusulur.
    const bulk = await api.fleetHealth?.().catch(() => undefined);
    if (bulk) {
      if (!cancelled.current) {
        const bulkRows: Row[] = bulk.map((item) => ({
          pano_id: item.pano_id,
          name: item.name ?? item.pano_id,
          commsOk: item.comms_ok,
          lastSeen: item.last_seen,
          nodesOk: item.nodes_ok,
          nodesTotal: item.nodes_total,
          rssi: item.rssi_dbm,
          vbak: item.vbak_pct,
          buffered: item.buffered,
          maintMode: item.maint_mode ?? null,
          fw: item.fw,
          baselineDay: item.baseline_day ?? null,
        }));
        setRows(bulkRows);
        setLoadedCount(bulkRows.length);
        setUsedBulk(true);
        setLoading(false);
      }
      return;
    }

    // 2. Toplu uc yoksa ya da hata dondurduyse tek tek cekim dongusune dus.
    setUsedBulk(false);
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
          maintMode: d.health.maint_mode ?? null,
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
          maintMode: null,
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

  // Esikler YALNIZCA deger geldiyse uygulanir. `null` "bilinmiyor" demektir ve 0 ile
  // ayni sey DEGILDIR: 0 dBm gecerli bir RSSI, %0 yedek guc gercek bir arizadir.
  // Eksik alani 0 sayan bir kisayol, veri gondermemis her panoyu kirmiziya boyar
  // (backend de ayni sozu tutuyor: views.py panel_health).
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

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const paged = sorted.slice((currentPage - 1) * pageSize, currentPage * pageSize);

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
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(1);
            }}
          />
        </label>
        <button
          aria-pressed={onlyAttention}
          onClick={() => {
            setOnlyAttention(!onlyAttention);
            setPage(1);
          }}
        >
          İnceleme gerekenler ·{" "}
          {rows.filter((r) => isBad(r) || isWarn(r)).length}
        </button>
        <button onClick={() => void load()} disabled={loading}>
          {loading ? "Yenileniyor…" : "Verileri yenile"}
        </button>
        {usedBulk && (
          <span className="tag-ok small" title="Tek HTTP isteğiyle toplu çekildi">
            <Icon name="check" size={13} /> Toplu Uç (O(1))
          </span>
        )}
        <select
          value={pageSize}
          onChange={(e) => {
            setPageSize(Number(e.target.value));
            setPage(1);
          }}
          className="small"
          style={{ background: "transparent", border: "1px solid var(--border)", color: "inherit", borderRadius: 4, padding: "2px 6px" }}
          aria-label="Sayfa boyutu"
        >
          <option value={25}>Sayfa: 25</option>
          <option value={50}>Sayfa: 50</option>
          <option value={100}>Sayfa: 100</option>
          <option value={2000}>Tümü</option>
        </select>
        <span className="dim small">
          {sorted.length} / {panels.length} pano
        </span>
      </div>
      {loading && (
        <p className="dim small">
          {loadedCount > 0
            ? `Yükleniyor… ${loadedCount} / ${panels.length} pano`
            : "Yükleniyor…"}
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
            {paged.map((r) => (
              <tr key={r.pano_id} className={isBad(r) ? "sel" : undefined}>
                <td>
                  <Link to={`/pano/${r.pano_id}`}>{r.name}</Link>{" "}
                  <span className="dim small">{r.pano_id}</span>
                  {/* Bakim kipi (F-21): sahadaki ekip panoyu acmis olabilir, bozulma
                      gibi gorunen degerlerin sebebi planli calisma olabilir. Yalnizca
                      uc bunu ACIKCA true dondurunce cizilir; null'da rozet yok. */}
                  {r.maintMode === true && (
                    <>
                      {" "}
                      <span
                        className="badge-shelved"
                        title="Pano bakım kipinde — değerler planlı çalışmadan kaynaklanıyor olabilir"
                      >
                        bakımda
                      </span>
                    </>
                  )}
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
      {totalPages > 1 && (
        <div style={{ display: "flex", gap: 8, alignItems: "center", justifyContent: "center", margin: "16px 0" }}>
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={currentPage <= 1} className="small">
            Önceki
          </button>
          <span className="small dim">
            Sayfa {currentPage} / {totalPages} ({(currentPage - 1) * pageSize + 1} - {Math.min(currentPage * pageSize, sorted.length)} / {sorted.length})
          </span>
          <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={currentPage >= totalPages} className="small">
            Sonraki
          </button>
        </div>
      )}
      <p className="dim small" style={{ marginTop: 12 }}>
        Düğüm ve iletişim değerleri son sorgulama anını gösterir. Güncel durumu
        almak için verileri yenileyin. Tablo tüm filoyu <strong>tek istekte</strong>{" "}
        çeker (<code>GET /api/v1/fleet/health</code>); toplu uç yanıt vermezse pano
        pano geri düşülür. “–” işareti <em>veri gelmedi</em> demektir, sıfır demek
        değildir.
      </p>
    </main>
  );
}
