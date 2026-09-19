export type Sample = [number, number | null];
export type SpatialSample = [number, number, number, number];
/** Only simultaneous, finite measurements; never interpolate missing evidence. */
export function joinSpatial(
  current: Sample[],
  delta: Sample[],
  ratio: Sample[],
): SpatialSample[] {
  const d = new Map(delta),
    k = new Map(ratio);
  return current
    .flatMap(([t, i]) => {
      const dv = d.get(t),
        kv = k.get(t);
      return Number.isFinite(t) &&
        i != null &&
        Number.isFinite(i) &&
        dv != null &&
        Number.isFinite(dv) &&
        kv != null &&
        Number.isFinite(kv)
        ? [[i, dv, kv, t] as SpatialSample]
        : [];
    })
    .sort((a, b) => a[3] - b[3]);
}
export function linearFit(points: Array<[number, number]>) {
  const finite = points.filter((p) => p.every(Number.isFinite));
  if (finite.length < 2) return null;
  const mx = finite.reduce((s, p) => s + p[0], 0) / finite.length;
  const my = finite.reduce((s, p) => s + p[1], 0) / finite.length;
  const denominator = finite.reduce((s, p) => s + (p[0] - mx) ** 2, 0);
  if (denominator < 1e-9) return null;
  const m =
    finite.reduce((s, p) => s + (p[0] - mx) * (p[1] - my), 0) / denominator;
  return { m, b: my - m * mx };
}
