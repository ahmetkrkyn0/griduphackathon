import { useId, type KeyboardEvent } from "react";
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
export function OnGorunus({
  points,
  selected = null,
  onSelect,
  ackedPoints,
  tvoc,
}: Props) {
  const id = useId();
  const choose = (pt: string) => onSelect?.(pt);
  const onKey = (event: KeyboardEvent, pt: string) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      choose(pt);
    }
  };

  return (
    <svg
      className="og"
      viewBox={`-95 -100 ${W + 190} ${H + 215}`}
      role="group"
      aria-label="Panonun ön görünüşü ve ölçüm noktaları"
    >
      <defs>
        <linearGradient id={`${id}-metal`} x2="1" y2=".3">
          <stop stopColor="#c0c7ca" />
          <stop offset=".18" stopColor="#f1f3f3" />
          <stop offset=".65" stopColor="#d4dadd" />
          <stop offset="1" stopColor="#a6afb5" />
        </linearGradient>
        <linearGradient id={`${id}-copper`} x2="0" y2="1">
          <stop stopColor="#ba865b" />
          <stop offset=".4" stopColor="#ebc5a1" />
          <stop offset=".55" stopColor="#b98056" />
          <stop offset="1" stopColor="#865239" />
        </linearGradient>
        <linearGradient id={`${id}-device`}>
          <stop stopColor="#333d45" />
          <stop offset=".45" stopColor="#657079" />
          <stop offset="1" stopColor="#30383e" />
        </linearGradient>
        <pattern
          id={`${id}-plate`}
          width="60"
          height="60"
          patternUnits="userSpaceOnUse"
        >
          <rect width="60" height="60" fill="#dee3e5" />
          <circle cx="30" cy="30" r="2" fill="#bdc6ca" />
        </pattern>
        <filter
          id={`${id}-shadow`}
          x="-10%"
          y="-10%"
          width="125%"
          height="130%"
        >
          <feDropShadow
            dx="7"
            dy="12"
            stdDeviation="8"
            floodColor="#263744"
            floodOpacity=".2"
          />
        </filter>
      </defs>
      <rect
        x={-22}
        y={-22}
        width={W + 44}
        height={H + 44}
        rx={9}
        fill={`url(#${id}-metal)`}
        stroke="#9ca7ae"
        strokeWidth={3}
        filter={`url(#${id}-shadow)`}
      />
      <rect
        x={14}
        y={14}
        width={W - 28}
        height={H - 28}
        fill={`url(#${id}-plate)`}
        stroke="#8f9ca5"
        strokeWidth={5}
      />
      <rect
        className="og-zone"
        x={0}
        y={0}
        width={W}
        height={ZONE_Y.topCompartmentEnd}
      />
      <rect
        className="og-zone"
        x={0}
        y={ZONE_Y.cableZoneStart}
        width={W}
        height={H - ZONE_Y.cableZoneStart}
      />
      <line
        className="og-rule"
        x1={0}
        y1={ZONE_Y.topCompartmentEnd}
        x2={W}
        y2={ZONE_Y.topCompartmentEnd}
      />
      <line
        className="og-rule dash"
        x1={0}
        y1={ZONE_Y.cableZoneStart}
        x2={W}
        y2={ZONE_Y.cableZoneStart}
      />
      {[24, W - 24].map((x) => (
        <g key={x}>
          {[30, 325, 760, 1125, H - 25].map((y) => (
            <g key={y}>
              <circle
                cx={x}
                cy={y}
                r={8}
                fill="#87949c"
                stroke="#edf0f2"
                strokeWidth={3}
              />
              <path
                d={`M${x - 4},${y}h8 M${x},${y - 4}v8`}
                stroke="#44535d"
                strokeWidth={2}
              />
            </g>
          ))}
        </g>
      ))}
      <text x={54} y={72} fontSize={25} fill="#53636c" letterSpacing={3}>
        AG DAĞITIM PANOSU
      </text>
      <rect x={54} y={88} width={205} height={25} rx={3} fill="#5d6b73" />
      <text x={66} y={106} fontSize={15} fill="white" letterSpacing={2}>
        İÇ YERLEŞİM / ÖN
      </text>
      <path
        d="M1320 84h-170v210H70"
        fill="none"
        stroke="#606e77"
        strokeWidth={8}
      />
      {[0, 1, 2, 3].map((i) => (
        <path
          key={i}
          d={`M${315 + i * 110} 253v${28 + i * 7}h${200 - i * 25}`}
          fill="none"
          stroke={i % 2 ? "#718187" : "#384953"}
          strokeWidth={4}
        />
      ))}

      {/* Ust bolme (sartname 2.2.8.1.iv): DIN ray, TVOC-2, Pano Beyni, modem, sigortalar, kompanzasyon */}
      <line className="og-rail" x1={60} y1={205} x2={W - 60} y2={205} />
      <line className="og-rail-lip" x1={60} y1={199} x2={W - 60} y2={199} />
      <rect className="og-dev" x={90} y={158} width={120} height={94} rx={6}>
        <title>TVOC-2 ark koruma</title>
      </rect>
      {/* HMI dokunmatik ekran: govdenin cogunu kaplayan tek parca ekran (buton yok — dokunmatik). */}
      <rect
        className="og-screen-bezel"
        x={98}
        y={166}
        width={90}
        height={62}
        rx={3}
      />
      <rect
        className="og-screen"
        x={101}
        y={169}
        width={84}
        height={56}
        rx={2}
      />
      <circle
        className={`og-led ${tvoc?.prot_health_ok === false ? "bad" : "ok"}`}
        cx={185}
        cy={172}
        r={5}
      />
      <rect className="og-ours" x={240} y={150} width={170} height={110} rx={8}>
        <title>Pano Beyni</title>
      </rect>
      <circle className="og-led ok" cx={335} cy={164} r={5} />
      <rect
        className="og-dev faint"
        x={440}
        y={160}
        width={120}
        height={90}
        rx={6}
      >
        <title>Modem</title>
      </rect>
      <circle className="og-led ok" cx={535} cy={174} r={4.5} />
      {[0, 1, 2, 3, 4].map((i) => (
        <rect
          key={i}
          className="og-dev fainter"
          x={610 + i * 42}
          y={172}
          width={30}
          height={66}
          rx={3}
        />
      ))}
      {[0, 1, 2].map((i) => {
        const cx = 1010 + i * 105;
        return (
          <g key={i}>
            <rect
              x={cx - 40}
              y={145}
              width={80}
              height={130}
              rx={8}
              fill={`url(#${id}-device)`}
              stroke="#252f34"
              strokeWidth={2}
            />
            <ellipse
              cx={cx}
              cy={145}
              rx={40}
              ry={13}
              fill="#b7c0c4"
              stroke="#63737d"
              strokeWidth={2}
            />
            <rect
              x={cx - 23}
              y={184}
              width={46}
              height={35}
              rx={2}
              fill="#d6dddf"
            />
            <text
              x={cx}
              y={208}
              textAnchor="middle"
              fontSize={13}
              fill="#4f5e67"
            >
              CAP
            </text>
            <rect x={cx - 4} y={128} width={8} height={18} fill="#ac8054" />
            {/* Basinc tahliye izi: gercek guc kondansatorlerinin ust yuzeyindeki cizik desen. */}
            {[0, 120, 240].map((deg) => (
              <line
                key={deg}
                className="og-comp-vent"
                x1={cx}
                y1={145}
                x2={cx + 22 * Math.cos((deg * Math.PI) / 180)}
                y2={145 + 7 * Math.sin((deg * Math.PI) / 180)}
              />
            ))}
          </g>
        );
      })}
      {/* ENTES MPR-53CS-DIN/96: dogrulanmis 96x96mm DIN panel format (urun sayfasi) —
          LCD + 4 gezinme tusu, 3D ikizle es (TASARIM-REVIZYONU.md §15). */}
      <rect className="og-dev" x={1440} y={160} width={96} height={94} rx={4}>
        <title>MPR-53CS şebeke analizörü</title>
      </rect>
      <rect
        className="og-screen-bezel"
        x={1449}
        y={168}
        width={70}
        height={46}
        rx={2}
      />
      <rect className="og-screen" x={1452} y={171} width={64} height={40} />
      {[0, 1, 2, 3].map((i) => (
        <rect
          key={i}
          className="og-screen-btn"
          x={1449 + i * 12}
          y={222}
          width={8}
          height={8}
          rx={1}
        />
      ))}

      {/* Ana baralar ve ustten gelen giris baralari */}
      {PHASES.map((phase, i) => (
        <g key={phase}>
          <rect
            x={40}
            y={BAR_Y[phase] - 44}
            width={W - 80}
            height={88}
            rx={3}
            fill={`url(#${id}-copper)`}
            stroke="#a6744d"
            strokeWidth={2}
          />
          <rect
            x={girisX((i + 1) as 1 | 2 | 3) - 21}
            y={0}
            width={42}
            height={BAR_Y[phase]}
            fill={`url(#${id}-copper)`}
            stroke="#a6744d"
            strokeWidth={2}
          />
          <rect
            x={1210}
            y={BAR_Y[phase] - 15}
            width={47}
            height={30}
            rx={3}
            fill="#e7e9e8"
          />
          <text
            x={1233}
            y={BAR_Y[phase] + 7}
            fontSize={21}
            textAnchor="middle"
            fill="#34454e"
          >
            {phase}
          </text>
        </g>
      ))}
      <rect
        className="og-bar faint"
        x={40}
        y={N_BAR_Y - 8}
        width={W - 80}
        height={16}
        rx={3}
      />
      <rect
        className="og-bar faint"
        x={GIRIS_N_X - 8}
        y={0}
        width={16}
        height={N_BAR_Y}
      />

      {/* DSYA seritleri ve kablolar */}
      {DSYA_NUMBERS.map((n) => {
        const x = dsyaX(n);
        const spare = n >= FIRST_SPARE_DSYA;
        return (
          <g key={n}>
            <rect
              className={spare ? "og-dsya spare" : "og-dsya"}
              x={x - 50}
              y={420}
              width={100}
              height={620}
              rx={10}
            />
            {PHASES.map((phase) => (
              <g key={phase}>
                <rect
                  x={x - 40}
                  y={BAR_Y[phase] - 64}
                  width={80}
                  height={126}
                  rx={5}
                  fill={spare ? "#cbd2d6" : "#bdc6cb"}
                  stroke="#80909a"
                  strokeWidth={2}
                />
                {!spare && (
                  <>
                    <rect
                      x={x - 26}
                      y={BAR_Y[phase] - 43}
                      width={52}
                      height={85}
                      rx={3}
                      fill="#eff0eb"
                      stroke="#87959b"
                      strokeWidth={3}
                    />
                    <rect
                      x={x - 30}
                      y={BAR_Y[phase] - 48}
                      width={60}
                      height={15}
                      rx={2}
                      fill="#798b96"
                    />
                    <rect
                      x={x - 30}
                      y={BAR_Y[phase] + 30}
                      width={60}
                      height={15}
                      rx={2}
                      fill="#798b96"
                    />
                    <rect
                      x={x - 7}
                      y={BAR_Y[phase] - 18}
                      width={14}
                      height={35}
                      rx={2}
                      fill="#303f48"
                    />
                  </>
                )}
              </g>
            ))}
            {!spare && (
              <>
                {/* Sigorta tutamagi: DSYA bir MCB degil, NH bicak sigortali yuk ayiricidir —
                    arastirma sonrasi duzeltildi (Etien DSYA urun sayfasi, TASARIM-REVIZYONU.md §15). */}
                <circle className="og-fusecap" cx={x} cy={470} r={16} />
                <circle className="og-fusecap-hi" cx={x - 5} cy={465} r={4} />
              </>
            )}
            <text className="og-label" x={x} y={405} textAnchor="middle">
              {spare ? `${n} yedek` : `DSYA-${n}`}
            </text>
            {!spare &&
              [-1, 0, 1].map((offset) => (
                <g key={offset}>
                  <path
                    d={`M${x + offset * 30} ${TERMINAL_Y} C${x + offset * 33} 1210 ${x + offset * 43} 1330 ${x + offset * 33} ${H - 20}`}
                    stroke="#34404a"
                    strokeWidth={18}
                    fill="none"
                  />
                  <rect
                    x={x + offset * 30 - 10}
                    y={TERMINAL_Y - 25}
                    width={20}
                    height={55}
                    rx={3}
                    fill={`url(#${id}-copper)`}
                  />
                  <circle
                    cx={x + offset * 30}
                    cy={TERMINAL_Y - 10}
                    r={6}
                    fill="#9caab3"
                  />
                </g>
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
            <title>{`${label}: ${num(p.t_c)} °C · ${STATE_TEXT[state]}`}</title>
            <circle className="og-hit" cx={pos.x} cy={pos.y} r={18} />
            {state !== "normal" &&
              state !== "stale" &&
              !ackedPoints?.has(p.pt) && (
                <circle className="og-halo" cx={pos.x} cy={pos.y} r={46} />
              )}
            {isSelected && (
              <circle className="og-sel" cx={pos.x} cy={pos.y} r={30} />
            )}
            <circle className="og-dot" cx={pos.x} cy={pos.y} r={15} />
          </g>
        );
      })}
      <g aria-hidden="true">
        <path
          d={`M0 ${H + 62}h${W} M0 ${H + 47}v30 M${W} ${H + 47}v30`}
          stroke="#8b9ca8"
          strokeWidth={2}
        />
        <text
          x={W / 2}
          y={H + 90}
          textAnchor="middle"
          fontSize={22}
          fill="#60727e"
        >
          1600 mm · Temsili yerleşim
        </text>
      </g>
    </svg>
  );
}
