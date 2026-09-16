import { useMemo, useState } from "react";
import { num } from "../lib/format";

export interface ChartSeries {
  key: string;
  label: string;
  color: string;
  points: Array<[number, number | null]>;
  /** ikinci y ekseni: farklı birimdeki bir seriyi aynı grafikte gösterir (ör. akım vs sıcaklık). */
  axis?: "left" | "right";
  dash?: boolean;
}

export interface ChartMarker {
  tMs: number;
  label: string;
  color?: string;
}

interface Props {
  series: ChartSeries[];
  height?: number;
  markers?: ChartMarker[];
  yLabelLeft?: string;
  yLabelRight?: string;
  /** API'den gelen esik cizgisi (kural 10: deger burada SABIT degil, cagiran API'den aktarir). */
  thresholdLeft?: { value: number; label: string };
  emptyText?: string;
}

const WIDTH = 640;
const PAD = { top: 14, right: 50, bottom: 28, left: 50 };
const fmtDay = new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "short" });
const fmtTime = new Intl.DateTimeFormat("tr-TR", { hour: "2-digit", minute: "2-digit" });
const fmtFull = new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

function niceDomain(min: number, max: number): [number, number] {
  if (min === max) return [min - 1, max + 1];
  const pad = (max - min) * 0.08;
  return [min - pad, max + pad];
}

function buildPath(points: Array<[number, number | null]>, x: (t: number) => number, y: (v: number) => number): string {
  let d = "";
  let started = false;
  for (const [t, v] of points) {
    if (v == null || Number.isNaN(v)) {
      started = false;
      continue;
    }
    d += `${started ? "L" : "M"}${x(t).toFixed(1)},${y(v).toFixed(1)} `;
    started = true;
  }
  return d.trim();
}

/** Kucuk, bagimliliksiz cok-serili cizgi grafik. Birden fazla sayfada kullanilir. */
export function CizgiGrafik({ series, height = 220, markers = [], yLabelLeft, yLabelRight, thresholdLeft, emptyText }: Props) {
  const [hover, setHover] = useState<{ xSvg: number; clientPct: number; t: number } | null>(null);

  const layout = useMemo(() => {
    const withData = series.filter((s) => s.points.some(([, v]) => v != null));
    const allT = withData.flatMap((s) => s.points.map(([t]) => t));
    if (allT.length === 0 || withData.length === 0) return null;

    const [t0, t1] = [Math.min(...allT), Math.max(...allT)];
    const leftVals = withData.filter((s) => s.axis !== "right").flatMap((s) => s.points.map(([, v]) => v).filter((v): v is number => v != null));
    const rightVals = withData.filter((s) => s.axis === "right").flatMap((s) => s.points.map(([, v]) => v).filter((v): v is number => v != null));
    const withThreshold = thresholdLeft ? [...leftVals, thresholdLeft.value] : leftVals;
    const [yl0, yl1] = leftVals.length ? niceDomain(Math.min(...withThreshold), Math.max(...withThreshold)) : [0, 1];
    const [yr0, yr1] = rightVals.length ? niceDomain(Math.min(...rightVals), Math.max(...rightVals)) : [0, 1];

    const innerW = WIDTH - PAD.left - PAD.right;
    const innerH = height - PAD.top - PAD.bottom;
    const x = (t: number) => PAD.left + ((t - t0) / (t1 - t0 || 1)) * innerW;
    const yLeft = (v: number) => PAD.top + innerH - ((v - yl0) / (yl1 - yl0 || 1)) * innerH;
    const yRight = (v: number) => PAD.top + innerH - ((v - yr0) / (yr1 - yr0 || 1)) * innerH;

    const spanMs = t1 - t0;
    const fmt = spanMs > 36 * 3_600_000 ? fmtDay : fmtTime;
    const xTicks = [t0, t0 + spanMs / 2, t1];
    const leftTicks = [yl0, (yl0 + yl1) / 2, yl1];
    const rightTicks = [yr0, (yr0 + yr1) / 2, yr1];

    return { x, yLeft, yRight, leftTicks, rightTicks, xTicks, fmt, hasRight: rightVals.length > 0, t0, t1, spanMs };
  }, [series, height, thresholdLeft]);

  if (!layout) {
    return <p className="dim small chart-empty">{emptyText ?? "Bu aralıkta veri yok."}</p>;
  }
  const { x, yLeft, yRight, leftTicks, rightTicks, xTicks, fmt, hasRight, t0, spanMs } = layout;

  const onPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const relX = e.clientX - rect.left;
    const clientPct = (relX / rect.width) * 100;
    const svgX = (relX / rect.width) * WIDTH;
    if (svgX < PAD.left || svgX > WIDTH - PAD.right) {
      setHover(null);
      return;
    }
    const innerW = WIDTH - PAD.left - PAD.right;
    const ratio = (svgX - PAD.left) / innerW;
    const t = t0 + ratio * spanMs;
    setHover({ xSvg: svgX, clientPct, t });
  };

  const onPointerLeave = () => setHover(null);

  // Imlece en yakin degerleri bul
  const hoveredData = hover
    ? series
        .map((s) => {
          const valid = s.points.filter((p): p is [number, number] => p[1] != null);
          if (valid.length === 0) return null;
          let best = valid[0];
          let minDiff = Math.abs(valid[0][0] - hover.t);
          for (let i = 1; i < valid.length; i++) {
            const diff = Math.abs(valid[i][0] - hover.t);
            if (diff < minDiff) {
              minDiff = diff;
              best = valid[i];
            }
          }
          return {
            key: s.key,
            label: s.label,
            color: s.color,
            val: best[1],
            ySvg: s.axis === "right" ? yRight(best[1]) : yLeft(best[1]),
          };
        })
        .filter((d): d is NonNullable<typeof d> => d != null)
    : [];

  return (
    <div className="chart">
      <svg
        className="chart-svg"
        viewBox={`0 0 ${WIDTH} ${height}`}
        role="img"
        aria-label={series.map((s) => s.label).join(", ")}
        onPointerMove={onPointerMove}
        onPointerLeave={onPointerLeave}
      >
        {leftTicks.map((v) => (
          <g key={v}>
            <line className="chart-grid" x1={PAD.left} x2={WIDTH - PAD.right} y1={yLeft(v)} y2={yLeft(v)} />
            <text className="chart-tick" x={PAD.left - 8} y={yLeft(v) + 4} textAnchor="end">
              {num(v, Math.abs(v) < 5 ? 2 : 0)}
            </text>
          </g>
        ))}
        {hasRight &&
          rightTicks.map((v) => (
            <text key={v} className="chart-tick" x={WIDTH - PAD.right + 8} y={yRight(v) + 4} textAnchor="start">
              {num(v, 0)}
            </text>
          ))}
        {xTicks.map((t) => (
          <text key={t} className="chart-tick" x={x(t)} y={height - 6} textAnchor="middle">
            {fmt.format(t)}
          </text>
        ))}

        {thresholdLeft && (
          <g>
            <line className="chart-threshold" x1={PAD.left} x2={WIDTH - PAD.right} y1={yLeft(thresholdLeft.value)} y2={yLeft(thresholdLeft.value)} />
            <text className="chart-threshold-label" x={WIDTH - PAD.right} y={yLeft(thresholdLeft.value) - 4} textAnchor="end">
              {thresholdLeft.label}
            </text>
          </g>
        )}

        {markers.map((m) => (
          <g key={m.tMs}>
            <line className="chart-marker" style={m.color ? { stroke: m.color } : undefined} x1={x(m.tMs)} x2={x(m.tMs)} y1={PAD.top} y2={height - PAD.bottom} />
            <text className="chart-marker-label" x={x(m.tMs)} y={PAD.top + 10} textAnchor="middle">
              {m.label}
            </text>
          </g>
        ))}

        {series.map((s) => (
          <path
            key={s.key}
            className={s.dash ? "chart-line dash" : "chart-line"}
            style={{ stroke: s.color }}
            d={buildPath(s.points, x, (v) => (s.axis === "right" ? yRight(v) : yLeft(v)))}
            fill="none"
          />
        ))}

        {hover && (
          <g className="chart-crosshair-group">
            <line
              className="chart-crosshair"
              x1={hover.xSvg}
              x2={hover.xSvg}
              y1={PAD.top}
              y2={height - PAD.bottom}
            />
            {hoveredData.map((d) => (
              <circle
                key={d.key}
                cx={hover.xSvg}
                cy={d.ySvg}
                r={3.5}
                fill={d.color}
                stroke="var(--surface, #fff)"
                strokeWidth={1.5}
              />
            ))}
          </g>
        )}
      </svg>

      {hover && hoveredData.length > 0 && (
        <div
          className="chart-tooltip"
          style={{
            left: `${Math.min(Math.max(hover.clientPct, 15), 85)}%`,
          }}
        >
          <div className="chart-tooltip-time">{fmtFull.format(hover.t)}</div>
          <div className="chart-tooltip-rows">
            {hoveredData.map((h) => (
              <div key={h.key} className="chart-tooltip-row">
                <span className="chart-swatch" style={{ background: h.color }} />
                <span className="chart-tooltip-label">{h.label}:</span>
                <span className="chart-tooltip-val">{num(h.val, 1)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="chart-legend">
        {series.map((s) => (
          <span key={s.key} className="chart-legend-item">
            <span className="chart-swatch" style={{ background: s.color }} />
            {s.label}
            {s.axis === "right" ? " (sağ eksen)" : ""}
          </span>
        ))}
        {(yLabelLeft || yLabelRight) && (
          <span className="dim small">
            {yLabelLeft}
            {yLabelLeft && yLabelRight ? " · " : ""}
            {yLabelRight}
          </span>
        )}
      </div>
    </div>
  );
}
