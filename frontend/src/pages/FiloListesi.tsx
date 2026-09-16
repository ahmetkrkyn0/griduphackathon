import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { PanelSummary } from "../api/types";
import { PrioMark } from "../components/PrioMark";
import { RiskMatrisi } from "../components/RiskMatrisi";
import { SureEkseni } from "../components/SureEkseni";
import { ago, ttlText } from "../lib/format";
import { hypText } from "../lib/labels";
import { useNow } from "../lib/useNow";
import { effectivePrio, fleetHeadline, needsAttention, panelHeadline, sortWorklist } from "../lib/worklist";
import { useFleet } from "../state/fleet";

type HeroView = "eksen" | "risk";

// SureEkseni (zaman ekseni) dar ekranda gizlenir (bkz. app.css @media 960px, sabit piksel
// duzeni dar ekrana uymuyor). Risk matrisi SVG'si olcekli oldugu icin mobilde de calisiyor;
// mobil kullanici ilk acilista bos alanla karsilasmasin diye varsayilan gorunum ona gore secilir.
const initialHeroView = (): HeroView =>
  typeof window !== "undefined" && window.matchMedia("(max-width: 960px)").matches ? "risk" : "eksen";

export function FiloListesi() {
  const { panels, loaded, error } = useFleet();
  const [heroView, setHeroView] = useState<HeroView>(initialHeroView);
  const [search, setSearch] = useState("");
  useNow(5000);

  const worklist = useMemo(() => sortWorklist(panels), [panels]);
  const normal = useMemo(
    () => panels.filter((p) => !needsAttention(p)).sort((a, b) => a.name.localeCompare(b.name, "tr")),
    [panels],
  );

  const query = search.trim().toLowerCase();
  const filteredWorklist = useMemo(() => {
    if (!query) return worklist;
    return worklist.filter((p) => p.name.toLowerCase().includes(query) || p.pano_id.toLowerCase().includes(query));
  }, [worklist, query]);

  const filteredNormal = useMemo(() => {
    if (!query) return normal;
    return normal.filter((p) => p.name.toLowerCase().includes(query) || p.pano_id.toLowerCase().includes(query));
  }, [normal, query]);

  if (!loaded) {
    return (
      <main className="page">
        <p className="empty">Filo yükleniyor…</p>
      </main>
    );
  }
  if (error && panels.length === 0) {
    return (
      <main className="page">
        <div className="empty">
          <h1>Filo verisi alınamadı</h1>
          <p>
            {error}. Backend'i <code>docker compose up</code> ile başlatın; backend olmadan denemek için{" "}
            <code>npm run dev:mock</code> kullanın.
          </p>
        </div>
      </main>
    );
  }
  if (panels.length === 0) {
    return (
      <main className="page">
        <div className="empty">
          <h1>Henüz pano yok</h1>
          <p>Devreye alınan ilk pano veri gönderdiğinde burada görünecek.</p>
        </div>
      </main>
    );
  }

  const noResults = query && filteredWorklist.length === 0 && filteredNormal.length === 0;

  return (
    <main className="page">
      <section className="hero" aria-labelledby="filo-baslik">
        <h1 id="filo-baslik">{fleetHeadline(worklist)}</h1>
        <p>Panolar sorunun ne zaman kritik hale geleceğine göre dizilir. {normal.length} pano normal çalışıyor.</p>
        
        <div className="filo-toolbar">
          <div className="search-wrap">
            <span className="search-icon" aria-hidden="true">🔍</span>
            <input
              type="search"
              className="search-input"
              placeholder="Pano adı veya kimliği ile ara (ör. TR-04, Bornova)…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Panolarda ara"
            />
            {search && (
              <button type="button" className="search-clear" onClick={() => setSearch("")} aria-label="Aramayı temizle">
                ✕
              </button>
            )}
          </div>
          {worklist.length > 0 && !query && (
            <div className="chart-range" role="group" aria-label="Filo görünümü">
              <button type="button" aria-pressed={heroView === "eksen"} onClick={() => setHeroView("eksen")}>
                Zaman ekseni
              </button>
              <button type="button" aria-pressed={heroView === "risk"} onClick={() => setHeroView("risk")}>
                Risk matrisi
              </button>
            </div>
          )}
        </div>

        {worklist.length > 0 && !query && (
          heroView === "eksen" ? <SureEkseni worklist={worklist} /> : <RiskMatrisi panels={worklist} />
        )}
      </section>

      {noResults && (
        <div className="empty search-empty" role="status">
          <p>"{search}" ile eşleşen pano bulunamadı.</p>
        </div>
      )}

      {filteredWorklist.length > 0 && (
        <section id="yapilacaklar" aria-labelledby="yapilacaklar-baslik">
          <h2 id="yapilacaklar-baslik" className="section-title">
            {query ? `Eşleşen sorunlu panolar (${filteredWorklist.length})` : "Şimdi yapılacaklar"}
          </h2>
          <ul className="work">
            {filteredWorklist.map((panel) => (
              <li key={panel.pano_id}>
                <WorkRow panel={panel} />
              </li>
            ))}
          </ul>
        </section>
      )}

      {filteredNormal.length > 0 && (
        <details className="normal" open={!!query}>
          <summary>
            {filteredNormal.length} pano normal çalışıyor
            {query ? " (filtrelendi)" : ""}
          </summary>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Pano</th>
                  <th>Kimlik</th>
                  <th className="r">Risk</th>
                  <th className="r">Taban öğrenme</th>
                  <th className="r">Son veri</th>
                </tr>
              </thead>
              <tbody>
                {filteredNormal.map((p) => (
                  <tr key={p.pano_id}>
                    <td>
                      <Link to={`/pano/${p.pano_id}`}>{p.name}</Link>
                    </td>
                    <td className="dim">{p.pano_id}</td>
                    <td className="r">{p.risk_score}</td>
                    <td className="r">{p.baseline_day != null ? `${p.baseline_day}. gün` : "–"}</td>
                    <td className="r">{ago(p.last_seen)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </main>
  );
}

function WorkRow({ panel }: { panel: PanelSummary }) {
  const prio = effectivePrio(panel);
  const ttl = ttlText(panel.ttl_h);
  return (
    <Link to={`/pano/${panel.pano_id}`} className="work-row">
      {prio && <PrioMark prio={prio} />}
      <span className="work-name-cell">
        <span className="work-name">{panel.name}</span>
        <span className="work-id">{panel.pano_id}</span>
      </span>
      <span className="work-body">
        <span className="work-head">{panelHeadline(panel)}</span>
        <span className="work-meta">
          {hypText(panel.risk_mode)}, risk {panel.risk_score}, son veri {ago(panel.last_seen)}
        </span>
      </span>
      <span className="work-ttl">
        {ttl && (
          <>
            {ttl}
            <small>sınıra</small>
          </>
        )}
      </span>
    </Link>
  );
}
