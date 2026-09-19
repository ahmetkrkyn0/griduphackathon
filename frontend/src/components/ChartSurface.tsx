import { useEffect, useRef, useState, type ReactNode } from "react";
import * as echarts from "echarts/core";
import { LineChart, ScatterChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  MarkLineComponent,
} from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import type { EChartsCoreOption } from "echarts/core";

echarts.use([
  LineChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  MarkLineComponent,
  SVGRenderer,
]);
export const chartColors = [
  "#178579",
  "#8060b5",
  "#ff671e",
  "#3276bc",
  "#bd4c83",
  "#a58716",
];
/** Preserve the established series identity, adapted to the light workspace palette. */
export function chartColor(color: string) {
  const colors: Record<string, string> = {
    "#003da5": "#3276bc",
    "#456da8": "#178579",
    "#d9530f": "#ff671e",
    "#1f8a70": "#178579",
    "#7a4fbe": "#8060b5",
  };
  return colors[color.toLowerCase()] ?? color;
}
export const axisStyle = {
  axisLine: { lineStyle: { color: "#b9c4d0" } },
  axisTick: { show: false },
  axisLabel: {
    color: "#586779",
    fontFamily: "Inter",
    fontSize: 12,
    hideOverlap: true,
    formatter: (v: number) =>
      v.toLocaleString("tr-TR", { maximumFractionDigits: 2 }),
  },
  nameTextStyle: { color: "#586779", fontFamily: "Inter", fontSize: 12 },
  splitLine: { lineStyle: { color: "#e5eaf0", type: "dashed" as const } },
};
export function ChartSurface({
  option,
  height = 300,
  label,
  children,
}: {
  option: EChartsCoreOption;
  height?: number;
  label: string;
  children?: ReactNode;
}) {
  const host = useRef<HTMLDivElement>(null);
  const instance = useRef<echarts.ECharts>();
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!host.current) return;
    const chart = echarts.init(host.current, undefined, { renderer: "svg" });
    instance.current = chart;
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(host.current);
    return () => {
      observer.disconnect();
      chart.dispose();
      instance.current = undefined;
    };
  }, []);
  useEffect(() => {
    try {
      instance.current?.setOption(
        { animation: false, textStyle: { fontFamily: "Inter" }, ...option },
        { replaceMerge: ["series", "xAxis", "yAxis"] },
      );
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }, [option]);
  const download = () => {
    const url = instance.current?.getDataURL({
      type: "svg",
      backgroundColor: "#ffffff",
    });
    if (!url) return;
    const a = document.createElement("a");
    a.href = url;
    a.download = "pano-analiz.svg";
    a.click();
  };
  return (
    <div className="instrument-chart">
      <div className="instrument-tools">
        <span className="instrument-caption">ÖLÇÜM ANALİZİ</span>
        <div>
          <button
            type="button"
            onClick={() =>
              instance.current?.dispatchAction({
                type: "dataZoom",
                start: 0,
                end: 100,
              })
            }
          >
            Aralığı sıfırla
          </button>
          <button
            type="button"
            onClick={download}
            aria-label={`${label} SVG indir`}
          >
            SVG ↓
          </button>
        </div>
      </div>
      {failed && (
        <p role="alert">
          Grafik çizilemedi. Ölçümleri veri tablosundan inceleyebilirsiniz.
        </p>
      )}
      <div
        ref={host}
        style={{ height }}
        role="img"
        aria-label={label}
        className="echart-host"
      />
      {children}
    </div>
  );
}
