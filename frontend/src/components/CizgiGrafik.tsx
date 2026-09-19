import { lazy } from "react";
import { ChartBoundary } from "./ChartBoundary";
import type { Props } from "./CizgiGrafikImpl";
export type { ChartMarker, ChartSeries } from "./CizgiGrafikImpl";
const Chart = lazy(() =>
  import("./CizgiGrafikImpl").then((m) => ({ default: m.CizgiGrafik })),
);
export function CizgiGrafik(props: Props) {
  return (
    <ChartBoundary>
      <Chart {...props} />
    </ChartBoundary>
  );
}
