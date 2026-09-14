import { useMemo } from "react";
import { num } from "../lib/format";

export interface ScatterSeries {
  key: string;
  label: string;
  color: string;
  /** [x, y] noktaları — ör. [I², ΔT]. */
  points: Array<[number, number]>;
}

interface Props {
  series: ScatterSeries[];
  xLabel: string;
  yLabel: string;
  height?: number;
  emptyText?: string;
}

const WIDTH = 460;
const PAD = { top: 14, right: 16, bottom: 50, left: 58 };

/** En kucuk kareler dogrusu: egim ve kesisim. */
function linearFit(points: Array<[number, number]>): { m: number; b: number } | null {
  if (points.length < 2) return null;
  const n = points.length;
  const sumX = points.reduce((s, [x]) => s + x, 0);
  const sumY = points.reduce((s, [, y]) => s + y, 0);
  const sumXY = points.reduce((s, [x, y]) => s + x * y, 0);
  const sumXX = points.reduce((s, [x]) => s + x * x, 0);
  const denom = n * sumXX - sumX * sumX;
  if (Math.abs(denom) < 1e-9) return null;
  const m = (n * sumXY - sumX * sumY) / denom;
  const b = (sumY - m * sumX) / n;
  return { m, b };
}

/**
 * I²–ΔT tarzı dağılım grafiği: sağlıklı bağlantıda tek eğim, gevşeyen bağlantıda daha dik
 * bir eğim oluşur (ısıl direnç K arttıkça ΔT = K·I² eğrisi dikleşir). Rapor §6.5 L1-1.
 */
export function SacilimGrafik({ series, xLabel, yLabel, height = 260, emptyText }: Props) {
  const layout = useMemo(() => {
    const all = series.flatMap((s) => s.points);
    if (all.length === 0) return null;
    const xs = all.map(([x]) => x);
    const ys = all.map(([, y]) => y);
    const [x0, x1] = [Math.min(0, ...xs), Math.max(...xs) * 1.05 || 1];
    const [y0, y1] = [Math.min(0, ...ys), Math.max(...ys) * 1.15 || 1];
    const innerW = WIDTH - PAD.left - PAD.right;
    const innerH = height - PAD.top - PAD.bottom;
    const x = (v: number) => PAD.left + ((v - x0) / (x1 - x0 || 1)) * innerW;
    const y = (v: number) => PAD.top + innerH - ((v - y0) / (y1 - y0 || 1)) * innerH;
    const fits = series.map((s) => ({ key: s.key, color: s.color, fit: linearFit(s.points) }));
    return { x, y, x0, x1, y0, y1, fits };
  }, [series, height]);

  if (!layout) return <p className="dim small chart-empty">{emptyText ?? "Bu aralıkta veri yok."}</p>;
  const { x, y, x0, x1, fits } = layout;
  const xTicks = [x0, (x0 + x1) / 2, x1];
  const yTicks = [layout.y0, (layout.y0 + layout.y1) / 2, layout.y1];

  return (
    <div className="chart">
      <svg className="chart-svg" viewBox={`0 0 ${WIDTH} ${height}`} role="img" aria-label={`${xLabel} - ${yLabel} dağılımı`}>
        {yTicks.map((v) => (
          <g key={v}>
            <line className="chart-grid" x1={PAD.left} x2={WIDTH - PAD.right} y1={y(v)} y2={y(v)} />
            <text className="chart-tick" x={PAD.left - 8} y={y(v) + 4} textAnchor="end">
              {num(v, 0)}
            </text>
          </g>
        ))}
        {xTicks.map((v) => (
          <text key={v} className="chart-tick" x={x(v)} y={height - PAD.bottom + 18} textAnchor="middle">
            {num(v, 0)}
          </text>
        ))}
        <text className="chart-axis-label" x={PAD.left + (WIDTH - PAD.left - PAD.right) / 2} y={height - 6} textAnchor="middle">
          {xLabel}
        </text>
        <text className="chart-axis-label" x={14} y={PAD.top + (height - PAD.top - PAD.bottom) / 2} textAnchor="middle" transform={`rotate(-90, 14, ${PAD.top + (height - PAD.top - PAD.bottom) / 2})`}>
          {yLabel}
        </text>

        {fits.map(
          ({ key, color, fit }) =>
            fit && (
              <line
                key={`fit-${key}`}
                className="chart-fit"
                style={{ stroke: color }}
                x1={x(x0)}
                y1={y(fit.m * x0 + fit.b)}
                x2={x(x1)}
                y2={y(fit.m * x1 + fit.b)}
              />
            ),
        )}
        {series.map((s) => (
          <g key={s.key}>
            {s.points.map(([px, py], i) => (
              <circle key={i} className="chart-dot" cx={x(px)} cy={y(py)} r={3.2} style={{ fill: s.color }} />
            ))}
          </g>
        ))}
      </svg>
      <div className="chart-legend">
        {fits.map(({ key, color, fit }) => {
          const s = series.find((s) => s.key === key)!;
          return (
            <span key={key} className="chart-legend-item">
              <span className="chart-swatch" style={{ background: color }} />
              {s.label}
              {fit && <span className="dim"> — eğim {num(fit.m * 1e6, 2)} (×10⁻⁶)</span>}
            </span>
          );
        })}
      </div>
    </div>
  );
}
