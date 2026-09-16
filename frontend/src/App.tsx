import { BrowserRouter, Link, NavLink, Route, Routes } from "react-router-dom";
import { usingMocks } from "./api/client";
import gdzLogo from "./assets/gdz-logo.svg";
import { ago, num } from "./lib/format";
import { useNow } from "./lib/useNow";
import { AlarmKonsolu } from "./pages/AlarmKonsolu";
import { BolgeHaritasi } from "./pages/BolgeHaritasi";
import { CihazSagligi } from "./pages/CihazSagligi";
import { FiloListesi } from "./pages/FiloListesi";
import { OlayAnalizi } from "./pages/OlayAnalizi";
import { PanoDetay } from "./pages/PanoDetay";
import { TrendKorelasyon } from "./pages/TrendKorelasyon";
import { FleetProvider, useFleet } from "./state/fleet";

const NAV = [
  { to: "/", label: "Filo", end: true },
  { to: "/alarmlar", label: "Alarmlar" },
  { to: "/trend", label: "Trend" },
  { to: "/olay", label: "Kara kutu" },
  { to: "/cihaz-sagligi", label: "Cihaz sağlığı" },
  { to: "/bolge", label: "Bölge" },
];

export function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <FleetProvider>
        <header className="topbar">
          <Link to="/" className="brand">
            <BrandMark />
            Grid Up Pano İzleme
          </Link>
          <nav className="nav" aria-label="Ana gezinme">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
                {n.label}
              </NavLink>
            ))}
          </nav>
          <FleetKpis />
        </header>
        <StatusStrip />
        <Routes>
          <Route path="/" element={<FiloListesi />} />
          <Route path="/pano/:panoId" element={<PanoDetay />} />
          <Route path="/alarmlar" element={<AlarmKonsolu />} />
          <Route path="/trend" element={<TrendKorelasyon />} />
          <Route path="/trend/:panoId" element={<TrendKorelasyon />} />
          <Route path="/olay" element={<OlayAnalizi />} />
          <Route path="/olay/:eventId" element={<OlayAnalizi />} />
          <Route path="/cihaz-sagligi" element={<CihazSagligi />} />
          <Route path="/bolge" element={<BolgeHaritasi />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </FleetProvider>
    </BrowserRouter>
  );
}

/** Kullanicinin sagladigi gercek GDZ Elektrik logosu (16 Eylul, kullanici talebi) — onceki
 *  "logo dosyalari gomulmez" karari (plan §3.5, grafit ucgen kivilcim isareti) burada acikca
 *  gecersiz kilindi. Gercek sitede (gdzelektrik.com.tr) header logosu inline SVG olarak
 *  126x70 px goruntuleniyor; bize verilen dosya farkli bir disa aktarim (960x540 viewBox,
 *  icinde gomulu raster) oldugu icin piksel-birebir degil, ayni oranli "logo olcegi" hedeflendi. */
function BrandMark() {
  return <img className="brand-mark" src={gdzLogo} alt="GDZ Elektrik" />;
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
        <b>{num(total, 0)}</b>
        <span>pano</span>
      </li>
      {commsPct != null && (
        <li>
          <b>%{num(commsPct, 1)}</b>
          <span>haberleşiyor</span>
        </li>
      )}
      {kpi?.alarms_per_100_panels_per_day != null && (
        <li>
          <b>{num(kpi.alarms_per_100_panels_per_day, 1)}</b>
          <span>alarm / 100 pano / gün</span>
        </li>
      )}
      {kpi?.p95_end_to_end_ms != null && (
        <li>
          <b>{num(kpi.p95_end_to_end_ms, 0)} ms</b>
          <span>alarmdan telefona (p95)</span>
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
