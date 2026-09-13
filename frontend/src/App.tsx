import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { usingMocks } from "./api/client";
import { ago, num } from "./lib/format";
import { useNow } from "./lib/useNow";
import { FiloListesi } from "./pages/FiloListesi";
import { PanoDetay } from "./pages/PanoDetay";
import { FleetProvider, useFleet } from "./state/fleet";

export function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <FleetProvider>
        <header className="topbar">
          <Link to="/" className="brand">
            Grid Up Pano İzleme
          </Link>
          <FleetKpis />
        </header>
        <StatusStrip />
        <Routes>
          <Route path="/" element={<FiloListesi />} />
          <Route path="/pano/:panoId" element={<PanoDetay />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </FleetProvider>
    </BrowserRouter>
  );
}

function FleetKpis() {
  const { panels, kpi } = useFleet();
  if (panels.length === 0 && !kpi) return null;

  const total = kpi?.panels_total ?? panels.length;
  const commsPct =
    kpi?.comms_ok_pct ?? (panels.length > 0 ? (100 * panels.filter((p) => p.comms_ok).length) / panels.length : null);

  return (
    <ul className="kpis" aria-label="Filo özeti">
      <li>
        <b>{num(total, 0)}</b>pano
      </li>
      {commsPct != null && (
        <li>
          <b>%{num(commsPct, 1)}</b>haberleşiyor
        </li>
      )}
      {kpi?.alarms_per_100_panels_per_day != null && (
        <li>
          <b>{num(kpi.alarms_per_100_panels_per_day, 1)}</b>alarm / 100 pano / gün
        </li>
      )}
      {kpi?.p95_end_to_end_ms != null && (
        <li>
          <b>{num(kpi.p95_end_to_end_ms, 0)} ms</b>alarmdan telefona (p95)
        </li>
      )}
    </ul>
  );
}

function StatusStrip() {
  const { stream, lastSync, error, panels } = useFleet();
  useNow(5000);

  if (usingMocks) {
    return (
      <div className="strip info" role="status">
        Örnek veriyle çalışıyor; backend'e bağlı değil.
      </div>
    );
  }
  const down = stream === "down" || (error !== null && panels.length > 0);
  if (!down) return null;

  const since = lastSync ? `Son güncelleme ${ago(new Date(lastSync).toISOString())}.` : "Henüz veri alınmadı.";
  return (
    <div className="strip stale" role="alert">
      Canlı bağlantı koptu, ekrandaki veriler eski olabilir. {since} Yeniden bağlanılıyor.
    </div>
  );
}

function NotFound() {
  return (
    <main className="page">
      <div className="empty">
        <h1>Sayfa bulunamadı</h1>
        <p>
          <Link to="/">Filo ekranına dönün.</Link>
        </p>
      </div>
    </main>
  );
}
