export type XY = { x: number; y: number };
export type MapPolygon = XY[][];
export type LabelCandidate = XY & { clearance: number; polygon: MapPolygon };

/** Geometry-only work: run once per district, never during a zoom gesture. */
export function prepareLabelCandidates(
  polygons: MapPolygon[],
): LabelCandidate[] {
  const candidates: LabelCandidate[] = [];
  for (const polygon of polygons) {
    const outer = polygon[0];
    const minX = Math.min(...outer.map((p) => p.x)),
      maxX = Math.max(...outer.map((p) => p.x));
    const minY = Math.min(...outer.map((p) => p.y)),
      maxY = Math.max(...outer.map((p) => p.y));
    for (let row = 1; row < 16; row++)
      for (let col = 1; col < 16; col++) {
        const point = {
          x: minX + ((maxX - minX) * col) / 16,
          y: minY + ((maxY - minY) * row) / 16,
        };
        if (!insidePolygons(point, [polygon])) continue;
        let clearance = Infinity;
        for (const ring of polygon)
          for (let i = 0; i < ring.length; i++) {
            clearance = Math.min(
              clearance,
              segmentDistance(point, ring[i], ring[(i + 1) % ring.length]),
            );
          }
        candidates.push({ ...point, clearance, polygon });
      }
  }
  return candidates
    .sort((a, b) => b.clearance - a.clearance)
    .filter(
      (candidate, i, all) =>
        !all
          .slice(0, i)
          .some(
            (previous) =>
              Math.hypot(previous.x - candidate.x, previous.y - candidate.y) <
              2,
          ),
    )
    .slice(0, 32);
}

/** Only test a few prepared positions in map coordinates; don't rescan geometry. */
export function placePreparedLabel(
  candidates: LabelCandidate[],
  width: number,
  height: number,
  scale: number,
  dots: XY[],
): XY | null {
  const boxWidth = (width + 2) / scale,
    boxHeight = (height + 2) / scale;
  for (const candidate of candidates) {
    if (candidate.clearance < boxHeight / 2) continue;
    if (
      dots.some(
        (dot) =>
          Math.abs(dot.x - candidate.x) < (width / 2 + 7) / scale &&
          Math.abs(dot.y - candidate.y) < (height / 2 + 7) / scale,
      )
    )
      continue;
    if (labelFits(candidate, boxWidth, boxHeight, candidate.polygon))
      return { x: candidate.x, y: candidate.y };
  }
  return null;
}

export function normalizeMapSearch(value: string): string {
  return value
    .toLocaleLowerCase("tr-TR")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/ı/g, "i")
    .replace(/\s+/g, "");
}

function inRing(p: XY, ring: XY[]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = ring[i],
      b = ring[j];
    if (
      a.y > p.y !== b.y > p.y &&
      p.x < ((b.x - a.x) * (p.y - a.y)) / (b.y - a.y) + a.x
    )
      inside = !inside;
  }
  return inside;
}

/** Outer rings contain land; inner rings are holes, not extra land. */
export function insidePolygons(p: XY, polygons: MapPolygon[]): boolean {
  return polygons.some(
    ([outer, ...holes]) =>
      inRing(p, outer) && !holes.some((hole) => inRing(p, hole)),
  );
}

function segmentDistance(p: XY, a: XY, b: XY): number {
  const dx = b.x - a.x,
    dy = b.y - a.y;
  const t = Math.max(
    0,
    Math.min(
      1,
      ((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy || 1),
    ),
  );
  return Math.hypot(p.x - a.x - t * dx, p.y - a.y - t * dy);
}

function crossesBox(
  a: XY,
  b: XY,
  left: number,
  top: number,
  right: number,
  bottom: number,
): boolean {
  let start = 0,
    end = 1;
  for (const [origin, delta, min, max] of [
    [a.x, b.x - a.x, left, right],
    [a.y, b.y - a.y, top, bottom],
  ]) {
    if (Math.abs(delta) < 1e-10) {
      if (origin < min || origin > max) return false;
    } else {
      const t0 = (min - origin) / delta,
        t1 = (max - origin) / delta;
      start = Math.max(start, Math.min(t0, t1));
      end = Math.min(end, Math.max(t0, t1));
      if (start > end) return false;
    }
  }
  return true;
}

/** Corners alone miss concavities and holes; reject every crossing boundary too. */
export function labelFits(
  p: XY,
  width: number,
  height: number,
  polygon: MapPolygon,
): boolean {
  const left = p.x - width / 2,
    right = p.x + width / 2;
  const top = p.y - height / 2,
    bottom = p.y + height / 2;
  if (
    ![
      { x: left, y: top },
      { x: right, y: top },
      { x: right, y: bottom },
      { x: left, y: bottom },
    ].every((corner) => insidePolygons(corner, [polygon]))
  )
    return false;
  return !polygon.some((ring) =>
    ring.some((a, i) =>
      crossesBox(a, ring[(i + 1) % ring.length], left, top, right, bottom),
    ),
  );
}

/** Find interior space for the complete label, keeping it away from panel markers.
 * Small districts intentionally defer their labels until the user zooms in. */
export function interiorLabel(
  polygons: MapPolygon[],
  width: number,
  height: number,
  dots: XY[] = [],
): XY | null {
  let best: XY | null = null;
  let bestScore = -Infinity;
  for (const polygon of polygons) {
    const outer = polygon[0];
    const minX = Math.min(...outer.map((p) => p.x)),
      maxX = Math.max(...outer.map((p) => p.x));
    const minY = Math.min(...outer.map((p) => p.y)),
      maxY = Math.max(...outer.map((p) => p.y));
    for (let row = 0; row <= 24; row++)
      for (let col = 0; col <= 24; col++) {
        const p = {
          x: minX + ((maxX - minX) * col) / 24,
          y: minY + ((maxY - minY) * row) / 24,
        };
        if (!insidePolygons(p, [polygon])) continue;
        const clearance = Math.min(
          ...polygon.flatMap((ring) =>
            ring.slice(1).map((b, i) => segmentDistance(p, ring[i], b)),
          ),
        );
        if (
          clearance < height / 2 + 2 ||
          !labelFits(p, width + 4, height + 4, polygon)
        )
          continue;
        if (
          dots.some(
            (d) =>
              Math.abs(d.x - p.x) < width / 2 + 11 &&
              Math.abs(d.y - p.y) < height / 2 + 11,
          )
        )
          continue;
        if (clearance > bestScore) {
          best = p;
          bestScore = clearance;
        }
      }
  }
  return best;
}
