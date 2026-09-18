import type { KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import type { PanelSummary } from "../api/types";
import { etkiEkseni } from "../lib/etki";
import { axisFraction, effectivePrio } from "../lib/worklist";

interface Props {
  panels: PanelSummary[];
}

const WIDTH = 700;
const HEIGHT = 340;
const PAD = { top: 20, right: 20, bottom: 46, left: 46 };
const X_TICKS_H = [0, 24, 72, 24 * 7, 24 * 14];

// Kunyesiz panolarin cizildigi ayri serit (etki modunda). Cizim alaninin ALTINDA durur ve
// kesikli bir cizgiyle ayrilir: "etkisi 0" ile "etkisi bilinmiyor" ayni yere dusmemeli.
const KUNYESIZ_BAND = 22;

const xTickLabel = (h: number) => (h === 0 ? "şimdi" : h < 24 ? `${h} sa` : `${h / 24} gün`);

/**
 * Filo ekranının ikinci görünümü (Y3): x = sınıra kalan süre (log, worklist.ts'teki eksenle
 * aynı ölçek), y = ETKİ. SOL-ÜST köşe en acil + en yüksek etki demektir (x soldan sağa zaman
 * arttığı için — ilk taslakta "sağ üst" yazılmıştı, uygulama sırasında düzeltildi).
 * İlham: Hitachi Lumada APM olasılık×etki risk matrisi (TASARIM-REVIZYONU.md §2, Y3).
 *
 * ETKİ EKSENİ — F-21 ile ne değişti
 * Önceki sürümde gerçek bir etki ekseni **yoktu** ve bu kodda dürüstçe itiraf edilmişti:
 * sözleşmede filodaki tüm panolar aynı `pano_type` (1600 kVA) olduğu için kVA sabit bir
 * eksen olurdu, bu yüzden y ekseni **risk skorunun kendisiydi** — yani matris fiilen tek
 * boyutluydu. F-21 varlık künyesini (CBS'den içe aktarılan `abone_sayisi`) getirdi ve
 * **abone sayısı gerçek bir etki eksenidir**: sayılabilir, panodan panoya değişir ve EPDK
 * Kalite Yönetmeliği Madde 8/2 zaten "etkilenen kullanıcı sayısı"nı istiyor.
 *
 * İTİRAF SİLİNMEDİ, DARALDI. Matris **künye girildiği ölçüde** iki boyutludur:
 *   - Hiçbir panonun künyesi yoksa eski davranış **aynen** korunur (y = risk skoru).
 *   - Künyesi olmayan panolar, etki modunda **ayrı bir şeritte** çizilir ve y = 0'a
 *     **konmaz**: "abonesi yok" ile "abone sayısını bilmiyoruz" aynı nokta değildir.
 * Ttl'i olmayan (ör. ark, koruma sağlığı kaybı) alarmlar x=0 (şimdi) noktasına yerleşir:
 * bunlar zaten anlık müdahale gerektirir, bir geri sayımları yoktur.
 */
export function RiskMatrisi({ panels }: Props) {
  const navigate = useNavigate();
  const innerW = WIDTH - PAD.left - PAD.right;

  // Etki ekseni karari saf fonksiyonda (lib/etki.ts) ve testle kilitli.
  const { mode: impactMode, max: maxImpact, missing } = etkiEkseni(panels);
  const showBand = impactMode && missing > 0;

  const innerH = HEIGHT - PAD.top - PAD.bottom - (showBand ? KUNYESIZ_BAND : 0);
  const yTicks = impactMode ? [0, maxImpact / 2, maxImpact] : [0, 50, 100];
  const bandY = PAD.top + innerH + KUNYESIZ_BAND / 2;

  const x = (ttlH: number | null) => PAD.left + axisFraction(ttlH ?? 0) * innerW;
  const yScale = (value: number, max: number) =>
    PAD.top + innerH - (Math.min(max, Math.max(0, value)) / max) * innerH;
  const y = (p: PanelSummary) =>
    impactMode
      ? p.abone_sayisi != null
        ? yScale(p.abone_sayisi, maxImpact)
        : bandY // kunyesiz: ayri serit, y=0 DEGIL
      : yScale(p.risk_score, 100);

  const axisLabel = impactMode ? "Etkilenen abone sayısı" : "Risk skoru";
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
        aria-label={`Risk matrisi: yatay eksende sınıra kalan süre, dikey eksende ${
          impactMode ? "etkilenen abone sayısı" : "risk skoru"
        }. Sol üst köşe en acil ve en yüksek etkili panoları gösterir.`}
      >
        <rect className="riskmx-quad" x={PAD.left} y={PAD.top} width={innerW / 2} height={innerH / 2} />

        {X_TICKS_H.map((h) => (
          <g key={h}>
            <line className="chart-grid" x1={x(h)} x2={x(h)} y1={PAD.top} y2={PAD.top + innerH} />
            <text className="chart-tick" x={x(h)} y={HEIGHT - PAD.bottom + 18} textAnchor="middle">
              {xTickLabel(h)}
            </text>
          </g>
        ))}
        {yTicks.map((value) => (
          <g key={value}>
            <line
              className="chart-grid"
              x1={PAD.left}
              x2={WIDTH - PAD.right}
              y1={yScale(value, impactMode ? maxImpact : 100)}
              y2={yScale(value, impactMode ? maxImpact : 100)}
            />
            <text
              className="chart-tick"
              x={PAD.left - 8}
              y={yScale(value, impactMode ? maxImpact : 100) + 4}
              textAnchor="end"
            >
              {Math.round(value)}
            </text>
          </g>
        ))}

        {showBand && (
          <g>
            {/* Kesikli ayirac: alttaki serit OLCEGIN PARCASI DEGILDIR. */}
            <line
              className="chart-grid riskmx-band-sep"
              x1={PAD.left}
              x2={WIDTH - PAD.right}
              y1={PAD.top + innerH + 2}
              y2={PAD.top + innerH + 2}
              strokeDasharray="4 3"
            />
            <text className="chart-tick" x={PAD.left - 8} y={bandY + 4} textAnchor="end">
              künye yok
            </text>
          </g>
        )}

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
          {axisLabel}
        </text>

        {panels.map((p) => {
          const prio = effectivePrio(p);
          const px = x(p.ttl_h);
          const py = y(p);
          const unknownImpact = impactMode && p.abone_sayisi == null;
          const nearRight = px > WIDTH - PAD.right - 90;
          const impactText = impactMode
            ? p.abone_sayisi != null
              ? `, ${p.abone_sayisi} abone`
              : ", künye girilmemiş"
            : `, risk ${p.risk_score}`;
          return (
            <g
              key={p.pano_id}
              className={`riskmx-pt${prio ? ` p-${prio}` : ""}${unknownImpact ? " riskmx-pt--kunyesiz" : ""}`}
              role="button"
              tabIndex={0}
              aria-label={`${p.name}${impactText}${
                p.ttl_h != null ? `, sınıra ${Math.round(p.ttl_h)} saat` : ", süre tahmini yok"
              }`}
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
        Gölgeli alan: sınırına yakın ve etkisi yüksek panolar — önce bunlara bakın. Sınıra kalan süre tahmini olmayan
        alarmlar (ör. ark, koruma sağlığı kaybı) "şimdi" ucuna yerleşir.
        {impactMode ? (
          <>
            {" "}
            Dikey eksen <strong>etkilenen abone sayısıdır</strong> (varlık künyesinden, F-21).
            {missing > 0 && (
              <>
                {" "}
                {missing} panonun künyesi CBS'den içe aktarılmadı; bunlar ölçeğe sokulmadan ayrı şeritte
                gösterilir — <em>abonesi yok demek değil, abone sayısı bilinmiyor demektir</em>.
              </>
            )}
          </>
        ) : (
          <>
            {" "}
            Hiçbir panonun künyesi içe aktarılmadığı için dikey eksen hâlâ <strong>risk skorudur</strong>:
            matris bu hâliyle tek boyutludur. Gerçek etki ekseni için varlık künyesi gerekir (F-21).
          </>
        )}
      </p>
    </div>
  );
}
