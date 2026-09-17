export function chartTicks(values: number[], includeZero = false): number[] {
  const finite = values.filter(Number.isFinite);
  if (!finite.length) return [0, 0.25, 0.5, 0.75, 1];
  let min = Math.min(...finite),
    max = Math.max(...finite);
  if (includeZero) {
    min = Math.min(0, min);
    max = Math.max(0, max);
  }
  if (min === max) {
    const pad = Math.abs(min) * 0.1 || 1;
    min -= pad;
    max += pad;
  }
  const rough = (max - min) / 4;
  const power = 10 ** Math.floor(Math.log10(rough));
  const step =
    ([1, 2, 2.5, 5, 10].find((n) => n * power >= rough) ?? 10) * power;
  const start = Math.floor(min / step) * step,
    end = Math.ceil(max / step) * step;
  return Array.from({ length: Math.round((end - start) / step) + 1 }, (_, i) =>
    Number((start + i * step).toPrecision(12)),
  );
}

export function linePath(
  points: Array<[number, number | null]>,
  x: (v: number) => number,
  y: (v: number) => number,
): string {
  let drawing = false;
  return points
    .map(([t, v]) => {
      if (v == null || !Number.isFinite(v) || !Number.isFinite(t)) {
        drawing = false;
        return "";
      }
      const command = drawing ? "L" : "M";
      drawing = true;
      return `${command}${x(t).toFixed(2)},${y(v).toFixed(2)}`;
    })
    .join(" ");
}

/** Nearest sample is returned as-is, including missing data, without interpolating measurements. */
export function nearestSample(
  points: Array<[number, number | null]>,
  time: number,
): [number, number | null] | null {
  if (!points.length) return null;
  return points.reduce((best, p) =>
    Math.abs(p[0] - time) < Math.abs(best[0] - time) ? p : best,
  );
}
