import type { KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import type { PanelSummary } from "../api/types";
import { axisFraction, effectivePrio } from "../lib/worklist";

interface Props {
  panels: PanelSummary[];
}

const WIDTH = 700;
const HEIGHT = 340;
const PAD = { top: 20, right: 20, bottom: 46, left: 46 };
const X_TICKS_H = [0, 24, 72, 24 * 7, 24 * 14];

const xTickLabel = (h: number) => (h === 0 ? "şimdi" : h < 24 ? `${h} sa` : `${h / 24} gün`);

/**
 * Filo ekranının ikinci görünümü (Y3): x = sınıra kalan süre (log, worklist.ts'teki eksenle
 * aynı ölçek), y = risk skoru (API'den, 0-100). SOL-ÜST köşe en acil + en yüksek risk demektir
 * (x soldan sağa zaman arttığı için — ilk taslakta "sağ üst" yazılmıştı, uygulama sırasında
 * düzeltildi). İlham: Hitachi Lumada APM olasılık×etki risk matrisi (TASARIM-REVIZYONU.md §2, Y3).
 *
 * "Etki" için plan trafo gücünü (kVA) öneriyordu, ama sözleşmede filodaki tüm panolar aynı
 * `pano_type` (1600 kVA, docs/10-bom-maliyet-roi.md) — bu alan hiç değişmiyor, y ekseni sabit
 * olurdu. Bunun yerine gerçekten değişen ve API'nin verdiği `risk_score` kullanıldı; kVA
 * KULLANILMADI (dürüstlük kuralı — sabit bir alanı "etki" gibi göstermek yanıltıcı olurdu).
 * Ttl'i olmayan (ör. ark, koruma sağlığı kaybı) alarmlar x=0 (şimdi) noktasına yerleşir: bunlar
 * zaten anlık müdahale gerektirir, bir geri sayımları yoktur.
 */
export function RiskMatrisi({ panels }: Props) {
  const navigate = useNavigate();
  const innerW = WIDTH - PAD.left - PAD.right;
  const innerH = HEIGHT - PAD.top - PAD.bottom;
  const x = (ttlH: number | null) => PAD.left + axisFraction(ttlH ?? 0) * innerW;
  const y = (risk: number) => PAD.top + innerH - (Math.min(100, Math.max(0, risk)) / 100) * innerH;

  const go = (panoId: string) => navigate(`/pano/${panoId}`);
  const onKey = (event: KeyboardEvent, panoId: string) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      go(panoId);
    }
  };

  return (
    <div className="riskmx">
      <svg
        className="chart-svg"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label="Risk matrisi: yatay eksende sınıra kalan süre, dikey eksende risk skoru. Sol üst köşe en acil ve en yüksek riskli panoları gösterir."
      >
        <rect className="riskmx-quad" x={PAD.left} y={PAD.top} width={innerW / 2} height={innerH / 2} />

        {X_TICKS_H.map((h) => (
          <g key={h}>
            <line className="chart-grid" x1={x(h)} x2={x(h)} y1={PAD.top} y2={HEIGHT - PAD.bottom} />
            <text className="chart-tick" x={x(h)} y={HEIGHT - PAD.bottom + 18} textAnchor="middle">
              {xTickLabel(h)}
            </text>
          </g>
        ))}
        {[0, 50, 100].map((r) => (
          <g key={r}>
            <line className="chart-grid" x1={PAD.left} x2={WIDTH - PAD.right} y1={y(r)} y2={y(r)} />
            <text className="chart-tick" x={PAD.left - 8} y={y(r) + 4} textAnchor="end">
              {r}
            </text>
          </g>
        ))}
        <text className="chart-axis-label" x={PAD.left + innerW / 2} y={HEIGHT - 6} textAnchor="middle">
          Sınıra kalan süre
        </text>
        <text
          className="chart-axis-label"
          x={14}
          y={PAD.top + innerH / 2}
          textAnchor="middle"
          transform={`rotate(-90, 14, ${PAD.top + innerH / 2})`}
        >
          Risk skoru
        </text>

        {panels.map((p) => {
          const prio = effectivePrio(p);
          const px = x(p.ttl_h);
          const py = y(p.risk_score);
          const nearRight = px > WIDTH - PAD.right - 90;
          return (
            <g
              key={p.pano_id}
              className={`riskmx-pt${prio ? ` p-${prio}` : ""}`}
              role="button"
              tabIndex={0}
              aria-label={`${p.name}, risk ${p.risk_score}${p.ttl_h != null ? `, sınıra ${Math.round(p.ttl_h)} saat` : ", süre tahmini yok"}`}
              onClick={() => go(p.pano_id)}
              onKeyDown={(event) => onKey(event, p.pano_id)}
            >
              <circle className="riskmx-hit" cx={px} cy={py} r={14} />
              <circle className="riskmx-dot" cx={px} cy={py} r={6} />
              <text className="riskmx-label" x={px + (nearRight ? -10 : 10)} y={py + 4} textAnchor={nearRight ? "end" : "start"}>
                {p.name}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="dim small riskmx-caption">
        Gölgeli alan: sınırına yakın ve riski yüksek panolar — önce bunlara bakın. Sınıra kalan süre tahmini olmayan
        alarmlar (ör. ark, koruma sağlığı kaybı) "şimdi" ucuna yerleşir.
      </p>
    </div>
  );
}
