import { lazy } from "react";
import { ChartBoundary } from "./ChartBoundary";
import type { Props } from "./SacilimGrafikImpl";
export type { ScatterSeries } from "./SacilimGrafikImpl";
const Chart = lazy(() =>
  import("./SacilimGrafikImpl").then((m) => ({ default: m.SacilimGrafik })),
);
export function SacilimGrafik(props: Props) {
  return (
    <ChartBoundary>
      <Chart {...props} />
    </ChartBoundary>
  );
}
