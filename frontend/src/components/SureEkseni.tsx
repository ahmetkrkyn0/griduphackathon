import { useEffect, useRef, useState, type CSSProperties, type RefObject } from "react";
import { Link } from "react-router-dom";
import type { PanelSummary } from "../api/types";
import { ttlText } from "../lib/format";
import { AXIS_HOURS, axisFraction, effectivePrio, layoutAxisRows, panelHeadline } from "../lib/worklist";
import { PrioMark } from "./PrioMark";

const TICKS: Array<[number, string]> = [
  [0, "bugün"],
  [24, "1 gün"],
  [72, "3 gün"],
  [168, "7 gün"],
  [AXIS_HOURS, "14 gün"],
];
const NOW_SLOTS = 2;

// app.css .axis ile ayni olculer: tek kaynak burasi, CSS degiskeni olarak aktarilir.
const START_PX = 290;
const END_PAD_PX = 236;
const CARD_PX = 236;
const ROWS = 3;

function useElementWidth(ref: RefObject<HTMLElement>): number {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(element);
    return () => observer.disconnect();
  }, [ref]);
  return width;
}

function Pin({ panel }: { panel: PanelSummary }) {
  const prio = effectivePrio(panel);
  const ttl = ttlText(panel.ttl_h);
  return (
    <Link to={`/pano/${panel.pano_id}`} className="pin">
      {prio && <PrioMark prio={prio} />}
      <span className="pin-card">
        <span className="pin-name">
          <span>{panel.name}</span>
          {ttl && <span className="pin-ttl">{ttl}</span>}
        </span>
        <span className="pin-head">{panelHeadline(panel)}</span>
      </span>
    </Link>
  );
}

/** Acilis ekraninin ana ogesi: panolar sorunun ne zaman kritiklesecegine gore dizilir. */
export function SureEkseni({ worklist }: { worklist: PanelSummary[] }) {
  const trackRef = useRef<HTMLDivElement>(null);
  const trackPx = useElementWidth(trackRef);

  const now = worklist.filter((p) => p.ttl_h == null);
  const timed = worklist
    .filter((p) => p.ttl_h != null && p.ttl_h <= AXIS_HOURS)
    .sort((a, b) => (a.ttl_h ?? 0) - (b.ttl_h ?? 0));
  const rows = layoutAxisRows(
    timed.map((p) => axisFraction(p.ttl_h ?? 0)),
    { trackPx, startPx: START_PX, endPadPx: END_PAD_PX, cardPx: CARD_PX, rows: ROWS },
  );

  const trackStyle = { "--x0": `${START_PX}px`, "--xr": `${END_PAD_PX}px` } as CSSProperties;
  const at = (hours: number, row = 0) => ({ "--f": axisFraction(hours), "--row": row }) as CSSProperties;

  return (
    <div ref={trackRef} className="axis" style={trackStyle} role="group" aria-label="Sınıra kalan süre ekseni">
      <div className="axis-now">
        <span className="axis-now-title">Şimdi</span>
        {now.slice(0, NOW_SLOTS).map((p) => (
          <Pin key={p.pano_id} panel={p} />
        ))}
        {now.length > NOW_SLOTS && (
          <a className="axis-more" href="#yapilacaklar">
            ve {now.length - NOW_SLOTS} pano daha
          </a>
        )}
        {now.length === 0 && <span className="axis-more">Şu an acil pano yok</span>}
      </div>

      <div className="axis-line" aria-hidden="true" />
      {TICKS.map(([hours, label]) => (
        <span key={hours} className="axis-tick" style={at(hours)} aria-hidden="true">
          <span>{label}</span>
        </span>
      ))}

      {timed.map((p, i) => (
        <div key={p.pano_id} className="axis-item" style={at(p.ttl_h ?? 0, rows[i])}>
          <span className="axis-stem" aria-hidden="true" />
          <Pin panel={p} />
        </div>
      ))}
    </div>
  );
}
