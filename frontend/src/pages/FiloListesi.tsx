import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Icon } from "../components/Icon";
import { RiskMatrisi } from "../components/RiskMatrisi";
import { SureEkseni } from "../components/SureEkseni";
import { ago, num, ttlText } from "../lib/format";
import { PRIO_NAME, hypText } from "../lib/labels";
import { useNow } from "../lib/useNow";
import type { PanelSummary } from "../api/types";
import {
  effectivePrio,
  needsAttention,
  panelHeadline,
  sortWorklist,
} from "../lib/worklist";
import { useFleet } from "../state/fleet";

function exportFleetCsv(panels: PanelSummary[]) {
  const headers = ["Pano ID", "Pano Adı", "Risk Skoru", "Öncelik", "Tanı", "Kalan Süre (Saat)", "Haberleşme", "Son Görülme"];
  const rows = panels.map((p) => [
    p.pano_id,
    `"${p.name.replace(/"/g, '""')}"`,
    p.risk_score,
    effectivePrio(p) ?? "Normal",
    `"${(p.risk_mode ?? "").replace(/"/g, '""')}"`,
    p.ttl_h != null ? p.ttl_h : "",
    p.comms_ok ? "Bağlı" : "Kopuk",
    p.last_seen,
  ]);
  const csvContent = "\uFEFF" + [headers.join(";"), ...rows.map((r) => r.join(";"))].join("\r\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const dateStr = new Date().toISOString().slice(0, 10);
  link.setAttribute("href", url);
  link.setAttribute("download", `gridup-pano-envanteri-${dateStr}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function FiloListesi() {
  const { panels, loaded, error, kpi } = useFleet();
  const [view, setView] = useState("risk");
  const [filter, setFilter] = useState("attention");
  const [company, setCompany] = useState("");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("priority");
  useNow(5000);
  const worklist = useMemo(() => sortWorklist(panels), [panels]);
  const normal = panels.filter((p) => !needsAttention(p));
  const critical = panels.filter((p) => effectivePrio(p) === "P1");
  const online = panels.filter((p) => p.comms_ok).length;
  const visible = [
    ...(filter === "attention"
      ? worklist
      : filter === "normal"
        ? normal
        : [...worklist, ...normal]),
  ]
    .filter(
      (p) =>
        (!company || p.pano_id.startsWith(company)) &&
        `${p.name} ${p.pano_id}`
          .toLocaleLowerCase("tr")
          .includes(query.toLocaleLowerCase("tr")),
    )
    .sort((a, b) =>
      sort === "risk"
        ? b.risk_score - a.risk_score
        : sort === "name"
          ? a.name.localeCompare(b.name, "tr")
          : 0,
    );
  if (!loaded)
    return (
      <main className="page">
        <div className="loading-state">
          <Icon name="pulse" size={32} />
          <h1>Operasyon verileri yükleniyor</h1>
          <p>Panoların son durumu alınıyor…</p>
        </div>
      </main>
    );
  if (error && !panels.length)
    return (
      <main className="page">
        <div className="empty">
          <h1>Filo verisi alınamadı</h1>
          <p>{error}</p>
          <p>Veri bağlantısını kontrol edip sayfayı yenileyin.</p>
        </div>
      </main>
    );
  if (!panels.length)
    return (
      <main className="page">
        <div className="empty">
          <h1>Henüz pano yok</h1>
          <p>İlk pano veri gönderdiğinde burada görünecek.</p>
        </div>
      </main>
    );
  return (
    <main className="page fleet-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">FİLO GÖRÜNÜRLÜĞÜ</span>
          <h1>Operasyon özeti</h1>
          <p>Öncelikleri görün, doğru panoya odaklanın.</p>
        </div>
        <Link className="btn ghost" to="/bolge">
          <Icon name="map" /> Bölgeyi görüntüle
        </Link>
      </div>
      <section className="metric-strip" aria-label="Filo özeti">
        <div className="metric">
          <span>
            <Icon name="cabinet" /> İzlenen pano
          </span>
          <strong>
            {panels.length}
            <small>varlık</small>
          </strong>
          <p>ADM ve GDZ dağıtım bölgeleri</p>
        </div>
        <div className="metric critical">
          <span>
            <Icon name="alarm" /> Kritik öncelik
          </span>
          <strong>
            {critical.length}
            <small>pano</small>
          </strong>
          <Link to="/alarmlar">
            Alarm merkezini aç <Icon name="arrow" size={14} />
          </Link>
        </div>
        <div className="metric">
          <span>
            <Icon name="clock" /> İnceleme bekleyen
          </span>
          <strong>
            {worklist.length}
            <small>pano</small>
          </strong>
          <p>{normal.length} pano normal durumda</p>
        </div>
        <div className="metric">
          <span>
            <Icon name="signal" /> Haberleşme
          </span>
          <strong>
            %{num((online / panels.length) * 100, 0)}
            <small>bağlı</small>
          </strong>
          <p>
            {online} / {panels.length} pano veri iletiyor
          </p>
        </div>
      </section>
      <div className="fleet-overview">
        <section className="panel overview-chart">
          <div className="panel-heading">
            <div>
              <h2>Öncelik görünümü</h2>
              <p>Risk ve müdahale zamanını birlikte değerlendirin.</p>
            </div>
            <div
              className="chart-range"
              role="group"
              aria-label="Filo görünümü"
            >
              <button
                aria-pressed={view === "risk"}
                onClick={() => setView("risk")}
              >
                Risk dağılımı
              </button>
              <button
                aria-pressed={view === "time"}
                onClick={() => setView("time")}
              >
                Zaman planı
              </button>
            </div>
          </div>
          {view === "risk" ? (
            <RiskMatrisi panels={worklist} />
          ) : (
            <SureEkseni worklist={worklist} />
          )}
        </section>
        <aside className="panel fleet-focus">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">ÖNCELİKLİ VARLIKLAR</span>
              <h2>İlk bakışta</h2>
            </div>
            <Icon name="pulse" />
          </div>
          <div className="focus-list">
            {worklist.slice(0, 3).map((p, i) => (
              <Link key={p.pano_id} to={`/pano/${p.pano_id}`}>
                <span className="focus-number">0{i + 1}</span>
                <div>
                  <strong>{p.name}</strong>
                  <p>{panelHeadline(p)}</p>
                  <span
                    className={`status-badge tone-${effectivePrio(p) ?? "normal"}`}
                  >
                    {effectivePrio(p) ? PRIO_NAME[effectivePrio(p)!] : "Normal"}
                  </span>
                </div>
                <Icon name="chevron" size={15} />
              </Link>
            ))}
            {!worklist.length && (
              <p className="calm">İnceleme gerektiren pano yok.</p>
            )}
          </div>
          <div className="focus-footer">
            <span>
              Alarm iletim süresi <small>p95</small>
            </span>
            <strong>
              {kpi?.p95_end_to_end_ms != null
                ? `${num(kpi.p95_end_to_end_ms, 0)} ms`
                : "Veri yok"}
            </strong>
          </div>
        </aside>
      </div>
      <section className="panel asset-register" id="yapilacaklar">
        <div className="panel-heading">
          <div>
            <h2>
              Pano envanteri{" "}
              <span className="count-badge">{panels.length}</span>
            </h2>
            <p>Durum, risk ve son telemetri tek çalışma listesinde.</p>
          </div>
        </div>
        <div className="asset-toolbar">
          <div className="table-tabs" role="group" aria-label="Pano filtresi">
            {[
              ["attention", "İncelenecek", worklist.length],
              ["all", "Tüm panolar", panels.length],
              ["normal", "Normal", normal.length],
            ].map(([key, label, count]) => (
              <button
                key={key}
                aria-pressed={filter === key}
                onClick={() => setFilter(String(key))}
              >
                {label}
                <span>{count}</span>
              </button>
            ))}
          </div>
          <div className="asset-tools">
            <label className="field-search">
              <Icon name="search" size={16} />
              <input
                aria-label="Envanterde pano ara"
                placeholder="Pano veya kimlik ara"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
            <select
              aria-label="Dağıtım şirketi"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
            >
              <option value="">Tüm şirketler</option>
              <option>ADM</option>
              <option>GDZ</option>
            </select>
            <select
              aria-label="Sıralama"
              value={sort}
              onChange={(e) => setSort(e.target.value)}
            >
              <option value="priority">Önceliğe göre</option>
              <option value="risk">Riske göre</option>
              <option value="name">İsme göre</option>
            </select>
            {visible.length > 0 && (
              <button
                type="button"
                className="btn-export"
                onClick={() => exportFleetCsv(visible)}
                title="Mevcut pano envanterini CSV olarak indir"
              >
                📥 CSV İndir
              </button>
            )}
          </div>
        </div>
        <div className="tbl-wrap">
          <table className="tbl asset-table">
            <thead>
              <tr>
                <th>Pano / konum</th>
                <th>Durum</th>
                <th>Risk skoru</th>
                <th>Tanı / gözlem</th>
                <th>Sınıra kalan</th>
                <th>Son veri</th>
                <th>
                  <span className="sr-only">Ayrıntılar</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {visible.map((p) => {
                const prio = effectivePrio(p);
                return (
                  <tr key={p.pano_id}>
                    <td>
                      <Link className="asset-name" to={`/pano/${p.pano_id}`}>
                        <span className="asset-icon">
                          <Icon name="cabinet" />
                        </span>
                        <span>
                          <strong>{p.name}</strong>
                          <small>{p.pano_id}</small>
                        </span>
                      </Link>
                    </td>
                    <td>
                      <span className={`status-badge tone-${prio ?? "normal"}`}>
                        {prio ? PRIO_NAME[prio] : "Normal"}
                      </span>
                    </td>
                    <td>
                      <span className="risk-cell">
                        <b>{p.risk_score}</b>
                        <span>
                          <i
                            style={{
                              width: `${Math.min(100, Math.max(0, p.risk_score))}%`,
                              background: prio
                                ? `var(--${prio.toLowerCase()})`
                                : "var(--dot)",
                            }}
                          />
                        </span>
                      </span>
                    </td>
                    <td className="diagnosis-cell">{hypText(p.risk_mode)}</td>
                    <td className="numeric">{ttlText(p.ttl_h) || "—"}</td>
                    <td>
                      <span
                        className={
                          p.comms_ok ? "freshness" : "freshness offline"
                        }
                      >
                        <i />
                        {p.comms_ok ? ago(p.last_seen) : "Bağlantı yok"}
                      </span>
                    </td>
                    <td>
                      <Link
                        className="icon-button"
                        to={`/pano/${p.pano_id}`}
                        aria-label={`${p.name} ayrıntıları`}
                      >
                        <Icon name="arrow" size={16} />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!visible.length && (
            <p className="console-empty">Bu filtrelerle eşleşen pano yok.</p>
          )}
        </div>
        <div className="table-footer">
          <span>{visible.length} pano gösteriliyor</span>
          <span>Risk puanları ve süre tahminleri son telemetriye dayanır.</span>
        </div>
      </section>
    </main>
  );
}
