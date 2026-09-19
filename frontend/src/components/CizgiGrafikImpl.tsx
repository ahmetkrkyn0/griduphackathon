import { useMemo, useState } from "react";
import { ChartSurface, axisStyle, chartColor } from "./ChartSurface";
import { num } from "../lib/format";
import type { EChartsCoreOption } from "echarts/core";

export interface ChartSeries {
  key: string;
  label: string;
  color: string;
  points: Array<[number, number | null]>;
  axis?: "left" | "right";
  dash?: boolean;
}
export interface ChartMarker {
  tMs: number;
  label: string;
  color?: string;
}
export interface Props {
  series: ChartSeries[];
  height?: number;
  markers?: ChartMarker[];
  yLabelLeft?: string;
  yLabelRight?: string;
  thresholdLeft?: { value: number; label: string };
  emptyText?: string;
  yDomainLeft?: [number, number];
}
const stamp = new Intl.DateTimeFormat("tr-TR", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Europe/Istanbul",
});
const tick = new Intl.DateTimeFormat("tr-TR", {
  day: "numeric",
  month: "short",
  timeZone: "Europe/Istanbul",
});
const hourTick = new Intl.DateTimeFormat("tr-TR", {
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Europe/Istanbul",
});
export function CizgiGrafik({
  series,
  height = 300,
  markers = [],
  yLabelLeft,
  yLabelRight,
  thresholdLeft,
  emptyText,
  yDomainLeft,
}: Props) {
  const [hidden, setHidden] = useState<string[]>([]);
  const [cursor, setCursor] = useState(0);
  const times = useMemo(
    () =>
      [
        ...new Set(
          series
            .flatMap((s) => s.points.map(([t]) => t))
            .filter(Number.isFinite),
        ),
      ].sort((a, b) => a - b),
    [series],
  );
  const hasRight = series.some((s) => s.axis === "right");
  const option: EChartsCoreOption = useMemo(
    () => ({
      grid: { top: 40, bottom: 68, left: 54, right: hasRight ? 55 : 22 },
      tooltip: {
        trigger: "axis",
        renderMode: "richText",
        backgroundColor: "#ffffff",
        borderColor: "#dbe3ed",
        textStyle: { color: "#243449", fontFamily: "Inter" },
        axisPointer: { type: "cross", label: { backgroundColor: "#38506b" } },
        valueFormatter: (v: unknown) =>
          typeof v === "number" ? num(v, 2) : "Ölçüm yok",
      },
      xAxis: {
        ...axisStyle,
        type: "time",
        axisLabel: {
          ...axisStyle.axisLabel,
          formatter: (v: number) =>
            (times.length && times[times.length - 1] - times[0] < 172800000
              ? hourTick
              : tick
            ).format(v),
        },
        axisPointer: {
          label: { formatter: (p: { value: number }) => stamp.format(p.value) },
        },
      },
      yAxis: [
        {
          ...axisStyle,
          type: "value",
          name: yLabelLeft,
          min: yDomainLeft?.[0],
          max: yDomainLeft?.[1],
          scale: true,
        },
        ...(hasRight
          ? [
              {
                ...axisStyle,
                type: "value",
                name: yLabelRight,
                scale: true,
                splitLine: { show: false },
              },
            ]
          : []),
      ],
      dataZoom: [
        { type: "inside", filterMode: "none", zoomOnMouseWheel: "ctrl" },
        {
          type: "slider",
          bottom: 8,
          height: 10,
          borderColor: "transparent",
          backgroundColor: "#edf1f5",
          fillerColor: "rgba(255,103,30,.16)",
          showDataShadow: false,
          brushSelect: false,
          handleSize: 16,
          handleIcon:
            "path://M2,0 L6,0 Q8,0 8,2 L8,14 Q8,16 6,16 L2,16 Q0,16 0,14 L0,2 Q0,0 2,0 Z",
          handleStyle: {
            color: "#ff671e",
            borderColor: "#ffffff",
            borderWidth: 1,
          },
          textStyle: { color: "#637386" },
          showDetail: false,
        },
      ],
      series: series.map((s, i) => ({
        name: s.label,
        type: "line",
        yAxisIndex: s.axis === "right" ? 1 : 0,
        data: hidden.includes(s.key)
          ? []
          : s.points
              .filter(([t]) => Number.isFinite(t))
              .map(([t, v]) => [t, v != null && Number.isFinite(v) ? v : null]),
        connectNulls: false,
        showSymbol: s.points.length < 3,
        symbolSize: 6,
        smooth: false,
        itemStyle: { color: chartColor(s.color) },
        lineStyle: { width: 2, type: s.dash ? "dashed" : "solid" },
        areaStyle:
          series.length === 1
            ? { color: chartColor(s.color), opacity: 0.08 }
            : undefined,
        markLine:
          i === 0
            ? {
                symbol: "none",
                silent: true,
                label: {
                  color: "#586779",
                  fontSize: 10,
                  position: "insideEndTop",
                },
                lineStyle: { color: "#b85b21", type: "dashed" },
                data: [
                  ...(thresholdLeft
                    ? [
                        {
                          yAxis: thresholdLeft.value,
                          name: thresholdLeft.label,
                          label: { formatter: thresholdLeft.label },
                        },
                      ]
                    : []),
                  ...markers.map((m) => ({
                    xAxis: m.tMs,
                    name: m.label,
                    label: { formatter: m.label },
                    lineStyle: { color: m.color ?? "#8060b5" },
                  })),
                ],
              }
            : undefined,
      })),
    }),
    [
      series,
      hidden,
      hasRight,
      yLabelLeft,
      yLabelRight,
      yDomainLeft,
      thresholdLeft,
      markers,
      times,
    ],
  );
  if (
    !series.some((s) =>
      s.points.some(
        ([t, v]) => Number.isFinite(t) && v != null && Number.isFinite(v),
      ),
    )
  )
    return (
      <p className="chart-empty">
        {emptyText ?? "Bu aralıkta geçerli ölçüm yok."}
      </p>
    );
  const selectedTime = times[Math.min(cursor, times.length - 1)];
  return (
    <ChartSurface
      option={option}
      height={height}
      label={`${yLabelLeft ?? "Ölçüm"} zaman grafiği`}
    >
      <div className="instrument-legend">
        {series.map((s) => (
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
            <i style={{ background: chartColor(s.color) }} />
            {s.label}
          </button>
        ))}
      </div>
      <details className="instrument-data">
        <summary>
          Ölçüm verilerini incele · {times.length} zaman noktası
        </summary>
        <label>
          Ölçüm zamanı{" "}
          <input
            type="range"
            min={0}
            max={times.length - 1}
            value={Math.min(cursor, times.length - 1)}
            onChange={(e) => setCursor(Number(e.target.value))}
          />
        </label>
        <p aria-live="polite">{stamp.format(selectedTime)}</p>
        <table>
          <thead>
            <tr>
              <th>Seri</th>
              <th>Değer</th>
            </tr>
          </thead>
          <tbody>
            {series.map((s) => {
              const value = s.points.find(([t]) => t === selectedTime)?.[1];
              return (
                <tr key={s.key}>
                  <td>{s.label}</td>
                  <td>
                    {value != null && Number.isFinite(value)
                      ? num(value, 3)
                      : "Ölçüm yok"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </details>
    </ChartSurface>
  );
}
