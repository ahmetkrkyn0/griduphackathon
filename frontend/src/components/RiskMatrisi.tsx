import { useChartWidth } from "../lib/useChartWidth";
import { useState } from "react";
import { Link } from "react-router-dom";
import type { PanelSummary } from "../api/types";
import { etkiEkseni } from "../lib/etki";
import { PRIO_NAME } from "../lib/labels";
import { axisFraction, effectivePrio } from "../lib/worklist";
import { ttlText } from "../lib/format";

const H = 286;
const L = 65,
  R = 36,
  T = 24,
  B = 48;
const ticks = [0, 24, 72, 168, 336];

/**
 * Y ekseni etiketi. Risk modunda degerler zaten tam sayidir ve main'deki ciktinin
 * AYNISI uretilir; etki modunda olcek yarilandiginda (or. max = 3) yuvarlamak etiketi
 * cizginin gercek degerinden KAYDIRIRDI, bu yuzden ondalik korunur.
 */
const yTickLabel = (value: number) =>
  Number.isInteger(value) ? String(value) : value.toFixed(1);

/**
 * Kunyesiz panolarin cizildigi ayri serit (yalnizca etki modunda). Cizim alaninin ALTINDA
 * durur ve kesikli bir cizgiyle ayrilir: "etkisi 0" ile "etkisi bilinmiyor" ayni yere dusmemeli.
 * Serit yokken cizim alani main'deki olcunun (H - T - B) TA KENDISIDIR.
 */
const KUNYESIZ_BAND = 28;

/**
 * Filo ekraninin ikinci gorunumu (Y3): x = sinira kalan sure (log, worklist.ts'teki eksenle
 * ayni olcek), y = risk skoru ya da ETKI. Sol-ust kose en acil + en yuksek deger demektir
 * (x soldan saga zaman arttigi icin).
 * Ilham: Hitachi Lumada APM olasilik x etki risk matrisi (TASARIM-REVIZYONU.md, Y3).
 *
 * SURE TAHMINI OLMAYAN alarmlar (or. ark, koruma sagligi kaybi) eksenin uzerine DEGIL,
 * eksenin solundaki ayri "Tahmin yok" sutununa yerlesir (x = L + 19). Bunlarin bir geri
 * sayimi yoktur; "simdi" noktasina konsalardi olculmus bir sure gibi okunurlardi.
 *
 * ETKI EKSENI — F-21 ile ne degisti
 * Onceki surumde gercek bir etki ekseni **yoktu**: sozlesmede filodaki tum panolar ayni
 * `pano_type` (1600 kVA) oldugu icin kVA sabit bir eksen olurdu, bu yuzden y ekseni **risk
 * skorunun kendisiydi** — yani matris fiilen tek boyutluydu. F-21 varlik kunyesini (CBS'den
 * ice aktarilan `abone_sayisi`) getirdi ve **abone sayisi gercek bir etki eksenidir**:
 * sayilabilir, panodan panoya degisir ve EPDK Kalite Yonetmeligi Madde 8/2 zaten
 * "etkilenen kullanici sayisi"ni istiyor.
 *
 * ITIRAF SILINMEDI, DARALDI. Matris **kunye girildigi olcude** iki boyutludur:
 *   - Hicbir panonun kunyesi yoksa eski davranis **aynen** korunur: y = risk skoru, birim
 *     etiketi "RISK SKORU" ve grafik main'deki geometrisiyle birebir ayni cizilir.
 *   - Kunyesi olmayan panolar, etki modunda **ayri bir seritte** cizilir ve y = 0'a
 *     **konmaz**: "abonesi yok" ile "abone sayisini bilmiyoruz" ayni nokta degildir.
 * Eksenin ne oldugu her iki modda da sol ustteki birim etiketinde YAZILI oldugu icin risk
 * modunda gizlenen bir sey yoktur; ayrica bir itiraf altyazisi cizilmez.
 */
export function RiskMatrisi({ panels }: { panels: PanelSummary[] }) {
  const { ref, width: W } = useChartWidth();
  const [active, setActive] = useState<string | null>(null);

  // Etki ekseni karari saf fonksiyonda (lib/etki.ts) ve testle kilitli.
  const { mode: impactMode, max: maxImpact, missing } = etkiEkseni(panels);
  const showBand = impactMode && missing > 0;

  // Serit yokken plotH === H - T - B ve plotBottom === H - B: main'in geometrisi aynen.
  const plotH = H - T - B - (showBand ? KUNYESIZ_BAND : 0);
  const plotBottom = T + plotH;
  const bandY = plotBottom + KUNYESIZ_BAND / 2;

  const x = (hours: number) => L + 95 + axisFraction(hours) * (W - L - R - 95);
  const yScale = (value: number, max: number) =>
    T + (1 - Math.max(0, Math.min(max, value)) / max) * plotH;
  const y = (p: PanelSummary) =>
    impactMode
      ? p.abone_sayisi != null
        ? yScale(p.abone_sayisi, maxImpact)
        : bandY // kunyesiz: ayri serit, y = 0 DEGIL
      : yScale(p.risk_score, 100);

  const yMax = impactMode ? maxImpact : 100;
  const yTicks = impactMode ? [0, maxImpact / 2, maxImpact] : [0, 25, 50, 75, 100];
  const unitLabel = impactMode ? "ETKİLENEN ABONE SAYISI" : "RİSK SKORU";
  const focused = panels.find((p) => p.pano_id === active);
  return (
    <div className="riskmx" ref={ref}>
      <div className="chart-viewport">
        <svg
          className="chart-svg"
          viewBox={`0 0 ${W} ${H}`}
          role="group"
          aria-label={
            impactMode
              ? "Pano risk dağılımı: düşey etkilenen abone sayısı, yatay sınıra kalan süre. Süre tahmini olmayanlar ayrı sütunda, künyesi içe aktarılmamış panolar ölçeğin altındaki ayrı şeritte gösterilir."
              : "Pano risk dağılımı: düşey risk skoru, yatay sınıra kalan süre. Süre tahmini olmayanlar ayrı sütundadır."
          }
        >
          <rect
            x={L - 19}
            y={T}
            width={77}
            height={H - T - B}
            rx={5}
            fill="#f3f5f7"
          />
          {yTicks.map((n) => (
            <g key={n}>
              <line
                className="chart-grid"
                x1={L - 19}
                x2={W - R}
                y1={yScale(n, yMax)}
                y2={yScale(n, yMax)}
              />
              <text
                className="chart-tick"
                x={L - 28}
                y={yScale(n, yMax) + 4}
                textAnchor="end"
              >
                {yTickLabel(n)}
              </text>
            </g>
          ))}
          {ticks
            .filter((h) => W > 460 || (W < 360 ? [0, 336] : [0, 72, 336]).includes(h))
            .map((h) => (
              <g key={h}>
                <line
                  className="chart-grid"
                  x1={x(h)}
                  x2={x(h)}
                  y1={T}
                  y2={plotBottom}
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
          {showBand && (
            <g>
              {/* Kesikli ayirac: alttaki serit OLCEGIN PARCASI DEGILDIR.
                  `chart-grid` sinifi BILEREK kullanilmiyor: chartsRefinement.css o sinifin
                  stroke-dasharray degerini `none` yapiyor, kesikli cizgi sessizce duz cizgiye
                  donusur ve serit olcegin son dilimi gibi okunurdu. */}
              <line
                className="riskmx-band-sep"
                x1={L - 19}
                x2={W - R}
                y1={plotBottom + 3}
                y2={plotBottom + 3}
                stroke="var(--line)"
                strokeWidth={1}
                strokeDasharray="4 3"
              />
              <text className="chart-tick" x={L - 28} y={bandY - 2} textAnchor="end">
                künye
              </text>
              <text className="chart-tick" x={L - 28} y={bandY + 10} textAnchor="end">
                yok
              </text>
            </g>
          )}
          <text
            className="chart-tick"
            x={L + 19}
            y={H - B + 21}
            textAnchor="middle"
          >
            Tahmin yok
          </text>
          <text className="chart-units" x={L - 19} y={12}>
            {unitLabel}
          </text>
          <text className="chart-units" x={W - R} y={H - 4} textAnchor="end">
            SINIRA KALAN SÜRE · LOG ÖLÇEK
          </text>
          {panels.map((p) => {
            const prio = effectivePrio(p);
            const px = p.ttl_h == null ? L + 19 : x(p.ttl_h);
            const py = y(p);
            const selected = active === p.pano_id;
            const unknownImpact = impactMode && p.abone_sayisi == null;
            const impactText = !impactMode
              ? ""
              : p.abone_sayisi != null
                ? `, ${p.abone_sayisi} abone`
                : ", künye girilmemiş";
            return (
              <Link
                key={p.pano_id}
                to={`/pano/${p.pano_id}`}
                className={`riskmx-pt${prio ? ` p-${prio}` : ""}${
                  unknownImpact ? " riskmx-pt--kunyesiz" : ""
                }`}
                aria-label={`${p.name}, risk ${p.risk_score}${impactText}, ${ttlText(p.ttl_h) || "süre tahmini yok"}`}
                onMouseEnter={() => setActive(p.pano_id)}
                onMouseLeave={() => setActive(null)}
                onFocus={() => setActive(p.pano_id)}
                onBlur={() => setActive(null)}
              >
                <title>
                  {p.name}: risk {p.risk_score}
                  {impactText}, {ttlText(p.ttl_h) || "Süre tahmini yok"}
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
                  r={selected ? 6 : 4.5}
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
      {impactMode && (
        <p className="dim small riskmx-caption">
          Dikey eksen <strong>etkilenen abone sayısıdır</strong> (varlık künyesinden, F-21).
          {missing > 0 && (
            <>
              {" "}
              {missing} panonun künyesi CBS'den içe aktarılmadı; bunlar ölçeğe sokulmadan ayrı
              şeritte gösterilir — <em>abonesi yok demek değil, abone sayısı bilinmiyor demektir</em>.
            </>
          )}
        </p>
      )}
      <div className="risk-footer">
        {focused ? (
          <span>
            <strong>{focused.name}</strong> · Risk {focused.risk_score} ·{" "}
            {impactMode && (
              <>
                {focused.abone_sayisi != null
                  ? `${focused.abone_sayisi} abone`
                  : "Künye içe aktarılmadı"}{" "}
                ·{" "}
              </>
            )}
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
