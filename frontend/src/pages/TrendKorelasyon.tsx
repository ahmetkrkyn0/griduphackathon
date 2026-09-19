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
  const [windowDays, setWindowDays] = useState(14);

  useEffect(() => {
    if (!panoId) return;
    setDetail(null);
    setPoint("");
    setSeries(null);
    setError(null);
    const controller = new AbortController();
    api
      .panel(panoId, controller.signal)
      .then((d) => {
        if (controller.signal.aborted) return;
        setDetail(d);
        setPoint(
          d.active_alarms?.find((a) => a.reason?.point)?.reason?.point ??
            d.points[0]?.pt ??
            "",
        );
      })
      .catch((e) => !controller.signal.aborted && setError(errorText(e)));
    return () => controller.abort();
  }, [panoId]);

  useEffect(() => {
    if (!panoId || !point) return;
    setSeries(null);
    setError(null);
    const controller = new AbortController();
    const to = new Date();
    const from = new Date(to.getTime() - windowDays * 86_400_000);
    const idx = phaseIndexOf(point);
    const tags = [`t_conn.${point}.k_ratio`, `t_conn.${point}.dt_c`];
    if (idx != null) tags.push(`elec.i_ph.${idx}`);
    api
      .series(panoId, tags, from, to, "1h", controller.signal)
      .then(setSeries)
      .catch((e) => !controller.signal.aborted && setError(errorText(e)));
    return () => controller.abort();
  }, [panoId, point, windowDays]);

  useEffect(() => {
    if (!panoId) return;
    setEnvSeries(null);
    const controller = new AbortController();
    const to = new Date();
    const from = new Date(to.getTime() - windowDays * 86_400_000);
    api
      .series(panoId, ["env.td_margin_k"], from, to, "1h", controller.signal)
      .then(setEnvSeries)
      .catch((e) => !controller.signal.aborted && setError(errorText(e)));
    return () => controller.abort();
  }, [panoId, windowDays]);

  const scatter = useMemo(() => {
    if (!series || !point) return null;
    const idx = phaseIndexOf(point);
    if (idx == null) return null;
    const dt = series[`t_conn.${point}.dt_c`];
    const i = series[`elec.i_ph.${idx}`];
    if (!dt || !i) return null;
    const mid = Math.floor(dt.length / 2);
    const currents = new Map(i);
    const pairs = (from: number, to: number) => {
      const out: Array<[number, number]> = [];
      for (let k = from; k < to; k++) {
        const iv = currents.get(dt[k][0]);
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
        <p>
          Yük-normalize ısınma: sağlıklı bağlantıda tek eğim, gevşeyen
          bağlantıda daha dik bir eğim oluşur.
        </p>
      </div>

      <div className="console-filters">
        <div className="analysis-field">
          <label className="dim small" htmlFor="pano-select">
            Pano
          </label>
          <select
            id="pano-select"
            value={panoId}
            onChange={(e) => navigate(`/trend/${e.target.value}`)}
          >
            {panels.map((p) => (
              <option key={p.pano_id} value={p.pano_id}>
                {p.name} ({p.pano_id})
              </option>
            ))}
          </select>
        </div>
        {detail && (
          <div className="analysis-field">
            <label className="dim small" htmlFor="point-select">
              Nokta
            </label>
            <select
              id="point-select"
              value={point}
              onChange={(e) => setPoint(e.target.value)}
            >
              {detail.points.map((p: ConnPoint) => (
                <option key={p.pt} value={p.pt}>
                  {p.label ?? pointLabel(p.pt)}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="chart-range" role="group" aria-label="Analiz dönemi">
          {[7, 14].map((days) => (
            <button
              key={days}
              aria-pressed={windowDays === days}
              onClick={() => setWindowDays(days)}
            >
              Son {days} gün
            </button>
          ))}
        </div>
      </div>

      {error && <p className="dim">{error}</p>}

      <div className="analytics-context">
        <span>
          <strong>{detail?.name ?? panoId}</strong>
        </span>
        <span>Saatlik ölçümler · Son {windowDays} gün</span>
        {detail && (
          <span>
            Güncel risk: <strong>{num(detail.risk_score ?? 0, 0)} / 100</strong>
          </span>
        )}
      </div>
      <div className="analysis-grid">
        <section className="phases">
          <h3>Yük ve ısınma ilişkisi</h3>
          {phaseIndexOf(point) == null ? (
            <p className="dim small">
              Bu nokta tek bir faza bağlı değil (ör. nötr); dağılım grafiği faz
              akımı gerektirir.
            </p>
          ) : scatter ? (
            <>
              <p className="dim small">
                Son {windowDays} günün ilk ve ikinci yarısı karşılaştırılır.
                Kesikli çizgiler doğrusal eğilimi gösterir.
              </p>
              <SacilimGrafik
                xLabel="Faz akımı² (A²)"
                yLabel="Ortam üstü artış (K)"
                series={[
                  {
                    key: "early",
                    label: "Dönemin ilk yarısı",
                    color: "#456da8",
                    points: scatter.early,
                  },
                  {
                    key: "late",
                    label: "Dönemin ikinci yarısı",
                    color: "#D9530F",
                    points: scatter.late,
                  },
                ]}
              />
            </>
          ) : (
            <p className="dim small">Yükleniyor…</p>
          )}
        </section>

        <section className="phases">
          <h3>Bağlantı sağlığı · K/K₀</h3>
          <p className="dim small">
            Başlangıç ısıl direncine göre değişim. Yükselen değerler inceleme
            gerektirir.
          </p>
          {series ? (
            <CizgiGrafik
              series={[
                {
                  key: "k",
                  label: "K/K₀",
                  color: "#003DA5",
                  points: series[`t_conn.${point}.k_ratio`] ?? [],
                },
              ]}
              yLabelLeft="K/K₀"
              thresholdLeft={{ value: 1, label: "Başlangıç · 1,0" }}
            />
          ) : (
            <p className="dim small">Yükleniyor…</p>
          )}
        </section>

        <section className="phases">
          <h3>Ortam üstü sıcaklık · ΔT</h3>
          <p className="dim small">
            Bağlantı ile pano içi ortam arasındaki sıcaklık farkı.
          </p>
          {series ? (
            <CizgiGrafik
              series={[
                {
                  key: "dt",
                  label: "ΔT (K)",
                  color: "#D9530F",
                  points: series[`t_conn.${point}.dt_c`] ?? [],
                },
              ]}
              yLabelLeft="ΔT (K)"
            />
          ) : (
            <p className="dim small">Yükleniyor…</p>
          )}
        </section>
        <section className="phases">
          <h3>Yoğuşma payı · Çiy noktası marjı</h3>
          <p className="dim small">
            Sıfıra yaklaşan marj, yoğuşma koşullarına yaklaşıldığını gösterir.
          </p>
          {envSeries ? (
            <CizgiGrafik
              series={[
                {
                  key: "td",
                  label: "Çiy noktası marjı (K)",
                  color: "#1F8A70",
                  points: envSeries["env.td_margin_k"] ?? [],
                },
              ]}
              yLabelLeft="K"
            />
          ) : (
            <p className="dim small">Yükleniyor…</p>
          )}
        </section>
      </div>
    </main>
  );
}
