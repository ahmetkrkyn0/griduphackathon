import { useChartWidth } from "../lib/useChartWidth";
import { useState } from "react";
import { Link } from "react-router-dom";
import type { PanelSummary } from "../api/types";
import { PRIO_NAME } from "../lib/labels";
import { axisFraction, effectivePrio } from "../lib/worklist";
import { ttlText } from "../lib/format";

const H = 310;
const L = 65,
  R = 36,
  T = 24,
  B = 48;
const ticks = [0, 24, 72, 168, 336];
export function RiskMatrisi({ panels }: { panels: PanelSummary[] }) {
  const { ref, width: W } = useChartWidth();
  const [active, setActive] = useState<string | null>(null);
  const x = (hours: number) => L + 95 + axisFraction(hours) * (W - L - R - 95);
  const y = (risk: number) =>
    T + (1 - Math.max(0, Math.min(100, risk)) / 100) * (H - T - B);
  const focused = panels.find((p) => p.pano_id === active);
  return (
    <div className="riskmx" ref={ref}>
      <div className="risk-chart-summary">
        <span>VARLIK SAĞLIĞI</span>
        <strong>{panels.length} pano</strong>
        <span>{panels.filter((p) => p.ttl_h != null).length} süre tahmini</span>
      </div>
      <div className="chart-viewport">
        <svg
          className="chart-svg"
          viewBox={`0 0 ${W} ${H}`}
          role="group"
          aria-label="Pano risk dağılımı: düşey risk skoru, yatay sınıra kalan süre. Süre tahmini olmayanlar ayrı sütundadır."
        >
          <rect
            x={L + 95}
            y={T}
            width={Math.max(0, W - L - R - 95)}
            height={H - T - B}
            fill="#fafbfd"
            rx={4}
          />
          <rect
            x={L - 19}
            y={T}
            width={77}
            height={H - T - B}
            rx={5}
            fill="#f3f5f7"
          />
          {[0, 25, 50, 75, 100].map((n) => (
            <g key={n}>
              <line
                className="chart-grid"
                x1={L - 19}
                x2={W - R}
                y1={y(n)}
                y2={y(n)}
              />
              <text
                className="chart-tick"
                x={L - 28}
                y={y(n) + 4}
                textAnchor="end"
              >
                {n}
              </text>
            </g>
          ))}
          {ticks
            .filter(
              (h) => W > 460 || (W < 360 ? [0, 336] : [0, 72, 336]).includes(h),
            )
            .map((h) => (
              <g key={h}>
                <line
                  className="chart-grid"
                  x1={x(h)}
                  x2={x(h)}
                  y1={T}
                  y2={H - B}
                />
                <text
                  className="chart-tick"
                  x={x(h)}
                  y={H - B + 21}
                  textAnchor="middle"
                >
                  {h === 0 ? "Şimdi" : `${h / 24} gün`}
                </text>
              </g>
            ))}
          <text
            className="chart-tick"
            x={L + 19}
            y={H - B + 21}
            textAnchor="middle"
          >
            Tahmin yok
          </text>
          <text className="chart-units" x={L - 19} y={12}>
            RİSK SKORU
          </text>
          <text className="chart-units" x={W - R} y={H - 4} textAnchor="end">
            SINIRA KALAN SÜRE · LOG ÖLÇEK
          </text>
          {panels.map((p) => {
            const prio = effectivePrio(p);
            const px = p.ttl_h == null ? L + 19 : x(p.ttl_h);
            const py = y(p.risk_score);
            const selected = active === p.pano_id;
            return (
              <Link
                key={p.pano_id}
                to={`/pano/${p.pano_id}`}
                className={`riskmx-pt${prio ? ` p-${prio}` : ""}`}
                aria-label={`${p.name}, risk ${p.risk_score}, ${ttlText(p.ttl_h) || "süre tahmini yok"}`}
                onMouseEnter={() => setActive(p.pano_id)}
                onMouseLeave={() => setActive(null)}
                onFocus={() => setActive(p.pano_id)}
                onBlur={() => setActive(null)}
              >
                <title>
                  {p.name}: risk {p.risk_score},{" "}
                  {ttlText(p.ttl_h) || "Süre tahmini yok"}
                </title>
                <circle className="riskmx-hit" cx={px} cy={py} r={15} />
                <circle
                  cx={px}
                  cy={py}
                  r={selected ? 13 : 10}
                  fill={prio ? `var(--${prio.toLowerCase()})` : "var(--dot)"}
                  opacity={0.1}
                />
                <circle
                  className="riskmx-dot"
                  cx={px}
                  cy={py}
                  r={selected ? 7 : 5.5}
                />
                {(selected || (W > 460 && p.risk_score >= 70)) && (
                  <text
                    className="riskmx-label"
                    x={px > W - 100 ? px - 13 : px + 13}
                    textAnchor={px > W - 100 ? "end" : "start"}
                    y={py - 9}
                    paintOrder="stroke"
                    stroke="white"
                    strokeWidth={4}
                    strokeLinejoin="round"
                  >
                    {p.name.split(" ")[0]}
                  </text>
                )}
              </Link>
            );
          })}
        </svg>
      </div>
      <p className="chart-scroll-hint">Grafiğin tamamı için yatay kaydırın.</p>
      <div className="risk-footer">
        {focused ? (
          <span>
            <strong>{focused.name}</strong> · Risk {focused.risk_score} ·{" "}
            {ttlText(focused.ttl_h) || "Süre tahmini yok"}
          </span>
        ) : (
          <span>Noktalara odaklanın veya pano ayrıntısını açın.</span>
        )}
        <div>
          {(["P1", "P2", "P3", "SYS"] as const).map((p) => (
            <span key={p}>
              <i style={{ background: `var(--${p.toLowerCase()})` }} />
              {PRIO_NAME[p]}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
