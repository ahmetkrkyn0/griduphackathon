import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { EpdkKaydi, OutageEvent, PanelSummary, Prio } from "../api/types";
import { EPDK_DURUM_METNI, aboneOzeti, epdkDeger, kesintidekiPanolar } from "../lib/kesinti";
import { PRIO_NAME } from "../lib/labels";
import { effectivePrio } from "../lib/worklist";
import { useFleet } from "../state/fleet";

// Sozlesmede lat/lon zaten onayli bir alan (contracts/openapi.yaml, PanelSummary) — bekleyen
// kontrat degisikligi (contracts/changes/2026-09-14-fleet-health-bulk.md) bunun yerine/ek olarak
// il/ilce eklemeyi oneriyor, ama lat/lon'u kullanmak icin o onaya gerek yok. Veri her zaman dolu
// olmayabilir (opsiyonel alan, backend telemetriyi oldugu gibi aktarir) — bu yuzden en az iki
// noktada koordinat varsa gercek konum tabanli gorunum, yoksa eski dagitim sirketi gruplamasina
// duser (durustluk kurali: olmayan veriyi olmus gibi gostermemek).
const COMPANY: Record<string, string> = { ADM: "ADM Elektrik", GDZ: "GDZ Elektrik" };
const PRIO_COLOR: Record<Prio, string> = { P1: "var(--p1)", P2: "var(--p2)", P3: "var(--p3)", SYS: "var(--sys)", INFO: "var(--dim)" };

function companyOf(panoId: string): string {
  return COMPANY[panoId.slice(0, 3)] ?? panoId.slice(0, 3);
}

type Geo = PanelSummary & { lat: number; lon: number };
const hasCoords = (p: PanelSummary): p is Geo => p.lat != null && p.lon != null;

const MAP_W = 900;
const MAP_H = 620;
const MAP_PAD = 64;

/** Gercek enlem/boylamdan yerel, olcek-korumali bir izdusum (kucuk bolgesel alanda yeterince
 *  dogru — boylam, ortalama enlemin kosinusuyle duzeltilir ki sekil dogu-bati yonunde sikismasin). */
function projector(points: Geo[]) {
  const lats = points.map((p) => p.lat);
  const lons = points.map((p) => p.lon);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  const lonScale = Math.cos(((minLat + maxLat) / 2) * (Math.PI / 180));
  const spanX = Math.max((maxLon - minLon) * lonScale, 0.02);
  const spanY = Math.max(maxLat - minLat, 0.02);
  const scale = Math.min((MAP_W - 2 * MAP_PAD) / spanX, (MAP_H - 2 * MAP_PAD) / spanY);
  const drawW = spanX * scale;
  const drawH = spanY * scale;
  const offX = (MAP_W - drawW) / 2;
  const offY = (MAP_H - drawH) / 2;
  return (p: Geo) => ({
    x: offX + (p.lon - minLon) * lonScale * scale,
    y: offY + (maxLat - p.lat) * scale,
  });
}

/** TC3: bölge haritası. Gerçek enlem/boylamı olan panolar varsa (ilçe merkezi hassasiyetinde,
 *  bkz. api/mock.ts DISTRICT_COORDS) yerel ölçekli bir konum grafiğine yerleştirilir — gerçek
 *  harita karosu (Google/Mapbox/OSM) kullanılmaz, çünkü GK4 yığını tamamen çevrimdışı çalışır. */
export function BolgeHaritasi() {
  const { panels } = useFleet();
  const geoPanels = panels.filter(hasCoords);
  const outages = useOutages();

  return (
    <main className="page">
      <div className="hero">
        <h1>Bölge haritası</h1>
        {geoPanels.length >= 2 ? (
          <p>
            Panoların gerçek enlem/boylamına göre yerel ölçekli konum görünümü. Noktalar ilçe merkezi
            hassasiyetindedir (gerçek trafo GPS pini değil); gerçek harita karosu (Google/Mapbox/OSM)
            kullanılmaz, çünkü yığın tamamen internetten bağımsız çalışır (GK4).
          </p>
        ) : (
          <p>
            Dağıtım şirketine göre özet görünüm. Bu filoda konum verisi (<code>lat</code>/<code>lon</code>)
            henüz yeterli sayıda pano için dolu değil; gerçek harita karosu kullanılmaz (GK4: çevrimdışı).
          </p>
        )}
      </div>

      <div className="region-legend">
        {(["P1", "P2", "P3", "SYS"] as Prio[]).map((p) => (
          <span key={p}>
            <span className="region-dot" style={{ background: PRIO_COLOR[p], width: 12, height: 12, display: "inline-block", borderRadius: 3, marginRight: 4 }} />
            {PRIO_NAME[p]}
          </span>
        ))}
        <span>
          <span className="region-dot normal" style={{ width: 12, height: 12, display: "inline-block", borderRadius: 3, marginRight: 4 }} />
          Normal
        </span>
      </div>

      {outages.map((outage) => (
        <KesintiSeridi key={outage.outage_id} outage={outage} />
      ))}

      {geoPanels.length >= 2 ? (
        <GeoHarita panels={geoPanels} allCount={panels.length} outages={outages} />
      ) : (
        <SirketGruplari panels={panels} />
      )}
    </main>
  );
}

/** Acik ust sebeke kesintileri (F-22). Harita disinda da gorunur: konum verisi olmayan
 *  filoda (SirketGruplari gorunumu) ozellik kaybolmasin. */
function useOutages(): OutageEvent[] {
  const [outages, setOutages] = useState<OutageEvent[]>([]);
  useEffect(() => {
    const control = new AbortController();
    const load = () =>
      api.outages("acik", control.signal).then(setOutages).catch(() => {
        /* kesinti listesi bir kolayliktir; alinamamasi haritayi bozmamali */
      });
    load();
    const timer = setInterval(load, 30_000);
    return () => {
      control.abort();
      clearInterval(timer);
    };
  }, []);
  return outages;
}

/**
 * Kesinti seridi: olayin metin karsiligi.
 *
 * ISA-101 geregi ayirt edicilik yalnizca RENGE dayanamaz — haritadaki halka sekil farkidir,
 * bu serit ise ayni bilgiyi METIN olarak verir. Ayrica konum verisi olmayan filoda harita
 * hic cizilmez ve ozellik yalnizca bu seritle yasar.
 */
function KesintiSeridi({ outage }: { outage: OutageEvent }) {
  return (
    <div className="kesinti-serit" role="status">
      <strong>Üst şebeke kesintisi</strong> — <code>{outage.fider_id}</code> fiderinde{" "}
      {outage.panolar.length} pano aynı anda sustu.{" "}
      Etkilenen abone: <strong>{aboneOzeti(outage).metin}</strong>.{" "}
      <span className="dim">
        Bu bir gruplamadır: alarmlar bastırılmadı, hepsi konsolda duruyor.
      </span>
      <EpdkTaslagi outageId={outage.outage_id} />
    </div>
  );
}

/**
 * EPDK Madde 8 kesinti kaydı taslağı (F-23).
 *
 * Talep üzerine açılır (`<details>`): taslak her kesinti şeridinde otomatik yüklenirse
 * ekran açılışında gereksiz istek atardı. Tablo, alanın **durumunu** ayrı bir sütunda
 * gösterir — ISA-101 gereği ayırt edicilik yalnızca renge dayanamaz; "elle doldurulacak"
 * bilgisi **metin** olarak durur.
 */
function EpdkTaslagi({ outageId }: { outageId: string }) {
  const [kayit, setKayit] = useState<EpdkKaydi | null>(null);
  const [hata, setHata] = useState(false);

  const yukle = () => {
    if (kayit || hata) return;
    api.epdkKaydi(outageId).then(setKayit).catch(() => setHata(true));
  };

  return (
    <details className="epdk-taslak" onToggle={yukle}>
      <summary>EPDK Madde 8 kesinti kaydı taslağı</summary>
      {hata && <p className="dim small">Taslak alınamadı.</p>}
      {kayit && (
        <>
          <p className="epdk-uyari" role="note">
            <strong>TASLAK</strong> — {kayit.uyari}
          </p>
          <p className="dim small">
            {kayit.ozet.toplam} alanın {kayit.ozet.olculen} tanesi ölçülüyor,{" "}
            {kayit.ozet.oneri} tanesi öneri, {kayit.ozet.elle_doldurulacak} tanesi elle doldurulacak.
          </p>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Alan</th>
                  <th>Değer</th>
                  <th>Durum</th>
                  <th>Açıklama</th>
                </tr>
              </thead>
              <tbody>
                {kayit.alanlar.map((alan) => (
                  <tr key={alan.ad} className={`epdk-${alan.durum}`}>
                    <td>{alan.ad}</td>
                    {/* Ölçmediğimiz alana SIFIR yazılmaz — kural lib/kesinti.ts'te ve testli. */}
                    <td className={alan.deger === null ? "dim" : undefined}>{epdkDeger(alan.deger)}</td>
                    <td>{EPDK_DURUM_METNI[alan.durum]}</td>
                    <td className="dim small">{alan.aciklama}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {kayit.kanit && kayit.kanit.length > 0 && (
            <p className="dim small">
              Kanıt: {kayit.kanit.filter((k) => k.event_id).length} pano için mevcut kara kutu
              zaman çizelgesi bağlandı{" "}
              {kayit.kanit
                .filter((k) => k.event_id)
                .map((k) => (
                  <Link key={k.pano_id} to={`/olay/${k.event_id}`} className="epdk-kanit">
                    {k.name ?? k.pano_id}
                  </Link>
                ))}
              . Yeni bir çizelge üretilmedi.
            </p>
          )}
        </>
      )}
    </details>
  );
}

function GeoHarita({ panels, allCount, outages }: { panels: Geo[]; allCount: number; outages: OutageEvent[] }) {
  const project = projector(panels);
  const missing = allCount - panels.length;
  // Kesintiye dahil panolar: haritada kesikli bir halka ile isaretlenir (sekil farki,
  // yalnizca renk degil — ISA-101).
  const outagePanels = kesintidekiPanolar(outages);
  return (
    <>
      <svg className="geo-map" viewBox={`0 0 ${MAP_W} ${MAP_H}`} role="group" aria-label="Panoların yaklaşık coğrafi konumu">
        <rect className="geo-frame" x={1} y={1} width={MAP_W - 2} height={MAP_H - 2} rx={12} />
        <g className="geo-compass" transform={`translate(${MAP_W - 46}, 40)`}>
          <line x1={0} y1={14} x2={0} y2={-14} />
          <path d="M -6 -6 L 0 -16 L 6 -6" />
          <text y={26} textAnchor="middle">K</text>
        </g>
        {panels.map((p) => {
          const { x, y } = project(p);
          const prio = effectivePrio(p);
          return (
            <g key={p.pano_id}>
              {prio && !["SYS", "INFO"].includes(prio) && <circle className="geo-halo" cx={x} cy={y} r={20} />}
              {outagePanels.has(p.pano_id) && (
                <circle className="geo-kesinti" cx={x} cy={y} r={26}>
                  <title>{`Üst şebeke kesintisi: ${outagePanels.get(p.pano_id)}`}</title>
                </circle>
              )}
              <Link to={`/pano/${p.pano_id}`} title={`${p.name} (${p.pano_id}), risk ${p.risk_score}`}>
                <circle
                  className={prio ? "geo-dot" : "geo-dot normal"}
                  style={prio ? { fill: PRIO_COLOR[prio] } : undefined}
                  cx={x}
                  cy={y}
                  r={10}
                />
                <text className="geo-label" x={x} y={y - 15} textAnchor="middle">
                  {p.name.split(" ")[0]}
                </text>
              </Link>
            </g>
          );
        })}
      </svg>
      {missing > 0 && (
        <p className="dim small geo-note">
          {missing} pano konum verisi olmadığı için haritada gösterilmiyor.
        </p>
      )}
    </>
  );
}

function SirketGruplari({ panels }: { panels: PanelSummary[] }) {
  const groups = new Map<string, PanelSummary[]>();
  for (const p of panels) {
    const key = companyOf(p.pano_id);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(p);
  }
  return (
    <div className="region-map">
      {[...groups.entries()].map(([company, list]) => {
        const attention = list.filter((p) => effectivePrio(p) !== null).length;
        return (
          <div key={company} className="region-col">
            <h3>
              <span>{company}</span>
              <span className="dim small">
                {list.length} pano{attention ? `, ${attention} ilgi bekliyor` : ""}
              </span>
            </h3>
            <div className="region-dots">
              {list
                .sort((a, b) => b.risk_score - a.risk_score)
                .map((p) => {
                  const prio = effectivePrio(p);
                  return (
                    <Link
                      key={p.pano_id}
                      to={`/pano/${p.pano_id}`}
                      className={prio ? "region-dot" : "region-dot normal"}
                      style={prio ? { background: PRIO_COLOR[prio] } : undefined}
                      title={`${p.name} (${p.pano_id}), risk ${p.risk_score}`}
                    >
                      {p.risk_score}
                    </Link>
                  );
                })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
