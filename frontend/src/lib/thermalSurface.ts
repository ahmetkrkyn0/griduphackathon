import type { SpatialSample } from "./analysisData";

/** Illustrative steady-state fit: ΔT = K₀ × (K/K₀) × I². Not a forecast. */
export function thermalSurface(points: SpatialSample[]) {
  const valid = points.filter(
    ([i, dt, ratio]) =>
      i > 0 && dt >= 0 && ratio > 0 && [i, dt, ratio].every(Number.isFinite),
  );
  if (valid.length < 3) return null;
  const coefficients = valid
    .map(([i, dt, ratio]) => dt / (i * i * ratio))
    .sort((a, b) => a - b);
  const k0 = coefficients[Math.floor(coefficients.length / 2)];
  const currents = valid.map((p) => p[0]),
    ratios = valid.map((p) => p[2]);
  const minI = Math.min(...currents),
    maxI = Math.max(...currents);
  const minK = Math.min(...ratios),
    maxK = Math.max(...ratios);
  if (maxI === minI || maxK === minK || k0 <= 0) return null;
  const data: [number, number, number][] = [];
  for (let y = 0; y <= 24; y++)
    for (let x = 0; x <= 32; x++) {
      const i = minI + ((maxI - minI) * x) / 32,
        ratio = minK + ((maxK - minK) * y) / 24;
      data.push([i, ratio, k0 * ratio * i * i]);
    }
  return { data, k0, max: Math.max(...data.map((p) => p[2])) };
}
