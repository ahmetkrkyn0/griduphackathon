import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { PanelSummary, Prio } from "../api/types";
import ilceSinirlari from "../data/ilce-sinirlari.json";
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

// [boylam, enlem] — GeoJSON sozlesmesi. Kaynak: UN OCHA HDX COD-AB-TUR (CC BY-IGO), ilce
// sinirlari Douglas-Peucker ile sadelestirildi (bkz. frontend/TASARIM-REVIZYONU.md §18). Bu dosya
// ADM (Aydin/Denizli/Mugla) ve GDZ'nin (Izmir/Manisa) hizmet bolgesindeki TUM 96 ilceyi icerir —
// yalnizca panosu olan 20 tanesini degil — harita "kopuk" degil butun gorunsun diye (kullanici
// talebi, 16 Eylul). Bu 5 il gercekte birbirine komsu (Izmir-Aydin, Manisa-Aydin, Manisa-Denizli
// sinirdas) oldugundan ayri bir "baglayici" ile eklemeye gerek kalmadi — bkz. TASARIM-REVIZYONU.md.
type LonLat = [number, number];
type BoundaryGeom = { type: "Polygon"; coordinates: LonLat[][] } | { type: "MultiPolygon"; coordinates: LonLat[][][] };
type TerritoryEntry = { company: "ADM" | "GDZ"; province: string; plate: string; geom: BoundaryGeom };
const TERRITORY = ilceSinirlari as unknown as Record<string, TerritoryEntry>;

function districtKey(name: string): string {
  return name.split(" ")[0];
}

function ringsOf(geom: BoundaryGeom): LonLat[][] {
  return geom.type === "Polygon" ? geom.coordinates : geom.coordinates.flat();
}

function pathOf(geom: BoundaryGeom, project: (lon: number, lat: number) => { x: number; y: number }): string {
  return ringsOf(geom)
    .map((ring) => `M${ring.map(([lon, lat]) => { const { x, y } = project(lon, lat); return `${x.toFixed(1)},${y.toFixed(1)}`; }).join("L")}Z`)
    .join(" ");
}

/** Gercek konumda birbirine cok yakin panolar (ornek: Bornova/Karsiyaka/Cigli, hepsi Izmir
 *  merkezinde birkac km arayla) noktalari gorsel olarak ust uste bindirir. Kucuk, karsilikli bir
 *  itme (birkac piksel) ile ayirir — yalnizca NOKTA isaretinin ekran konumu icin, ilcenin gercek
 *  sinirini etkilemez. Gercek haritalarin da yakinlastirma seviyesine gore yaptigi bir sey. */
function separateDots<T extends { x: number; y: number }>(points: T[], minDist: number, iterations = 8): T[] {
  const pts = points.map((p) => ({ ...p }));
  for (let iter = 0; iter < iterations; iter++) {
    for (let i = 0; i < pts.length; i++) {
      for (let j = i + 1; j < pts.length; j++) {
        const dx = pts[j].x - pts[i].x;
        const dy = pts[j].y - pts[i].y;
        const dist = Math.hypot(dx, dy) || 0.01;
        if (dist < minDist) {
          const push = (minDist - dist) / 2;
          const ux = dx / dist;
          const uy = dy / dist;
          pts[i].x -= ux * push;
          pts[i].y -= uy * push;
          pts[j].x += ux * push;
          pts[j].y += uy * push;
        }
      }
    }
  }
  return pts;
}

/** Etiketler birbirine cok yakinsa (ayni kume, ornegin Bornova/Karsiyaka/Cigli/Buca) ustuste binip
 *  okunmaz olur. Yalnizca dikey kaydirma yeterli degildi (birbirine 2 boyutta yakin noktalarda
 *  hala cakisiyordu) — simdi noktanin etrafinda (ust/alt/sag/sol/kose) sirayla aday konum dener,
 *  ilk cakismayanı kullanir; hicbiri bos degilse en az cakisani secer. */
function layoutLabelOffsets(points: { x: number; y: number; text: string }[]): { dx: number; dy: number }[] {
  const CHAR_W = 6.2;
  const LINE_H = 13;
  const CANDIDATES: Array<[number, number]> = [
    [0, -13],
    [0, 20],
    [26, -13],
    [-26, -13],
    [26, 20],
    [-26, 20],
    [0, 34],
    [0, -27],
    [34, 6],
    [-34, 6],
  ];
  const placed: { x0: number; x1: number; y0: number; y1: number }[] = [];
  const offsets: { dx: number; dy: number }[] = [];
  for (const p of points) {
    const halfW = (p.text.length * CHAR_W) / 2 + 2;
    let chosen: [number, number] = CANDIDATES[0];
    let chosenBox = { x0: 0, x1: 0, y0: 0, y1: 0 };
    let found = false;
    for (const [dx, dy] of CANDIDATES) {
      const cx = p.x + dx;
      const cy = p.y + dy;
      const box = { x0: cx - halfW, x1: cx + halfW, y0: Math.min(cy, cy - LINE_H), y1: Math.max(cy, cy - LINE_H) };
      const collides = placed.some((b) => box.x0 < b.x1 && box.x1 > b.x0 && box.y0 < b.y1 && box.y1 > b.y0);
      if (!collides) {
        chosen = [dx, dy];
        chosenBox = box;
        found = true;
        break;
      }
      if (!found) {
        chosen = [dx, dy];
        chosenBox = box;
      }
    }
    placed.push(chosenBox);
    offsets.push({ dx: chosen[0], dy: chosen[1] });
  }
  return offsets;
}

const MAP_W = 900;
const MAP_H = 620;
const MAP_PAD = 40;
const ZOOM_MIN = 1;
const ZOOM_MAX = 6;

/** Gercek enlem/boylamdan yerel, olcek-korumali bir izdusum (kucuk bolgesel alanda yeterince
 *  dogru — boylam, ortalama enlemin kosinusuyle duzeltilir ki sekil dogu-bati yonunde sikismasin). */
function projector(allPoints: LonLat[]) {
  const lats = allPoints.map(([, lat]) => lat);
  const lons = allPoints.map(([lon]) => lon);
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
  return (lon: number, lat: number) => ({
    x: offX + (lon - minLon) * lonScale * scale,
    y: offY + (maxLat - lat) * scale,
  });
}

/** TC3: bölge haritası. Gerçek enlem/boylamı olan panolar varsa (ilçe merkezi hassasiyetinde,
 *  bkz. api/mock.ts DISTRICT_COORDS) yerel ölçekli bir konum grafiğine yerleştirilir. Arka planda
 *  ADM/GDZ'nin hizmet bölgesindeki TÜM ilçeler (src/data/ilce-sinirlari.json, 96 ilçe) pasif gri
 *  zeminde çizilir ki harita "kopuk" görünmesin; panosu olan ilçeler bunun üstünde düz turuncu
 *  kontur ile öne çıkar (blur/glow kaldırıldı — kullanıcı geri bildirimi: "beyazımsı" duruyordu).
 *  Gerçek harita karosu (Google/Mapbox/OSM) kullanılmaz, çünkü GK4 yığını tamamen
 *  çevrimdışı çalışır — sınır verisi build zamanında pakete gömülü, çalışma zamanında hiçbir ağ
 *  isteği yapılmaz. */
export function BolgeHaritasi() {
  const { panels } = useFleet();
  const geoPanels = panels.filter(hasCoords);

  return (
    <main className="page">
      <div className="hero">
        <h1>Bölge haritası</h1>
        {geoPanels.length >= 2 ? (
          <p>
            ADM (Aydın, Denizli, Muğla) ve GDZ'nin (İzmir, Manisa) hizmet bölgesindeki tüm ilçeler,
            gerçek sınırlarıyla çizilir; panosu olan ilçeler turuncu ve vurgulu, diğerleri pasif
            gri gösterilir. Nokta konumu ilçe merkezi hassasiyetindedir (gerçek trafo GPS pini
            değil); gerçek harita karosu (Google/Mapbox/OSM) kullanılmaz, çünkü yığın tamamen
            internetten bağımsız çalışır (GK4).
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

      {geoPanels.length >= 2 ? <GeoHarita panels={geoPanels} allCount={panels.length} /> : <SirketGruplari panels={panels} />}
    </main>
  );
}

function GeoHarita({ panels, allCount }: { panels: Geo[]; allCount: number }) {
  const missing = allCount - panels.length;
  const panelDistricts = new Set(panels.map((p) => districtKey(p.name)));
  const territoryEntries = Object.entries(TERRITORY);

  const allLonLat: LonLat[] = [
    ...panels.map((p): LonLat => [p.lon, p.lat]),
    ...territoryEntries.flatMap(([, t]) => ringsOf(t.geom)).flat(),
  ];
  const project = projector(allLonLat);

  const rawPoints = panels.map((p) => ({ ...project(p.lon, p.lat), p }));
  const dotPoints = separateDots(rawPoints, 17);
  const labelOffsets = layoutLabelOffsets(dotPoints.map((d) => ({ x: d.x, y: d.y, text: d.p.name.split(" ")[0] })));

  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null);
  const [view, setView] = useState({ scale: 1, tx: 0, ty: 0 });

  const toSvgPoint = useCallback((clientX: number, clientY: number) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return { ux: MAP_W / 2, uy: MAP_H / 2 };
    return { ux: ((clientX - rect.left) / rect.width) * MAP_W, uy: ((clientY - rect.top) / rect.height) * MAP_H };
  }, []);

  const zoomAt = useCallback((ux: number, uy: number, factor: number) => {
    setView((v) => {
      const scale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, v.scale * factor));
      if (scale === v.scale) return v;
      const cx = (ux - v.tx) / v.scale;
      const cy = (uy - v.ty) / v.scale;
      return { scale, tx: ux - cx * scale, ty: uy - cy * scale };
    });
  }, []);

  // React'in onWheel'i pasif dinleyici olarak eklenir — preventDefault icinde cagrilsa bile
  // tarayicinin varsayilan davranisi (sayfa kaydirma / trackpad pinch'te tarayici sayfa yakinlastirmasi)
  // engellenmiyordu (kullanici bulgusu: "zoom atarken sayfayi asagiya da kaydiriyor"). Cozum: native,
  // passive:false bir 'wheel' dinleyicisi elle eklemek — yalnizca bu, preventDefault'un ise yaramasini saglar.
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const handler = (e: WheelEvent) => {
      e.preventDefault();
      const { ux, uy } = toSvgPoint(e.clientX, e.clientY);
      zoomAt(ux, uy, e.deltaY < 0 ? 1.18 : 1 / 1.18);
    };
    svg.addEventListener("wheel", handler, { passive: false });
    return () => svg.removeEventListener("wheel", handler);
  }, [toSvgPoint, zoomAt]);

  const onPointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
    if (view.scale === ZOOM_MIN) return;
    (e.target as Element).setPointerCapture(e.pointerId);
    dragRef.current = { x: e.clientX, y: e.clientY, tx: view.tx, ty: view.ty };
  };
  const onPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const drag = dragRef.current;
    const rect = svgRef.current?.getBoundingClientRect();
    if (!drag || !rect) return;
    const dx = ((e.clientX - drag.x) / rect.width) * MAP_W;
    const dy = ((e.clientY - drag.y) / rect.height) * MAP_H;
    setView((v) => ({ ...v, tx: drag.tx + dx, ty: drag.ty + dy }));
  };
  const onPointerUp = () => {
    dragRef.current = null;
  };

  return (
    <>
      <div className="geo-map-wrap">
        <svg
          ref={svgRef}
          className="geo-map"
          viewBox={`0 0 ${MAP_W} ${MAP_H}`}
          role="group"
          aria-label="ADM/GDZ hizmet bölgesi ve panoların gerçek konumu"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={onPointerUp}
          style={{ cursor: view.scale > ZOOM_MIN ? "grab" : "default" }}
        >
          <rect className="geo-frame" x={1} y={1} width={MAP_W - 2} height={MAP_H - 2} rx={12} />
          <g transform={`translate(${view.tx} ${view.ty}) scale(${view.scale})`}>
            {/* ADM/GDZ'nin tum hizmet bolgesi (96 ilce) — pasif/gri zemin, harita "kopuk" gorunmesin
                diye (kullanici talebi). Panosu olan ilceler duz turuncu kontur ile vurgulanir.
                fillRule verilmez (varsayilan nonzero): evenodd, sadelestirmeden kalan kendine-kesisen
                kenarlarda ilcenin icinde beyaz "cizgiler/delikler" gibi gorunuyordu (kullanici bulgusu). */}
            {territoryEntries.map(([name, t]) => (
              <path
                key={`t-${name}`}
                className={panelDistricts.has(name) ? "geo-district" : "geo-territory"}
                d={pathOf(t.geom, project)}
                vectorEffect="non-scaling-stroke"
              >
                <title>{`${name} (${COMPANY[t.company]})`}</title>
              </path>
            ))}

            {dotPoints.map(({ x, y, p }, i) => {
              const prio = effectivePrio(p);
              return (
                <g key={p.pano_id}>
                  {prio && !["SYS", "INFO"].includes(prio) && (
                    <circle className="geo-halo" cx={x} cy={y} r={13 / view.scale} vectorEffect="non-scaling-stroke" />
                  )}
                  <Link to={`/pano/${p.pano_id}`} title={`${p.name} (${p.pano_id}), risk ${p.risk_score}`}>
                    <circle
                      className={prio ? "geo-dot" : "geo-dot normal"}
                      style={prio ? { fill: PRIO_COLOR[prio] } : undefined}
                      cx={x}
                      cy={y}
                      r={6 / view.scale}
                      vectorEffect="non-scaling-stroke"
                    />
                    <text
                      className="geo-label"
                      x={x + labelOffsets[i].dx / view.scale}
                      y={y + labelOffsets[i].dy / view.scale}
                      textAnchor="middle"
                      fontSize={11 / view.scale}
                    >
                      {p.name.split(" ")[0]}
                    </text>
                  </Link>
                </g>
              );
            })}
          </g>
          <g className="geo-compass" transform={`translate(${MAP_W - 46}, 40)`}>
            <line x1={0} y1={14} x2={0} y2={-14} />
            <path d="M -6 -6 L 0 -16 L 6 -6" />
            <text y={26} textAnchor="middle">K</text>
          </g>
        </svg>
        <div className="geo-zoom">
          <button type="button" onClick={() => zoomAt(MAP_W / 2, MAP_H / 2, 1.4)} aria-label="Yakınlaştır">
            +
          </button>
          <button type="button" onClick={() => zoomAt(MAP_W / 2, MAP_H / 2, 1 / 1.4)} aria-label="Uzaklaştır">
            −
          </button>
          {view.scale > ZOOM_MIN && (
            <button type="button" onClick={() => setView({ scale: 1, tx: 0, ty: 0 })} aria-label="Haritayı sıfırla">
              ⟲
            </button>
          )}
        </div>
      </div>
      <p className="dim small geo-note">
        İlçe sınırları: UN OCHA HDX <a href="https://data.humdata.org/dataset/cod-ab-tur" target="_blank" rel="noreferrer">COD-AB-TUR</a> (CC BY-IGO), sadeleştirilmiş.
        Fare tekerleğiyle veya +/− ile yakınlaştırabilir, sürükleyerek kaydırabilirsiniz.
        {missing > 0 && ` ${missing} pano konum verisi olmadığı için haritada gösterilmiyor.`}
      </p>
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
