import { Link } from "react-router-dom";
import type { PanelSummary, Prio } from "../api/types";
import { PRIO_NAME } from "../lib/labels";
import { effectivePrio } from "../lib/worklist";
import { useFleet } from "../state/fleet";

// Sozlesmede il/ilce alani yok (yalnizca opsiyonel lat/lon, cogu zaman bos). Coografi olarak
// dogru olmayan bir seyi "harita" diye sunmamak icin (durustluk kurali) gercekten elde olan
// tek yapisal ayrim kullanilir: pano_id onekindeki dagitim sirketi (ADM/GDZ). Il/ilce kirilimi
// icin bkz. contracts/changes/2026-09-14-fleet-health-bulk.md'deki not.
const COMPANY: Record<string, string> = { ADM: "ADM Elektrik", GDZ: "GDZ Elektrik" };
const PRIO_COLOR: Record<Prio, string> = { P1: "var(--p1)", P2: "var(--p2)", P3: "var(--p3)", SYS: "var(--sys)", INFO: "var(--dim)" };

function companyOf(panoId: string): string {
  return COMPANY[panoId.slice(0, 3)] ?? panoId.slice(0, 3);
}

/** TC3: bölge haritası — çevrimdışı, dağıtım şirketi bazında özet (gerçek harita karosu yok, GK4). */
export function BolgeHaritasi() {
  const { panels } = useFleet();

  const groups = new Map<string, PanelSummary[]>();
  for (const p of panels) {
    const key = companyOf(p.pano_id);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(p);
  }

  return (
    <main className="page">
      <div className="hero">
        <h1>Bölge haritası</h1>
        <p>
          Dağıtım şirketine göre özet görünüm. İl/ilçe bazlı kırılım için sözleşmeye konum alanı eklenmesi gerekiyor
          (öneri: <code>contracts/changes/2026-09-14-fleet-health-bulk.md</code>); gerçek harita karosu kullanılmaz
          (yığın internetten bağımsız çalışır).
        </p>
      </div>

      <div className="region-legend">
        {(["P1", "P2", "P3", "SYS"] as Prio[]).map((p) => (
          <span key={p}>
            <span className="region-dot" style={{ background: PRIO_COLOR[p], width: 12, height: 12, display: "inline-block", borderRadius: 3, marginRight: 4 }} />
            {PRIO_NAME[p]}
          </span>
        ))}
        <span>
          <span className="region-dot normal" style={{ width: 12, height: 12, display: "inline-block", borderRadius: 3, marginRight: 4 }} />
          Normal
        </span>
      </div>

      <div className="region-map">
        {[...groups.entries()].map(([company, list]) => {
          const attention = list.filter((p) => effectivePrio(p) !== null).length;
          return (
            <div key={company} className="region-col">
              <h3>
                <span>{company}</span>
                <span className="dim small">
                  {list.length} pano{attention ? `, ${attention} ilgi bekliyor` : ""}
                </span>
              </h3>
              <div className="region-dots">
                {list
                  .sort((a, b) => b.risk_score - a.risk_score)
                  .map((p) => {
                    const prio = effectivePrio(p);
                    return (
                      <Link
                        key={p.pano_id}
                        to={`/pano/${p.pano_id}`}
                        className={prio ? "region-dot" : "region-dot normal"}
                        style={prio ? { background: PRIO_COLOR[prio] } : undefined}
                        title={`${p.name} (${p.pano_id}), risk ${p.risk_score}`}
                      >
                        {p.risk_score}
                      </Link>
                    );
                  })}
              </div>
            </div>
          );
        })}
      </div>
    </main>
  );
}
