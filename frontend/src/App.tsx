import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { FleetProvider } from "./state/fleet";
import { AppShell } from "./components/AppShell";
import { AlarmKonsolu } from "./pages/AlarmKonsolu";
import { BolgeHaritasi } from "./pages/BolgeHaritasi";
import { CihazSagligi } from "./pages/CihazSagligi";
import { FiloListesi } from "./pages/FiloListesi";
import { OlayAnalizi } from "./pages/OlayAnalizi";
import { PanoDetay } from "./pages/PanoDetay";
import { TrendKorelasyon } from "./pages/TrendKorelasyon";

export function App() {
  return (
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <FleetProvider>
        <AppShell>
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
        </AppShell>
      </FleetProvider>
    </BrowserRouter>
  );
}

function NotFound() {
  return (
    <main className="page">
      <h1>Sayfa bulunamadı</h1>
      <p>
        Aradığınız adres mevcut değil. <Link to="/">Filo listesine dönün</Link>.
      </p>
    </main>
  );
}
