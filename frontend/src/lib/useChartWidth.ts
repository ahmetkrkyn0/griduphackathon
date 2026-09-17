import { useLayoutEffect, useRef, useState } from "react";
import "../chartsRefinement.css";

/** Keep chart type at its native size instead of scaling labels with the SVG. */
export function useChartWidth() {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(560);
  useLayoutEffect(() => {
    const node = ref.current;
    if (!node) return;
    const update = () => setWidth(Math.max(260, Math.round(node.clientWidth)));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(node);
    return () => observer.disconnect();
  });
  return { ref, width };
}
