import { useEffect, useMemo, useRef, useState } from "react";
import { VisualMapContinuousComponent } from "echarts/components";
import type { ECharts } from "echarts/core";
import type { SpatialSample } from "../lib/analysisData";
import { num } from "../lib/format";
import { thermalSurface } from "../lib/thermalSurface";

export default function SpatialAnalysis({
  points,
  midpoint,
}: {
  points: SpatialSample[];
  midpoint: number;
}) {
  const host = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ECharts>();
  const [state, setState] = useState<"loading" | "ready" | "failed">("loading");
  const [mode, setMode] = useState<"points" | "surface">("points");
  const model = useMemo(() => thermalSurface(points), [points]);
  useEffect(() => {
    let cancelled = false;
    let chart: ECharts | undefined;
    let observer: ResizeObserver | undefined;
    setState("loading");
    async function start() {
      try {
        const canvas = document.createElement("canvas");
        const gl = canvas.getContext("webgl2") ?? canvas.getContext("webgl");
        if (!gl) throw new Error("WebGL unavailable");
        gl.getExtension("WEBGL_lose_context")?.loseContext();
        const [echarts, renderer] = await Promise.all([
          import("echarts/core"),
          import("echarts/renderers"),
        ]);
        const [charts, components] = await Promise.all([
          import("echarts-gl/charts"),
          import("echarts-gl/components"),
        ]);
        if (cancelled || !host.current) return;
        echarts.use(renderer.CanvasRenderer);
        echarts.use(charts.Scatter3DChart);
        echarts.use(charts.SurfaceChart);
        echarts.use(components.Grid3DComponent);
        echarts.use(VisualMapContinuousComponent);
        chart = echarts.init(host.current, undefined, { renderer: "canvas" });
        chartRef.current = chart;
        const axis = {
          type: "value",
          nameTextStyle: { color: "#42546b", fontSize: 12 },
          axisLine: { lineStyle: { color: "#95a6b8" } },
          axisLabel: { color: "#556579", fontSize: 11 },
          splitLine: { lineStyle: { color: "#dbe3ed" } },
        };
        chart.setOption({
          animation: false,
          backgroundColor: "#ffffff",
          tooltip: {
            renderMode: "richText",
            formatter: (p: { data: SpatialSample }) =>
              mode === "surface"
                ? `Isıl model · ölçüm değildir\nAkım: ${num(p.data[0], 1)} A\nK/K₀: ${num(p.data[1], 2)}\nΔT: ${num(p.data[2], 2)} K`
                : `${new Date(p.data[3]).toLocaleString("tr-TR", { timeZone: "Europe/Istanbul" })}\nAkım: ${num(p.data[0], 1)} A\nΔT: ${num(p.data[1], 2)} K\nK/K₀: ${num(p.data[2], 2)}`,
          },
          xAxis3D: {
            ...axis,
            name: "Akım (A)",
            min:
              mode === "surface"
                ? Math.min(...points.map((p) => p[0]))
                : undefined,
          },
          yAxis3D: {
            ...axis,
            name: mode === "surface" ? "K/K₀" : "ΔT (K)",
            min:
              mode === "surface"
                ? Math.min(...points.map((p) => p[2]))
                : undefined,
          },
          zAxis3D: { ...axis, name: mode === "surface" ? "ΔT (K)" : "K/K₀" },
          visualMap:
            mode === "surface" && model
              ? {
                  min: 0,
                  max: model.max,
                  dimension: 2,
                  seriesIndex: 0,
                  show: false,
                  inRange: {
                    color: ["#fbdca5", "#ffac54", "#ed7427", "#b64421"],
                  },
                }
              : undefined,
          grid3D: {
            boxWidth: 130,
            boxDepth: 85,
            boxHeight: 75,
            top: -15,
            environment: "#ffffff",
            viewControl: {
              alpha: 24,
              beta: 36,
              distance: 190,
              autoRotate: false,
              projection: "perspective",
            },
            light: { main: { intensity: 1.2 }, ambient: { intensity: 0.6 } },
          },
          series:
            mode === "surface" && model
              ? [
                  {
                    type: "surface",
                    name: "Isıl model",
                    data: model.data,
                    shading: "lambert",
                    wireframe: {
                      show: true,
                      lineStyle: { color: "rgba(106,56,23,.35)", width: 0.7 },
                    },
                    itemStyle: { opacity: 0.95 },
                  },
                ]
              : [
                  points.filter((p) => p[3] < midpoint),
                  points.filter((p) => p[3] >= midpoint),
                ].map((data, i) => ({
                  type: "scatter3D",
                  name: i ? "Dönemin ikinci yarısı" : "Dönemin ilk yarısı",
                  dimensions: ["Akım (A)", "ΔT (K)", "K/K₀", "Zaman"],
                  data,
                  symbolSize: 6,
                  itemStyle: {
                    color: i ? "#8060b5" : "#178579",
                    opacity: 0.85,
                  },
                  emphasis: { itemStyle: { color: "#d66a26" } },
                })),
        });
        observer = new ResizeObserver(() => chart?.resize());
        observer.observe(host.current);
        setState("ready");
      } catch {
        if (!cancelled) setState("failed");
      }
    }
    void start();
    return () => {
      cancelled = true;
      observer?.disconnect();
      chart?.dispose();
      chartRef.current = undefined;
    };
  }, [points, midpoint, mode, model]);
  return (
    <div className="instrument-chart spatial-chart">
      <div className="surface-mode" role="group" aria-label="3D grafik türü">
        <button
          aria-pressed={mode === "points"}
          onClick={() => setMode("points")}
        >
          Ölçüm noktaları
        </button>
        <button
          aria-pressed={mode === "surface"}
          disabled={!model}
          onClick={() => setMode("surface")}
        >
          Isıl yüzey · model
        </button>
      </div>
      {mode === "surface" && (
        <p className="surface-explanation">
          Ölçümlerden hesaplanan K₀ ile ΔT = K₀ × (K/K₀) × I² yüzeyi. Görülen
          akım ve oran aralıkları içindeki model değerleridir; her kesişim
          ölçülmüş değildir. Arıza tahmini değildir.
        </p>
      )}
      <div className="instrument-tools">
        <span className="instrument-caption">
          {mode === "surface" ? "ISIL MODEL YÜZEYİ" : "3D ÖLÇÜM UZAYI"} · {points.length} {mode === "surface" ? "REFERANS ÖLÇÜM" : "EŞLEŞEN ÖLÇÜM"}
        </span>
        <div>
          <button
            type="button"
            onClick={() =>
              chartRef.current?.setOption({
                grid3D: { viewControl: { alpha: 0, beta: 0, distance: 190 } },
              })
            }
          >
            Önden
          </button>
          <button
            type="button"
            onClick={() =>
              chartRef.current?.setOption({
                grid3D: { viewControl: { alpha: 24, beta: 36, distance: 190 } },
              })
            }
          >
            Görünümü sıfırla
          </button>
        </div>
      </div>
      {state === "loading" && <p role="status">3D analiz hazırlanıyor…</p>}
      {state === "failed" && (
        <p role="alert">
          3D görünüm bu cihazda açılamadı. Aynı ölçümleri aşağıdaki tablodan
          veya 2D analizden inceleyebilirsiniz.
        </p>
      )}
      <div
        ref={host}
        className="spatial-host"
        style={{ display: state === "failed" ? "none" : "block" }}
        role="img"
        aria-label={mode === "surface" ? "Akım ve bağlantı direncine göre modellenen sıcaklık artışı yüzeyi" : "Akım, sıcaklık artışı ve bağlantı sağlığı için döndürülebilir üç boyutlu dağılım"}
      />
      <div className="spatial-hint">
        <span>Sürükle: döndür</span>
        <span>Tekerlek: yakınlaştır</span>
        <span>
          {mode === "surface"
            ? "Yüzey üzerine gel: model değeri"
            : "Nokta üzerine gel: ölçüm"}
        </span>
      </div>
      <div className="spatial-periods" hidden={mode === "surface"}>
        <span>
          <i style={{ background: "#178579" }} />
          Dönemin ilk yarısı
        </span>
        <span>
          <i style={{ background: "#8060b5" }} />
          Dönemin ikinci yarısı
        </span>
      </div>
      <details className="instrument-data">
        <summary>3D ölçüm tablosu · klavyeyle incele</summary>
        <div className="instrument-table-scroll">
          <table>
            <thead>
              <tr>
                <th>Zaman (TR)</th>
                <th>Akım (A)</th>
                <th>ΔT (K)</th>
                <th>K/K₀</th>
              </tr>
            </thead>
            <tbody>
              {points.map((p, i) => (
                <tr key={i}>
                  <td>
                    {new Date(p[3]).toLocaleString("tr-TR", {
                      timeZone: "Europe/Istanbul",
                    })}
                  </td>
                  <td>{num(p[0], 2)}</td>
                  <td>{num(p[1], 2)}</td>
                  <td>{num(p[2], 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
