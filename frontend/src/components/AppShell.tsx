import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { usingMocks } from "../api/client";
import gdzLogo from "../assets/gdz-logo.svg";
import { ago } from "../lib/format";
import { useNow } from "../lib/useNow";
import { effectivePrio } from "../lib/worklist";
import { useFleet } from "../state/fleet";
import { isAlarmAudioMuted, setAlarmAudioMuted } from "../lib/audio";
import { Icon, type IconName } from "./Icon";
import { OperatorGirisi } from "./OperatorGirisi";
import "../brandRefinement.css";

function AudioMuteButton() {
  const [muted, setMuted] = useState(isAlarmAudioMuted());
  const toggle = () => {
    const next = !muted;
    setAlarmAudioMuted(next);
    setMuted(next);
  };
  return (
    <button
      type="button"
      className={`icon-button audio-mute-button ${muted ? "muted" : ""}`}
      onClick={toggle}
      title={muted ? "Alarm sesini aç" : "Alarm sesini sustur"}
      aria-label={muted ? "Alarm sesini aç" : "Alarm sesini sustur"}
      aria-pressed={!muted}
      style={{ padding: "4px 8px" }}
    >
      <Icon name={muted ? "mute" : "volume"} size={16} />
    </button>
  );
}

const NAV: { to: string; label: string; icon: IconName; end?: boolean }[] = [
  { to: "/", label: "Operasyon özeti", icon: "grid", end: true },
  { to: "/alarmlar", label: "Alarm merkezi", icon: "alarm" },
  { to: "/bolge", label: "Bölge haritası", icon: "map" },
  { to: "/trend", label: "Trend ve analiz", icon: "chart" },
  { to: "/olay", label: "Olay inceleme", icon: "layers" },
  { to: "/cihaz-sagligi", label: "Cihaz sağlığı", icon: "pulse" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { panels, stream, lastSync, error } = useFleet();
  const location = useLocation();
  const now = useNow(5000);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [query, setQuery] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const critical = panels.filter((p) => effectivePrio(p) === "P1").length;
  const active = NAV.find((n) =>
    n.end ? location.pathname === n.to : location.pathname.startsWith(n.to),
  );
  const offline = stream === "down" || !!error;
  const live = stream === "open";
  const openSearch = () => {
    setQuery("");
    dialog.current?.showModal();
    searchInput.current?.focus();
  };
  useEffect(() => {
    setMobileOpen(false);
    dialog.current?.close();
  }, [location.pathname]);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        openSearch();
      }
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);
  const results = panels
    .filter((p) =>
      `${p.name} ${p.pano_id}`
        .toLocaleLowerCase("tr")
        .includes(query.toLocaleLowerCase("tr")),
    )
    .slice(0, 12);
  return (
    <div className="app-shell">
      <a className="skip-link" href="#workspace">
        İçeriğe geç
      </a>
      {mobileOpen && (
        <button
          className="nav-scrim"
          aria-label="Menüyü kapat"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside className={`sidebar${mobileOpen ? " is-open" : ""}`}>
        <Link to="/" className="product-brand">
          <span className="product-symbol">
            <Icon name="pulse" size={25} />
          </span>
          <span>
            Pano İzleme<small>ŞEBEKE OPERASYONLARI</small>
          </span>
        </Link>
        <div className="workspace-scope">
          <Icon name="map" className="scope-location" size={19} />
          <div>
            Ege Bölgesi<small>ADM & GDZ Elektrik</small>
          </div>
          <span className="scope-dot" />
        </div>
        <div className="nav-section-label">ÇALIŞMA ALANI</div>
        <nav className="side-nav" aria-label="Ana gezinme">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `side-link${isActive ? " active" : ""}`
              }
            >
              <Icon name={n.icon} />
              <span>{n.label}</span>
              {n.to === "/alarmlar" && critical > 0 && (
                <b className="nav-count">{critical}</b>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-status">
            <Icon name="signal" />
            <span>
              {usingMocks
                ? "Örnek veri ortamı"
                : live && !offline
                  ? "Veri akışı bağlı"
                  : "Bağlantı bekleniyor"}
              <small>{panels.length} kayıtlı pano</small>
            </span>
          </div>
          <div className="company-signature">
            <img src={gdzLogo} alt="GDZ Elektrik" />
            <span>
              ADM <small>ELEKTRİK</small>
            </span>
          </div>
          <span className="sidebar-footnote">
            Dağıtım varlıkları · Durum izleme
          </span>
        </div>
      </aside>
      <div className="app-workspace" id="workspace">
        <header className="workspace-topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              onClick={() => setMobileOpen(!mobileOpen)}
              aria-label="Gezinme menüsü"
              aria-expanded={mobileOpen}
            >
              <Icon name="menu" />
            </button>
            <span>Kontrol merkezi</span>
            <Icon name="chevron" size={13} />
            <strong>{active?.label ?? "Pano detayı"}</strong>
          </div>
          <div className="topbar-tools">
            <AudioMuteButton />
            <button className="search-trigger" onClick={openSearch}>
              <Icon name="search" />
              <span>Pano ara</span>
              <kbd>Ctrl K</kbd>
            </button>
            <span
              className={`connection-pill ${usingMocks ? "demo" : offline ? "down" : ""}`}
            >
              <i />
              {usingMocks ? "Demo" : live && !offline ? "Bağlı" : "Bekleniyor"}
            </span>
            <time className="workspace-clock">
              {new Date(now).toLocaleTimeString("tr-TR", {
                hour: "2-digit",
                minute: "2-digit",
                timeZone: "Europe/Istanbul",
              })}
            </time>
            {/* F-19: setToken()'i cagiran tek arayuz. Dusurulurse belirtec hic
                kurulmaz ve kimlik dogrulama sessizce devre disi kalir. */}
            <OperatorGirisi />
          </div>
        </header>
        {usingMocks ? (
          <div className="environment-strip">
            <span>DEMO ORTAMI</span> Örnek veriler gösteriliyor. Saha bağlantısı
            yok.
          </div>
        ) : offline ? (
          <div className="strip stale" role="alert">
            Bağlantı kesildi. Ekrandaki veriler eski olabilir.{" "}
            {lastSync
              ? `Son eşitleme: ${ago(new Date(lastSync).toISOString())}.`
              : "Veri bekleniyor."}
          </div>
        ) : null}
        {children}
        <footer className="workspace-footer">
          <span>ADM / GDZ · Pano durum izleme</span>
          <span>
            {usingMocks
              ? "Örnek veri"
              : lastSync
                ? `Son eşitleme ${ago(new Date(lastSync).toISOString())}`
                : "Veri bekleniyor"}{" "}
            · Yerel saat (TR)
          </span>
        </footer>
      </div>
      <dialog
        className="search-dialog"
        ref={dialog}
        onClick={(e) => {
          if (e.target === dialog.current) dialog.current.close();
        }}
      >
        <div className="search-dialog-head">
          <Icon name="search" />
          <input
            ref={searchInput}
            aria-label="Pano adı veya kimliği"
            placeholder="Pano adı veya kimliğiyle ara…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button
            className="icon-button"
            aria-label="Aramayı kapat"
            onClick={() => dialog.current?.close()}
          >
            <Icon name="close" />
          </button>
        </div>
        <p className="eyebrow">PANOLAR · {results.length} SONUÇ</p>
        <div className="search-results">
          {results.map((p) => (
            <Link key={p.pano_id} to={`/pano/${p.pano_id}`}>
              <Icon name="cabinet" />
              <span>
                <strong>{p.name}</strong>
                <small>{p.pano_id}</small>
              </span>
              <span className="search-risk">Risk {p.risk_score}</span>
              <Icon name="arrow" />
            </Link>
          ))}
          {results.length === 0 && (
            <p className="console-empty">Eşleşen pano bulunamadı.</p>
          )}
        </div>
      </dialog>
    </div>
  );
}
