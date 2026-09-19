import { Link } from "react-router-dom";
import type { PanelSummary } from "../api/types";
import { ttlText } from "../lib/format";
import { axisFraction, effectivePrio } from "../lib/worklist";
export function SureEkseni({ worklist }: { worklist: PanelSummary[] }) {
  const known = worklist
    .filter((p) => p.ttl_h != null && Number.isFinite(p.ttl_h))
    .sort((a, b) => a.ttl_h! - b.ttl_h!);
  const unknown = worklist.filter(
    (p) => p.ttl_h == null || !Number.isFinite(p.ttl_h),
  );
  return (
    <div className="planning-chart">
      <div className="planning-heading">
        <span>BAKIM UFUKLARI</span>
        <strong>
          {known.length} süre tahmini · {unknown.length} değerlendirme bekleyen
        </strong>
      </div>
      <div className="planning-axis">
        <span>Pano</span>
        <div>
          {[0, 72, 168, 336].map((h) => (
            <span key={h} style={{ left: `${axisFraction(h) * 100}%` }}>
              {h === 0 ? "Şimdi" : `${h / 24} gün`}
            </span>
          ))}
        </div>
        <span>Kalan süre</span>
      </div>
      {known.map((p) => (
        <Link
          className="planning-row"
          key={p.pano_id}
          to={`/pano/${p.pano_id}`}
        >
          <span>
            {p.name}
            <small>Risk {p.risk_score} / 100</small>
          </span>
          <div className="planning-track">
            <i
              style={{
                width: `${Math.max(2, axisFraction(p.ttl_h!) * 100)}%`,
                background: `var(--${effectivePrio(p)?.toLowerCase() ?? "dot"})`,
              }}
            />
            <b
              style={{
                left: `${Math.min(98, Math.max(2, axisFraction(p.ttl_h!) * 100))}%`,
              }}
            />
          </div>
          <strong>{ttlText(p.ttl_h)}</strong>
        </Link>
      ))}
      {!known.length && <p className="empty">Bu seçimde süre tahmini yok.</p>}
      <div className="planning-unknown">
        <span>Süre tahmini olmayanlar</span>
        <div>
          {unknown.map((p) => (
            <Link to={`/pano/${p.pano_id}`} key={p.pano_id}>
              <i
                style={{
                  background: `var(--${effectivePrio(p)?.toLowerCase() ?? "dot"})`,
                }}
              />
              {p.name}
            </Link>
          ))}
        </div>
      </div>
      <p className="planning-note">
        Logaritmik zaman ölçeği · 14 gün üzeri sağ uçta gösterilir. Süreler
        arıza zamanı değil, izlenen sınıra ilişkin tahminlerdir.
      </p>
    </div>
  );
}
