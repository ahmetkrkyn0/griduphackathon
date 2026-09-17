type Point = { x: number; y: number; text: string };
export type MapLabel = { x: number; y: number; width: number; height: number; anchorX: number; anchorY: number };

function distanceToLine(p: Point, start: Point, x: number, y: number): number {
  const dx = x - start.x, dy = y - start.y;
  const t = Math.max(0, Math.min(1, ((p.x - start.x) * dx + (p.y - start.y) * dy) / (dx * dx + dy * dy || 1)));
  return Math.hypot(p.x - start.x - t * dx, p.y - start.y - t * dy);
}

/** Layout in viewport units so zoom uses the same spacing as the rendered labels. */
export function layoutMapLabels(points: Point[], width: number, height: number): MapLabel[] {
  const placed: MapLabel[] = [];
  return points.map((point) => {
    const w = point.text.length * 6.8 + 16;
    const h = 22;
    let best: MapLabel | undefined;
    let bestScore = Infinity;
    for (const gap of [16, 30, 46, 66, 90, 120]) {
      for (const [dx, dy] of [[w / 2 + gap, 0], [-w / 2 - gap, 0], [0, -h / 2 - gap], [0, h / 2 + gap], [w / 2 + gap, -h - gap], [-w / 2 - gap, -h - gap], [w / 2 + gap, h + gap], [-w / 2 - gap, h + gap]]) {
        const x = Math.max(8, Math.min(width - w - 8, point.x + dx - w / 2));
        const y = Math.max(8, Math.min(height - h - 8, point.y + dy - h / 2));
        const anchorX = Math.max(x, Math.min(x + w, point.x));
        const anchorY = Math.max(y, Math.min(y + h, point.y));
        const overlaps = placed.filter((b) => x < b.x + b.width + 5 && x + w + 5 > b.x && y < b.y + b.height + 5 && y + h + 5 > b.y).length;
        const coversDots = points.filter((p) => p.x > x - 12 && p.x < x + w + 12 && p.y > y - 12 && p.y < y + h + 12).length;
        const crossesDots = points.filter((p) => p !== point && distanceToLine(p, point, anchorX, anchorY) < 10).length;
        const score = overlaps * 10000 + coversDots * 10000 + crossesDots * 250 + Math.hypot(anchorX - point.x, anchorY - point.y);
        if (score < bestScore) {
          bestScore = score;
          best = { x, y, width: w, height: h, anchorX, anchorY };
        }
      }
    }
    placed.push(best!);
    return best!;
  });
}
