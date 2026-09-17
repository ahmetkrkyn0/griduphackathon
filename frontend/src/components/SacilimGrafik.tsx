import { useId, useMemo, useState } from "react";
import { chartTicks } from "../lib/chartMath";
import { useChartWidth } from "../lib/useChartWidth";
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

const PAD = { top: 20, right: 25, bottom: 50, left: 65 };

/** En kucuk kareler dogrusu: egim ve kesisim. */
function linearFit(
  points: Array<[number, number]>,
): { m: number; b: number } | null {
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
export function SacilimGrafik({
  series,
  xLabel,
  yLabel,
  height = 270,
  emptyText,
}: Props) {
  const id = useId();
  const { ref, width: WIDTH } = useChartWidth();
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const layout = useMemo(() => {
    const all = series
      .flatMap((s) => s.points)
      .filter(([x, y]) => Number.isFinite(x) && Number.isFinite(y));
    if (all.length === 0) return null;
    const xs = all.map(([x]) => x);
    const ys = all.map(([, y]) => y);
    const xTicks = chartTicks(xs, true),
      yTicks = chartTicks(ys, true);
    const [x0, x1] = [xTicks[0], xTicks.at(-1)!];
    const [y0, y1] = [yTicks[0], yTicks.at(-1)!];
    const innerW = WIDTH - PAD.left - PAD.right;
    const innerH = height - PAD.top - PAD.bottom;
    const x = (v: number) => PAD.left + ((v - x0) / (x1 - x0 || 1)) * innerW;
    const y = (v: number) =>
      PAD.top + innerH - ((v - y0) / (y1 - y0 || 1)) * innerH;
    const fits = series.map((s) => ({
      key: s.key,
      color: s.color,
      fit: linearFit(
        s.points.filter(([x, y]) => Number.isFinite(x) && Number.isFinite(y)),
      ),
    }));
    return { x, y, x0, x1, xTicks, yTicks, fits };
  }, [series, height, WIDTH]);

  if (!layout)
    return (
      <p className="dim small chart-empty">
        {emptyText ?? "Bu aralıkta veri yok."}
      </p>
    );
  const { x, y, x0, x1, fits, xTicks, yTicks } = layout;

  return (
    <div className="chart" ref={ref}>
      <div className="scatter-summary">
        {series.map((s) => (
          <span key={s.key}>
            <strong style={{ color: s.color }}>
              {
                s.points.filter(
                  ([x, y]) => Number.isFinite(x) && Number.isFinite(y),
                ).length
              }
            </strong>{" "}
            ölçüm · {s.label}
          </span>
        ))}
      </div>
      <div className="chart-viewport">
        <svg
          className="chart-svg"
          viewBox={`0 0 ${WIDTH} ${height}`}
          role="img"
          aria-label={`${xLabel} - ${yLabel} dağılımı`}
        >
          <defs>
            <clipPath id={id}>
              <rect
                x={PAD.left}
                y={PAD.top}
                width={WIDTH - PAD.left - PAD.right}
                height={height - PAD.top - PAD.bottom}
              />
            </clipPath>
          </defs>
          {yTicks.map((v) => (
            <g key={v}>
              <line
                className="chart-grid"
                x1={PAD.left}
                x2={WIDTH - PAD.right}
                y1={y(v)}
                y2={y(v)}
              />
              <text
                className="chart-tick"
                x={PAD.left - 8}
                y={y(v) + 4}
                textAnchor="end"
              >
                {num(v, 0)}
              </text>
            </g>
          ))}
          {xTicks
            .filter(
              (_, i) => WIDTH >= 420 || i % 2 === 0 || i === xTicks.length - 1,
            )
            .map((v) => (
              <text
                key={v}
                className="chart-tick"
                x={x(v)}
                y={height - PAD.bottom + 18}
                textAnchor="middle"
              >
                {Math.abs(v) >= 1000 ? `${num(v / 1000, 0)}k` : num(v, 0)}
              </text>
            ))}
          <text
            className="chart-axis-label"
            x={PAD.left + (WIDTH - PAD.left - PAD.right) / 2}
            y={height - 6}
            textAnchor="middle"
          >
            {xLabel}
          </text>
          <text
            className="chart-axis-label"
            x={14}
            y={PAD.top + (height - PAD.top - PAD.bottom) / 2}
            textAnchor="middle"
            transform={`rotate(-90, 14, ${PAD.top + (height - PAD.top - PAD.bottom) / 2})`}
          >
            {yLabel}
          </text>

          <g clipPath={`url(#${id})`}>
            {fits
              .filter((s) => !hidden.has(s.key))
              .map(
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
            {series
              .filter((s) => !hidden.has(s.key))
              .map((s) => (
                <g key={s.key}>
                  {s.points
                    .filter(
                      ([x, y]) => Number.isFinite(x) && Number.isFinite(y),
                    )
                    .map(([px, py], i) => (
                      <circle
                        key={i}
                        className="chart-dot"
                        cx={x(px)}
                        cy={y(py)}
                        r={3}
                        style={{ fill: s.color }}
                        opacity={0.45}
                      >
                        <title>
                          {s.label}: {xLabel} {num(px, 0)}, {yLabel}{" "}
                          {num(py, 2)}
                        </title>
                      </circle>
                    ))}
                </g>
              ))}
          </g>
        </svg>
      </div>
      <p className="chart-scroll-hint">Grafiğin tamamı için yatay kaydırın.</p>
      <div className="chart-legend">
        {fits.map(({ key, color, fit }) => {
          const s = series.find((s) => s.key === key)!;
          return (
            <button
              key={key}
              className="chart-legend-item"
              aria-pressed={!hidden.has(key)}
              onClick={() =>
                setHidden((prev) => {
                  const next = new Set(prev);
                  next.has(key) ? next.delete(key) : next.add(key);
                  return next;
                })
              }
            >
              <span className="chart-swatch" style={{ background: color }} />
              {s.label}
              {fit && (
                <span className="dim">
                  {" "}
                  — eğim {num(fit.m * 1e6, 2)} (×10⁻⁶)
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
