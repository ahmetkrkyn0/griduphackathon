import { useMemo } from "react";
import { Link } from "react-router-dom";
import type { PanelSummary } from "../api/types";
import { PrioMark } from "../components/PrioMark";
import { SureEkseni } from "../components/SureEkseni";
import { ago, ttlText } from "../lib/format";
import { hypText } from "../lib/labels";
import { useNow } from "../lib/useNow";
import { effectivePrio, fleetHeadline, needsAttention, panelHeadline, sortWorklist } from "../lib/worklist";
import { useFleet } from "../state/fleet";

export function FiloListesi() {
  const { panels, loaded, error } = useFleet();
  useNow(5000);

  const worklist = useMemo(() => sortWorklist(panels), [panels]);
  const normal = useMemo(
    () => panels.filter((p) => !needsAttention(p)).sort((a, b) => a.name.localeCompare(b.name, "tr")),
    [panels],
  );

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

  return (
    <main className="page">
      <section className="hero" aria-labelledby="filo-baslik">
        <h1 id="filo-baslik">{fleetHeadline(worklist)}</h1>
        <p>Panolar sorunun ne zaman kritik hale geleceğine göre dizilir. {normal.length} pano normal çalışıyor.</p>
        {worklist.length > 0 && <SureEkseni worklist={worklist} />}
      </section>

      {worklist.length > 0 && (
        <section id="yapilacaklar" aria-labelledby="yapilacaklar-baslik">
          <h2 id="yapilacaklar-baslik" className="section-title">
            Şimdi yapılacaklar
          </h2>
          <ul className="work">
            {worklist.map((panel) => (
              <li key={panel.pano_id}>
                <WorkRow panel={panel} />
              </li>
            ))}
          </ul>
        </section>
      )}

      {normal.length > 0 && (
        <details className="normal">
          <summary>{normal.length} pano normal çalışıyor</summary>
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
                {normal.map((p) => (
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
