import { useState } from "react";
import { ChartSurface, axisStyle, chartColors } from "./ChartSurface";
import { linearFit } from "../lib/analysisData";
import { num } from "../lib/format";
export interface ScatterSeries {
  key: string;
  label: string;
  color: string;
  points: Array<[number, number]>;
}
export interface Props {
  series: ScatterSeries[];
  xLabel: string;
  yLabel: string;
  height?: number;
  emptyText?: string;
}
export function SacilimGrafik({
  series,
  xLabel,
  yLabel,
  height = 300,
  emptyText,
}: Props) {
  const [hidden, setHidden] = useState<string[]>([]);
  const data = series.map((s) => ({
    ...s,
    points: s.points.filter((p) => p.every(Number.isFinite)),
    fit: linearFit(s.points),
  }));
  if (!data.some((s) => s.points.length))
    return (
      <p className="chart-empty">
        {emptyText ?? "Bu aralıkta geçerli ölçüm yok."}
      </p>
    );
  return (
    <ChartSurface
      height={height}
      label={`${xLabel} / ${yLabel} dağılım grafiği`}
      option={{
        grid: { left: 65, right: 25, top: 38, bottom: 70 },
        tooltip: {
          trigger: "item",
          renderMode: "richText",
          backgroundColor: "#ffffff",
          textStyle: { color: "#243449" },
        },
        xAxis: {
          ...axisStyle,
          type: "value",
          name: xLabel,
          nameLocation: "middle",
          nameGap: 32,
        },
        yAxis: { ...axisStyle, type: "value", name: yLabel },
        dataZoom: [
          { type: "inside", zoomOnMouseWheel: "ctrl", filterMode: "none" },
        ],
        series: data.flatMap((s, i) => {
          const xs = s.points.map((p) => p[0]);
          const lo = Math.min(...xs),
            hi = Math.max(...xs);
          return [
            {
              type: "scatter",
              name: s.label,
              data: hidden.includes(s.key) ? [] : s.points,
              symbolSize: 6,
              itemStyle: { color: chartColors[i], opacity: 0.65 },
            },
            {
              type: "line",
              name: `${s.label} · eğilim`,
              data:
                s.fit && !hidden.includes(s.key)
                  ? [
                      [lo, s.fit.m * lo + s.fit.b],
                      [hi, s.fit.m * hi + s.fit.b],
                    ]
                  : [],
              symbol: "none",
              lineStyle: { color: chartColors[i], type: "dashed", width: 2 },
              silent: true,
            },
          ];
        }),
      }}
    >
      <div className="instrument-legend">
        {data.map((s, i) => (
          <button
            key={s.key}
            aria-pressed={!hidden.includes(s.key)}
            onClick={() =>
              setHidden((prev) =>
                prev.includes(s.key)
                  ? prev.filter((k) => k !== s.key)
                  : [...prev, s.key],
              )
            }
          >
            <i style={{ background: chartColors[i] }} />
            {s.label} <span>{s.points.length} ölçüm</span>
          </button>
        ))}
      </div>
      <details className="instrument-data">
        <summary>Eğilim değerleri ve ölçüm tablosu</summary>
        {data.map((s) => (
          <div key={s.key}>
            <p>
              {s.label} ·{" "}
              {s.fit
                ? `Eğim ${num(s.fit.m * 1e6, 2)} ×10⁻⁶`
                : "Eğim hesaplamak için yeterli farklı ölçüm yok."}
            </p>
            <div className="instrument-table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>{xLabel}</th>
                    <th>{yLabel}</th>
                  </tr>
                </thead>
                <tbody>
                  {s.points.map((p, i) => (
                    <tr key={i}>
                      <td>{num(p[0], 2)}</td>
                      <td>{num(p[1], 2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </details>
    </ChartSurface>
  );
}
