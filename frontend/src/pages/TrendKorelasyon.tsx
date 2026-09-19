import { lazy, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { errorText } from "../api/errors";
import type { ConnPoint, PanelDetail, SeriesResponse } from "../api/types";
import { CizgiGrafik } from "../components/CizgiGrafik";
import { SacilimGrafik } from "../components/SacilimGrafik";
import { num } from "../lib/format";
import { pointLabel } from "../lib/labels";
import { useFleet } from "../state/fleet";
import { joinSpatial } from "../lib/analysisData";
import { ChartBoundary } from "../components/ChartBoundary";

const SpatialAnalysis = lazy(() => import("../components/SpatialAnalysis"));

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
  const [spatial, setSpatial] = useState(false);

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
      .then((data) => {
        if (!controller.signal.aborted) setSeries(data);
      })
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
      .then((data) => {
        if (!controller.signal.aborted) setEnvSeries(data);
      })
      .catch((e) => !controller.signal.aborted && setError(errorText(e)));
    return () => controller.abort();
  }, [panoId, windowDays]);

  const periodMidpoint = useMemo(() => {
    const times = (series?.[`t_conn.${point}.dt_c`] ?? [])
      .map((p) => p[0])
      .filter(Number.isFinite);
    return times.length ? (Math.min(...times) + Math.max(...times)) / 2 : 0;
  }, [series, point]);

  const scatter = useMemo(() => {
    if (!series || !point) return null;
    const idx = phaseIndexOf(point);
    if (idx == null) return null;
    const dt = series[`t_conn.${point}.dt_c`];
    const i = series[`elec.i_ph.${idx}`];
    if (!dt || !i) return null;
    const currents = new Map(i);
    const pairs = (late: boolean) => {
      const out: Array<[number, number]> = [];
      for (const [t, dv] of dt) {
        const iv = currents.get(t);
        if (
          Number.isFinite(t) &&
          t >= periodMidpoint === late &&
          iv != null &&
          Number.isFinite(iv) &&
          dv != null &&
          Number.isFinite(dv)
        )
          out.push([iv * iv, dv]);
      }
      return out;
    };
    return {
      early: pairs(false),
      late: pairs(true),
    };
  }, [series, point, periodMidpoint]);

  const spatialPoints = useMemo(() => {
    const idx = phaseIndexOf(point);
    if (!series || idx == null) return [];
    return joinSpatial(
      series[`elec.i_ph.${idx}`] ?? [],
      series[`t_conn.${point}.dt_c`] ?? [],
      series[`t_conn.${point}.k_ratio`] ?? [],
    );
  }, [series, point]);
  const latest = spatialPoints.at(-1);

  if (!panoId) {
    return (
      <main className="page">
        <p className="empty">Henüz pano yok.</p>
      </main>
    );
  }

  return (
    <main className="page analytics-page">
      <div className="hero">
        <span className="section-kicker">VARLIK PERFORMANSI / ANALİTİK</span>
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
      <div className="analysis-readouts">
        <div>
          <span>Eşzamanlı örnek</span>
          <strong>
            {series ? spatialPoints.length : "—"}
            <small>ölçüm</small>
          </strong>
          <p>Akım · ΔT · K/K₀ eşleşmesi</p>
        </div>
        <div>
          <span>Son eşleşen akım</span>
          <strong>
            {latest ? num(latest[0], 1) : "—"}
            <small>A</small>
          </strong>
          <p>Seçili bağlantının fazı</p>
        </div>
        <div>
          <span>Son eşleşen ısınma</span>
          <strong>
            {latest ? num(latest[1], 1) : "—"}
            <small>K</small>
          </strong>
          <p>Ortam üzerindeki sıcaklık farkı</p>
        </div>
        <div>
          <span>Son eşleşen K/K₀</span>
          <strong>
            {latest ? num(latest[2], 2) : "—"}
            <small>oran</small>
          </strong>
          <p>Başlangıç ısıl direncine göre</p>
        </div>
      </div>
      <div className="analysis-mode-bar">
        <div>
          <span className="section-kicker">ÖLÇÜMDEN İÇGÖRÜYE</span>
          <h2>Bağlantının davranışını keşfet</h2>
        </div>
        <div className="chart-range" role="group" aria-label="Analiz görünümü">
          <button aria-pressed={!spatial} onClick={() => setSpatial(false)}>
            2D analiz
          </button>
          <button aria-pressed={spatial} onClick={() => setSpatial(true)}>
            3D ölçüm uzayı
          </button>
        </div>
      </div>
      {spatial && (
        <section className="spatial-section">
          <h3>Yük, ısınma ve bağlantı sağlığı</h3>
          <p>
            Ölçüm noktaları aynı andaki üç geçerli ölçümü gösterir. Isıl yüzey
            sekmesi, yük ve bağlantı direncinin ısınmaya etkisini model olarak gösterir.
          </p>
          {spatialPoints.length ? (
            <ChartBoundary>
              <SpatialAnalysis
                points={spatialPoints}
                midpoint={periodMidpoint}
              />
            </ChartBoundary>
          ) : (
            <p className="chart-empty">
              {series
                ? "Bu seçimde üç eksen için eşleşen ölçüm yok. Faz bağlantısı seçin veya dönemi değiştirin."
                : "Ölçümler yükleniyor…"}
            </p>
          )}
        </section>
      )}
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
