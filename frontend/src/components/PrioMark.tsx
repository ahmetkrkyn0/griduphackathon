import type { Prio } from "../api/types";
import { PRIO_NAME } from "../lib/labels";

const GLYPH: Record<Prio, string> = { P1: "1", P2: "2", P3: "3", SYS: "S", INFO: "i" };

interface Props {
  prio: Prio;
  acked?: boolean;
  small?: boolean;
}

/** ISA-101 tarzi oncelik isareti: renk + sekil + karakter; renk korlugunde de ayirt edilir. */
export function PrioMark({ prio, acked = false, small = false }: Props) {
  const label = acked ? `${PRIO_NAME[prio]}, onaylandı` : PRIO_NAME[prio];
  const className = ["prio", `prio-${prio}`, acked && "acked", small && "small"].filter(Boolean).join(" ");
  return (
    <span className={className} role="img" aria-label={label} title={label}>
      {GLYPH[prio]}
    </span>
  );
}
