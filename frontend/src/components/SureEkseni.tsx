import { Link } from "react-router-dom";
import type { PanelSummary } from "../api/types";
import { ttlText } from "../lib/format";
import { effectivePrio } from "../lib/worklist";
export function SureEkseni({ worklist }: { worklist: PanelSummary[] }) {
  const lanes = [
    {
      name: "Süre tahmini yok",
      sub: "Alarm nedenini inceleyin",
      points: worklist.filter((p) => p.ttl_h == null),
    },
    {
      name: "İlk 72 saat",
      sub: "Yakın dönem",
      points: worklist.filter((p) => p.ttl_h != null && p.ttl_h <= 72),
    },
    {
      name: "3–7 gün",
      sub: "Bakım planlaması",
      points: worklist.filter(
        (p) => p.ttl_h != null && p.ttl_h > 72 && p.ttl_h <= 168,
      ),
    },
    {
      name: "7 gün ve sonrası",
      sub: "İzleme",
      points: worklist.filter((p) => p.ttl_h != null && p.ttl_h > 168),
    },
  ];
  return (
    <div
      className="schedule-lanes"
      role="group"
      aria-label="Tahmini sınıra kalan süreye göre panolar"
    >
      {lanes.map((lane) => (
        <div className="schedule-lane" key={lane.name}>
          <div>
            <strong>{lane.name}</strong>
            <small>{lane.sub}</small>
          </div>
          <div>
            {lane.points.map((p) => (
              <Link
                key={p.pano_id}
                to={`/pano/${p.pano_id}`}
                style={{
                  borderLeftColor: `var(--${effectivePrio(p)?.toLowerCase() ?? "dot"})`,
                }}
              >
                <span>{p.name}</span>
                <small>{ttlText(p.ttl_h) || "Tahmin yok"}</small>
              </Link>
            ))}
            {!lane.points.length && (
              <span className="dim small">Bu aralıkta pano yok</span>
            )}
          </div>
        </div>
      ))}
      <p className="dim small">
        Gösterilen süreler arıza zamanı değil, izlenen sınıra ilişkin
        tahminlerdir.
      </p>
    </div>
  );
}
