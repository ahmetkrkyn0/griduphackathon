import type { KeyboardEvent } from "react";
import type { ConnPoint, Tvoc } from "../api/types";
import { num } from "../lib/format";
import { STATE_TEXT, pointLabel } from "../lib/labels";
import {
  BAR_Y,
  DSYA_COUNT,
  FIRST_SPARE_DSYA,
  GIRIS_N_X,
  N_BAR_Y,
  PANEL_MM,
  TERMINAL_Y,
  ZONE_Y,
  dsyaX,
  girisX,
  pointPos,
} from "../lib/panelGeometry";

interface Props {
  points: ConnPoint[];
  selected?: string | null;
  onSelect?: (pt: string) => void;
  /** Onaylanmis alarma bagli noktalar: halka animasyonu durur (Y6, calm technology). */
  ackedPoints?: ReadonlySet<string>;
  /** TVOC-2 govde LED'i icin — 3D ikizdeki ayni detayin 2D karsiligi (kural 10 ile catismaz). */
  tvoc?: Tvoc | null;
}

const { width: W, height: H } = PANEL_MM;
const PHASES = ["L1", "L2", "L3"] as const;
const DSYA_NUMBERS = Array.from({ length: DSYA_COUNT }, (_, i) => i + 1);

/** EK-II/14 olculerine gore 2D on gorunus. Nokta rengi yalnizca API'nin ConnPoint.state alanindan gelir.
 *  Gercekcilik detaylari (3D ikizle es duzeyde, TASARIM-REVIZYONU.md §14): govde LED'leri, devre
 *  kesici anahtar kollari, kondansator basinc tahliye izi, DIN ray'de ince bir on/arka ayrimi.
 *  Hepsi dekoratif — tek istisna TVOC-2 LED'i, API'nin tvoc.prot_health_ok alanini yansitir. */
export function OnGorunus({ points, selected = null, onSelect, ackedPoints, tvoc }: Props) {
  const choose = (pt: string) => onSelect?.(pt);
  const onKey = (event: KeyboardEvent, pt: string) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      choose(pt);
    }
  };

  return (
    <svg className="og" viewBox={`-30 -30 ${W + 60} ${H + 60}`} role="group" aria-label="Panonun ön görünüşü ve ölçüm noktaları">
      <rect className="og-enc" x={0} y={0} width={W} height={H} rx={6} />
      <rect className="og-zone" x={0} y={0} width={W} height={ZONE_Y.topCompartmentEnd} />
      <rect className="og-zone" x={0} y={ZONE_Y.cableZoneStart} width={W} height={H - ZONE_Y.cableZoneStart} />
      <line className="og-rule" x1={0} y1={ZONE_Y.topCompartmentEnd} x2={W} y2={ZONE_Y.topCompartmentEnd} />
      <line className="og-rule dash" x1={0} y1={ZONE_Y.cableZoneStart} x2={W} y2={ZONE_Y.cableZoneStart} />

      {/* Ust bolme (sartname 2.2.8.1.iv): DIN ray, TVOC-2, Pano Beyni, modem, sigortalar, kompanzasyon */}
      <line className="og-rail" x1={60} y1={205} x2={W - 60} y2={205} />
      <line className="og-rail-lip" x1={60} y1={199} x2={W - 60} y2={199} />
      <rect className="og-dev" x={90} y={158} width={120} height={94} rx={6}>
        <title>TVOC-2 ark koruma</title>
      </rect>
      <circle className={`og-led ${tvoc?.prot_health_ok === false ? "bad" : "ok"}`} cx={185} cy={172} r={5} />
      <rect className="og-ours" x={240} y={150} width={170} height={110} rx={8}>
        <title>Pano Beyni</title>
      </rect>
      <circle className="og-led ok" cx={335} cy={164} r={5} />
      <rect className="og-dev faint" x={440} y={160} width={120} height={90} rx={6}>
        <title>Modem</title>
      </rect>
      <circle className="og-led ok" cx={535} cy={174} r={4.5} />
      {[0, 1, 2, 3, 4].map((i) => (
        <rect key={i} className="og-dev fainter" x={610 + i * 42} y={172} width={30} height={66} rx={3} />
      ))}
      {[0, 1, 2].map((i) => {
        const cx = 1010 + i * 105;
        return (
          <g key={i}>
            <circle className="og-comp" cx={cx} cy={205} r={42} />
            {/* Basinc tahliye izi: gercek guc kondansatorlerinin ust yuzeyindeki cizik desen. */}
            {[0, 120, 240].map((deg) => (
              <line
                key={deg}
                className="og-comp-vent"
                x1={cx}
                y1={205}
                x2={cx + 22 * Math.cos((deg * Math.PI) / 180)}
                y2={205 + 22 * Math.sin((deg * Math.PI) / 180)}
              />
            ))}
          </g>
        );
      })}

      {/* Ana baralar ve ustten gelen giris baralari */}
      {PHASES.map((phase, i) => (
        <g key={phase}>
          <rect className="og-bar" x={40} y={BAR_Y[phase] - 10} width={W - 80} height={20} rx={3} />
          <rect className="og-bar" x={girisX((i + 1) as 1 | 2 | 3) - 10} y={0} width={20} height={BAR_Y[phase]} />
        </g>
      ))}
      <rect className="og-bar faint" x={40} y={N_BAR_Y - 8} width={W - 80} height={16} rx={3} />
      <rect className="og-bar faint" x={GIRIS_N_X - 8} y={0} width={16} height={N_BAR_Y} />

      {/* DSYA seritleri ve kablolar */}
      {DSYA_NUMBERS.map((n) => {
        const x = dsyaX(n);
        const spare = n >= FIRST_SPARE_DSYA;
        return (
          <g key={n}>
            <rect className={spare ? "og-dsya spare" : "og-dsya"} x={x - 50} y={420} width={100} height={620} rx={10} />
            {!spare && (
              <>
                {/* Devre kesici anahtar kolu + acik/kapali penceresi — 3D ikizdeki ayni detay. */}
                <rect className="og-toggle" x={x - 15} y={445} width={30} height={42} rx={3} />
                <rect className="og-toggle-window" x={x - 12} y={500} width={24} height={14} rx={2} />
              </>
            )}
            <text className="og-label" x={x} y={405} textAnchor="middle">
              {spare ? `${n} yedek` : `DSYA-${n}`}
            </text>
            {!spare &&
              [-1, 0, 1].map((offset) => (
                <line key={offset} className="og-cable" x1={x + offset * 30} y1={TERMINAL_Y} x2={x + offset * 30} y2={H} />
              ))}
          </g>
        );
      })}

      {/* Olcum noktalari */}
      {points.map((p) => {
        const pos = pointPos(p.pt);
        if (!pos) return null;
        const state = p.state ?? "normal";
        const isSelected = p.pt === selected;
        const label = p.label ?? pointLabel(p.pt);
        return (
          <g
            key={p.pt}
            className={`og-pt st-${state}`}
            role="button"
            tabIndex={0}
            aria-pressed={isSelected}
            aria-label={`${label}: ${num(p.t_c)} °C, ${STATE_TEXT[state]}`}
            onClick={() => choose(p.pt)}
            onKeyDown={(event) => onKey(event, p.pt)}
          >
            <circle className="og-hit" cx={pos.x} cy={pos.y} r={18} />
            {state !== "normal" && state !== "stale" && !ackedPoints?.has(p.pt) && (
              <circle className="og-halo" cx={pos.x} cy={pos.y} r={46} />
            )}
            {isSelected && <circle className="og-sel" cx={pos.x} cy={pos.y} r={30} />}
            <circle className="og-dot" cx={pos.x} cy={pos.y} r={15} />
          </g>
        );
      })}
    </svg>
  );
}
