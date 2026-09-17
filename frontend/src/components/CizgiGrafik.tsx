import { useId, useMemo, useState } from "react";
import { chartTicks, linePath, nearestSample } from "../lib/chartMath";
import { useChartWidth } from "../lib/useChartWidth";
import { num } from "../lib/format";

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
interface Props {
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
const formatTick = (n: number) =>
  Math.abs(n) >= 100000
    ? `${num(n / 1000, 0)}k`
    : num(n, Math.abs(n) < 10 ? 1 : 0);

export function CizgiGrafik({
  series,
  height = 270,
  markers = [],
  yLabelLeft,
  yLabelRight,
  thresholdLeft,
  emptyText,
  yDomainLeft,
}: Props) {
  const id = useId();
  const { ref, width: W } = useChartWidth();
  const hasRight = series.some((s) => s.axis === "right");
  const PAD = { top: 32, right: hasRight ? 64 : 24, bottom: 32, left: 48 };
  const tickCount = W < 420 ? 3 : 5;
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [hover, setHover] = useState<number | null>(null);
  const shown = series.filter((s) => !hidden.has(s.key));
  const layout = useMemo(() => {
    const times = [
      ...new Set(
        series.flatMap((s) => s.points.map(([t]) => t)).filter(Number.isFinite),
      ),
    ].sort((a, b) => a - b);
    if (
      !times.length ||
      !series.some((s) =>
        s.points.some(([, v]) => v != null && Number.isFinite(v)),
      )
    )
      return null;
    const t0 = times[0],
      t1 = times.at(-1)!;
    const vals = (axis: string) =>
      series
        .filter((s) => (s.axis ?? "left") === axis)
        .flatMap((s) => s.points.flatMap(([, v]) => (v == null ? [] : [v])));
    const left =
      yDomainLeft && yDomainLeft[1] > yDomainLeft[0]
        ? Array.from(
            { length: 5 },
            (_, i) =>
              yDomainLeft[0] + ((yDomainLeft[1] - yDomainLeft[0]) * i) / 4,
          )
        : chartTicks([
            ...vals("left"),
            ...(thresholdLeft ? [thresholdLeft.value] : []),
          ]);
    const right = chartTicks(vals("right"));
    const x = (t: number) =>
      PAD.left + ((t - t0) / (t1 - t0 || 1)) * (W - PAD.left - PAD.right);
    const y = (v: number, axis?: string) => {
      const ticks = axis === "right" ? right : left;
      return (
        height -
        PAD.bottom -
        ((v - ticks[0]) / (ticks.at(-1)! - ticks[0])) *
          (height - PAD.top - PAD.bottom)
      );
    };
    return { times, t0, t1, x, y, left, right };
  }, [series, height, thresholdLeft, W, yDomainLeft, hasRight]);
  if (!layout)
    return (
      <p className="dim small chart-empty">
        {emptyText ?? "Bu aralıkta ölçüm verisi bulunmuyor."}
      </p>
    );
  const { times, t0, t1, x, y, left, right } = layout;
  const currentTime = hover == null ? t1 : Math.max(t0, Math.min(t1, hover));
  const readouts = shown.map((s) => ({
    ...s,
    sample: nearestSample(s.points, currentTime),
  }));
  const fmt = new Intl.DateTimeFormat(
    "tr-TR",
    t1 - t0 > 36 * 3600000
      ? { day: "numeric", month: "short", timeZone: "Europe/Istanbul" }
      : { hour: "2-digit", minute: "2-digit", timeZone: "Europe/Istanbul" },
  );
  const toggle = (key: string) =>
    setHidden((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  return (
    <div className="chart" ref={ref}>
      <div className="chart-readout">
        <span>
          {hover == null ? "Son ölçüm · " : ""}
          {stamp.format(currentTime)}
        </span>
        {readouts.map((s) => (
          <span className="chart-readout-value" key={s.key}>
            <i style={{ background: s.color }} />
            {s.label}
            <strong>
              {s.sample?.[1] != null && Number.isFinite(s.sample[1])
                ? num(s.sample[1], 2)
                : "Veri yok"}
            </strong>
          </span>
        ))}
      </div>
      <div className="chart-viewport">
        <svg
          className="chart-svg"
          viewBox={`0 0 ${W} ${height}`}
          role="img"
          tabIndex={0}
          aria-label={`${series.map((s) => s.label).join(", ")}. Değer okumak için sağ ve sol ok tuşlarını kullanın.`}
          onPointerMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const px = ((e.clientX - rect.left) / rect.width) * W;
            const t =
              t0 +
              Math.max(
                0,
                Math.min(1, (px - PAD.left) / (W - PAD.left - PAD.right)),
              ) *
                (t1 - t0);
            setHover(
              nearestSample(
                times.map((v) => [v, v]),
                t,
              )?.[0] ?? t,
            );
          }}
          onPointerLeave={() => setHover(null)}
          onBlur={() => setHover(null)}
          onKeyDown={(e) => {
            if (
              !["ArrowLeft", "ArrowRight", "Home", "End", "Escape"].includes(
                e.key,
              )
            )
              return;
            e.preventDefault();
            if (e.key === "Escape") {
              setHover(null);
              return;
            }
            const index = times.indexOf(
              nearestSample(
                times.map((t) => [t, t]),
                currentTime,
              )![0],
            );
            setHover(
              e.key === "Home"
                ? t0
                : e.key === "End"
                  ? t1
                  : times[
                      Math.max(
                        0,
                        Math.min(
                          times.length - 1,
                          index + (e.key === "ArrowRight" ? 1 : -1),
                        ),
                      )
                    ],
            );
          }}
        >
          <defs>
            <clipPath id={id}>
              <rect
                x={PAD.left}
                y={PAD.top}
                width={W - PAD.left - PAD.right}
                height={height - PAD.top - PAD.bottom}
              />
            </clipPath>
          </defs>
          <text className="chart-units" x={PAD.left} y={13}>
            {yLabelLeft}
          </text>
          {hasRight && (
            <text
              className="chart-units"
              x={W - PAD.right}
              y={13}
              textAnchor="end"
            >
              {yLabelRight}
            </text>
          )}
          {left.map((v) => (
            <g key={v}>
              <line
                className="chart-grid"
                x1={PAD.left}
                x2={W - PAD.right}
                y1={y(v)}
                y2={y(v)}
              />
              <text
                className="chart-tick"
                x={PAD.left - 12}
                y={y(v) + 4}
                textAnchor="end"
              >
                {formatTick(v)}
              </text>
            </g>
          ))}
          {hasRight &&
            right.map((v) => (
              <text
                key={v}
                className="chart-tick"
                x={W - PAD.right + 12}
                y={y(v, "right") + 4}
              >
                {formatTick(v)}
              </text>
            ))}
          {(t0 === t1
            ? [t0]
            : Array.from(
                { length: tickCount },
                (_, i) => t0 + ((t1 - t0) * i) / (tickCount - 1),
              )
          ).map((t, i) => (
            <text
              key={i}
              className="chart-tick"
              x={x(t)}
              y={height - 8}
              textAnchor="middle"
            >
              {fmt.format(t)}
            </text>
          ))}
          <g clipPath={`url(#${id})`}>
            {thresholdLeft && (
              <line
                className="chart-threshold"
                x1={PAD.left}
                x2={W - PAD.right}
                y1={y(thresholdLeft.value)}
                y2={y(thresholdLeft.value)}
              />
            )}
            {markers
              .filter((m) => m.tMs >= t0 && m.tMs <= t1)
              .map((m, i) => (
                <g key={`${m.tMs}-${i}`}>
                  <line
                    className="chart-marker"
                    style={{ stroke: m.color }}
                    x1={x(m.tMs)}
                    x2={x(m.tMs)}
                    y1={PAD.top}
                    y2={height - PAD.bottom}
                  />
                  <text
                    className="chart-marker-label"
                    x={x(m.tMs) - 6}
                    y={PAD.top + 11}
                    textAnchor="end"
                  >
                    {m.label}
                  </text>
                </g>
              ))}
            {shown.map((s) => (
              <path
                key={s.key}
                className={`chart-line${s.dash ? " dash" : ""}`}
                style={{ stroke: s.color }}
                d={linePath(s.points, x, (v) => y(v, s.axis))}
                fill="none"
              />
            ))}
            {shown
              .filter((s) => s.points.filter(([, v]) => v != null).length === 1)
              .map((s) => {
                const point = s.points.find(([, v]) => v != null)!;
                return (
                  <circle
                    key={s.key}
                    cx={x(point[0])}
                    cy={y(point[1]!, s.axis)}
                    r={3}
                    fill={s.color}
                  />
                );
              })}
            {hover != null && (
              <>
                <line
                  className="chart-crosshair"
                  x1={x(currentTime)}
                  x2={x(currentTime)}
                  y1={PAD.top}
                  y2={height - PAD.bottom}
                />
                {readouts.map(
                  (s) =>
                    s.sample?.[1] != null && (
                      <circle
                        key={s.key}
                        cx={x(s.sample[0])}
                        cy={y(s.sample[1], s.axis)}
                        r={4}
                        fill={s.color}
                        stroke="white"
                        strokeWidth={2}
                      />
                    ),
                )}
              </>
            )}
          </g>
          {thresholdLeft && (
            <text
              className="chart-threshold-label"
              x={W - PAD.right}
              y={y(thresholdLeft.value) - 5}
              textAnchor="end"
            >
              {thresholdLeft.label}
            </text>
          )}
        </svg>
      </div>
      <p className="chart-scroll-hint">Grafiğin tamamı için yatay kaydırın.</p>
      <div className="chart-legend">
        {series.map((s) => (
          <button
            key={s.key}
            className="chart-legend-item"
            aria-pressed={!hidden.has(s.key)}
            onClick={() => toggle(s.key)}
          >
            <span className="chart-swatch" style={{ background: s.color }} />
            {s.label}
            {s.axis === "right" ? " · sağ eksen" : ""}
          </button>
        ))}
        <span className="dim">Serilere tıklayarak karşılaştırın</span>
      </div>
    </div>
  );
}
