import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { errorText } from "../api/errors";
import type { ConnPoint, PanelDetail, SeriesResponse } from "../api/types";
import { CizgiGrafik } from "../components/CizgiGrafik";
import { SacilimGrafik } from "../components/SacilimGrafik";
import { num } from "../lib/format";
import { pointLabel } from "../lib/labels";
import { useFleet } from "../state/fleet";

const WINDOW_DAYS = 14; // rapor S1 senaryosuyla ayni pencere (14 gunluk gevsek baglanti rampasi)
const PHASE_INDEX: Record<string, number> = { L1: 0, L2: 1, L3: 2 };

function phaseIndexOf(pt: string): number | null {
  const m = /_(L[123])$/.exec(pt);
  return m ? PHASE_INDEX[m[1]] : null;
}

/**
 * TC3: I²–ΔT dağılımı (sağlıklı vs gevşeyen bağlantı farklı eğim, rapor §6.5 L1-1),
 * K/K₀ trendi ve çiy noktası marjı zaman serisi.
 */
export function TrendKorelasyon() {
  const { panoId: routePanoId } = useParams();
  const navigate = useNavigate();
  const { panels } = useFleet();
  const panoId = routePanoId ?? panels[0]?.pano_id ?? "";

  const [detail, setDetail] = useState<PanelDetail | null>(null);
  const [point, setPoint] = useState<string>("");
  const [series, setSeries] = useState<SeriesResponse | null>(null);
  const [envSeries, setEnvSeries] = useState<SeriesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!panoId) return;
    setDetail(null);
    api
      .panel(panoId)
      .then((d) => {
        setDetail(d);
        setPoint(d.points[0]?.pt ?? "");
      })
      .catch((e) => setError(errorText(e)));
  }, [panoId]);

  useEffect(() => {
    if (!panoId || !point) return;
    setSeries(null);
    const controller = new AbortController();
    const to = new Date();
    const from = new Date(to.getTime() - WINDOW_DAYS * 86_400_000);
    const idx = phaseIndexOf(point);
    const tags = [`t_conn.${point}.k_ratio`, `t_conn.${point}.dt_c`];
    if (idx != null) tags.push(`elec.i_ph.${idx}`);
    api
      .series(panoId, tags, from, to, "1h", controller.signal)
      .then(setSeries)
      .catch((e) => !controller.signal.aborted && setError(errorText(e)));
    return () => controller.abort();
  }, [panoId, point]);

  useEffect(() => {
    if (!panoId) return;
    const controller = new AbortController();
    const to = new Date();
    const from = new Date(to.getTime() - WINDOW_DAYS * 86_400_000);
    api
      .series(panoId, ["env.td_margin_k"], from, to, "1h", controller.signal)
      .then(setEnvSeries)
      .catch(() => {});
    return () => controller.abort();
  }, [panoId]);

  const scatter = useMemo(() => {
    if (!series || !point) return null;
    const idx = phaseIndexOf(point);
    if (idx == null) return null;
    const dt = series[`t_conn.${point}.dt_c`];
    const i = series[`elec.i_ph.${idx}`];
    if (!dt || !i) return null;
    const mid = Math.floor(dt.length / 2);
    const pairs = (from: number, to: number) => {
      const out: Array<[number, number]> = [];
      for (let k = from; k < to; k++) {
        const iv = i[k]?.[1];
        const dv = dt[k]?.[1];
        if (iv != null && dv != null) out.push([iv * iv, dv]);
      }
      return out;
    };
    return {
      early: pairs(0, mid),
      late: pairs(mid, dt.length),
    };
  }, [series, point]);

  if (!panoId) {
    return (
      <main className="page">
        <p className="empty">Henüz pano yok.</p>
      </main>
    );
  }

  return (
    <main className="page">
      <div className="hero">
        <h1>Trend ve korelasyon</h1>
        <p>Yük-normalize ısınma: sağlıklı bağlantıda tek eğim, gevşeyen bağlantıda daha dik bir eğim oluşur.</p>
      </div>

      <div className="console-filters">
        <label className="dim small" htmlFor="pano-select">
          Pano
        </label>
        <select id="pano-select" value={panoId} onChange={(e) => navigate(`/trend/${e.target.value}`)}>
          {panels.map((p) => (
            <option key={p.pano_id} value={p.pano_id}>
              {p.name} ({p.pano_id})
            </option>
          ))}
        </select>
        {detail && (
          <>
            <label className="dim small" htmlFor="point-select">
              Nokta
            </label>
            <select id="point-select" value={point} onChange={(e) => setPoint(e.target.value)}>
              {detail.points.map((p: ConnPoint) => (
                <option key={p.pt} value={p.pt}>
                  {p.label ?? pointLabel(p.pt)}
                </option>
              ))}
            </select>
          </>
        )}
      </div>

      {error && <p className="dim">{error}</p>}

      <section className="phases">
        <h3>I² – ΔT dağılımı</h3>
        {phaseIndexOf(point) == null ? (
          <p className="dim small">Bu nokta tek bir faza bağlı değil (ör. nötr); dağılım grafiği faz akımı gerektirir.</p>
        ) : scatter ? (
          <>
            <p className="dim small">
              Son {WINDOW_DAYS} günün ilk ve ikinci yarısı karşılaştırılır: eğim dikleşiyorsa ısıl direnç (K) artıyor demektir.
            </p>
            <SacilimGrafik
              xLabel="Faz akımı² (A²)"
              yLabel="Ortam üstü artış (K)"
              series={[
                { key: "early", label: `İlk ${WINDOW_DAYS / 2} gün`, color: "#9AA3AA", points: scatter.early },
                { key: "late", label: `Son ${WINDOW_DAYS / 2} gün`, color: "#DD6418", points: scatter.late },
              ]}
            />
          </>
        ) : (
          <p className="dim small">Yükleniyor…</p>
        )}
      </section>

      <section className="phases">
        <h3>Isıl direnç indeksi (K/K₀) trendi</h3>
        {series ? (
          <CizgiGrafik
            series={[
              { key: "k", label: "K/K₀", color: "#003DA5", points: series[`t_conn.${point}.k_ratio`] ?? [] },
              { key: "dt", label: "ΔT (K)", color: "#D9530F", points: series[`t_conn.${point}.dt_c`] ?? [], axis: "right" },
            ]}
            yLabelLeft="K/K₀"
            yLabelRight="ΔT (K)"
          />
        ) : (
          <p className="dim small">Yükleniyor…</p>
        )}
      </section>

      <section className="phases">
        <h3>Çiy noktası marjı</h3>
        {envSeries ? (
          <CizgiGrafik series={[{ key: "td", label: "Çiy noktası marjı (K)", color: "#1F8A70", points: envSeries["env.td_margin_k"] ?? [] }]} yLabelLeft="K" />
        ) : (
          <p className="dim small">Yükleniyor…</p>
        )}
      </section>

      {detail && (
        <div className="facts">
          <div className="fact">
            <div className="k">Risk skoru</div>
            <div className="v">{num(detail.risk_score ?? 0, 0)}</div>
          </div>
        </div>
      )}
    </main>
  );
}
