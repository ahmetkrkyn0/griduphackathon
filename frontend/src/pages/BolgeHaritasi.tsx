import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { EpdkKaydi, OutageEvent, PanelSummary, Prio } from "../api/types";
import ilceSinirlari from "../data/ilce-sinirlari.json";
import { EPDK_DURUM_METNI, aboneOzeti, epdkDeger, kesintidekiPanolar } from "../lib/kesinti";
import {
  insidePolygons,
  prepareLabelCandidates,
  placePreparedLabel,
  normalizeMapSearch as normalize,
} from "../lib/mapGeometry";
import "../mapRefinement.css";
import { PRIO_NAME } from "../lib/labels";
import { effectivePrio } from "../lib/worklist";
import { useFleet } from "../state/fleet";

// Sozlesmede lat/lon zaten onayli bir alan (contracts/openapi.yaml, PanelSummary) — bekleyen
// kontrat degisikligi (contracts/changes/2026-09-14-fleet-health-bulk.md) bunun yerine/ek olarak
// il/ilce eklemeyi oneriyor, ama lat/lon'u kullanmak icin o onaya gerek yok. Veri her zaman dolu
// olmayabilir (opsiyonel alan, backend telemetriyi oldugu gibi aktarir) — bu yuzden en az iki
// noktada koordinat varsa gercek konum tabanli gorunum, yoksa eski dagitim sirketi gruplamasina
// duser (durustluk kurali: olmayan veriyi olmus gibi gostermemek).
const COMPANY: Record<string, string> = {
  ADM: "ADM Elektrik",
  GDZ: "GDZ Elektrik",
};
const PRIO_COLOR: Record<Prio, string> = {
  P1: "var(--p1)",
  P2: "var(--p2)",
  P3: "var(--p3)",
  SYS: "var(--sys)",
  INFO: "var(--dim)",
};

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
type BoundaryGeom =
  | { type: "Polygon"; coordinates: LonLat[][] }
  | { type: "MultiPolygon"; coordinates: LonLat[][][] };
type TerritoryEntry = {
  company: "ADM" | "GDZ";
  province: string;
  plate: string;
  geom: BoundaryGeom;
};
const TERRITORY = ilceSinirlari as unknown as Record<string, TerritoryEntry>;

function ringsOf(geom: BoundaryGeom): LonLat[][] {
  return geom.type === "Polygon" ? geom.coordinates : geom.coordinates.flat();
}

function pathOf(
  geom: BoundaryGeom,
  project: (lon: number, lat: number) => { x: number; y: number },
): string {
  return ringsOf(geom)
    .map(
      (ring) =>
        `M${ring
          .map(([lon, lat]) => {
            const { x, y } = project(lon, lat);
            return `${x.toFixed(1)},${y.toFixed(1)}`;
          })
          .join("L")}Z`,
    )
    .join(" ");
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
  const scale = Math.min(
    (MAP_W - 2 * MAP_PAD) / spanX,
    (MAP_H - 2 * MAP_PAD) / spanY,
  );
  const drawW = spanX * scale;
  const drawH = spanY * scale;
  const offX = (MAP_W - drawW) / 2;
  const offY = (MAP_H - drawH) / 2;
  return (lon: number, lat: number) => ({
    x: offX + (lon - minLon) * lonScale * scale,
    y: offY + (maxLat - lat) * scale,
  });
}

const territoryEntries = Object.entries(TERRITORY);
const polygonsOf = (geom: BoundaryGeom) =>
  geom.type === "Polygon" ? [geom.coordinates] : geom.coordinates;
const project = projector(
  territoryEntries.flatMap(([, t]) => ringsOf(t.geom)).flat(),
);
const mapGeometry = Object.fromEntries(
  territoryEntries.map(([name, t]) => [
    name,
    {
      path: pathOf(t.geom, project),
      geographic: polygonsOf(t.geom).map((polygon) =>
        polygon.map((ring) => ring.map(([x, y]) => ({ x, y }))),
      ),
      projected: polygonsOf(t.geom).map((polygon) =>
        polygon.map((ring) => ring.map(([lon, lat]) => project(lon, lat))),
      ),
    },
  ]),
);
const boundaryPath = territoryEntries
  .map(([name]) => mapGeometry[name].path)
  .join(" ");
let preparedLabels:
  | Record<string, ReturnType<typeof prepareLabelCandidates>>
  | undefined;
function getPreparedLabels() {
  return (preparedLabels ??= Object.fromEntries(
    territoryEntries.map(([name]) => [
      name,
      prepareLabelCandidates(mapGeometry[name].projected),
    ]),
  ));
}

/** Offline regional map using bundled district boundaries and panel coordinates. */
export function BolgeHaritasi() {
  const { panels } = useFleet();
  const geoPanels = useMemo(() => panels.filter(hasCoords), [panels]);
  const outages = useOutages();

  return (
    <main className="page">
      <div className="hero">
        <h1>Bölge haritası</h1>
        {geoPanels.length >= 2 ? (
          <p>
            ADM ve GDZ hizmet bölgelerindeki panoları haritada keşfedin. İlçe
            sınırları turuncu, pano bulunan ilçeler hafif dolguyla gösterilir.
            Pano ayrıntıları için noktalara tıklayın; il ve ilçe seçerek
            görünümü daraltın.
          </p>
        ) : (
          <p>
            Dağıtım şirketine göre özet görünüm. Bu filoda konum verisi (
            <code>lat</code>/<code>lon</code>) henüz yeterli sayıda pano için
            dolu değil; gerçek harita karosu kullanılmaz (GK4: çevrimdışı).
          </p>
        )}
      </div>

      <div className="region-legend">
        {(["P1", "P2", "P3", "SYS"] as Prio[]).map((p) => (
          <span key={p}>
            <span
              className="region-dot"
              style={{
                background: PRIO_COLOR[p],
                width: 12,
                height: 12,
                display: "inline-block",
                borderRadius: 3,
                marginRight: 4,
              }}
            />
            {PRIO_NAME[p]}
          </span>
        ))}
        <span>
          <span
            className="region-dot normal"
            style={{
              width: 12,
              height: 12,
              display: "inline-block",
              borderRadius: 3,
              marginRight: 4,
            }}
          />
          Normal
        </span>
      </div>

      {outages.map((outage) => (
        <KesintiSeridi key={outage.outage_id} outage={outage} />
      ))}

      {geoPanels.length >= 2 ? (
        <GeoHarita
          panels={geoPanels}
          allCount={panels.length}
          outages={outages}
        />
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

function GeoHarita({
  panels,
  allCount,
  outages,
}: {
  panels: Geo[];
  allCount: number;
  outages: OutageEvent[];
}) {
  const [view, commitView] = useState({ scale: 1, tx: 0, ty: 0 });
  const pendingView = useRef(view);
  const frame = useRef<number | null>(null);
  const setView = useCallback(
    (next: typeof view | ((current: typeof view) => typeof view)) => {
      pendingView.current =
        typeof next === "function" ? next(pendingView.current) : next;
      if (frame.current !== null) return;
      frame.current = requestAnimationFrame(() => {
        frame.current = null;
        commitView(pendingView.current);
      });
    },
    [],
  );
  useEffect(
    () => () => {
      if (frame.current !== null) cancelAnimationFrame(frame.current);
    },
    [],
  );
  const [province, setProvince] = useState("");
  const [district, setDistrict] = useState("");
  const [query, setQuery] = useState("");
  const [hovered, setHovered] = useState<string | null>(null);
  const missing = allCount - panels.length;
  // Kesintiye dahil panolar (F-22): haritada kesikli bir HALKA ile isaretlenir —
  // sekil farki, yalnizca renk degil (ISA-101). Ayni bilgi yukaridaki kesinti
  // seridinde METIN olarak da durur, harita hic cizilmese bile ozellik yasar.
  const outagePanels = kesintidekiPanolar(outages);
  const provinceNames: Record<string, string> = {
    "09": "Aydın",
    "20": "Denizli",
    "35": "İzmir",
    "45": "Manisa",
    "48": "Muğla",
  };
  const geographicDistrict = (p: Geo) =>
    territoryEntries.find(([name]) =>
      insidePolygons({ x: p.lon, y: p.lat }, mapGeometry[name].geographic),
    )?.[0];
  const located = useMemo(
    () =>
      panels.map((p) => ({
        p,
        district: geographicDistrict(p),
        ...project(p.lon, p.lat),
      })),
    [panels],
  );
  const matchesRegion = (name: string, t: TerritoryEntry) =>
    (!province || t.plate === province) && (!district || name === district);
  const matchesQuery = (name: string, t: TerritoryEntry) =>
    !query.trim() ||
    normalize(`${name} ${provinceNames[t.plate]}`).includes(
      normalize(query.trim()),
    );
  const filtered = located.filter(({ p, district: name }) => {
    const t = name ? TERRITORY[name] : undefined;
    return (
      ((!province && !district) || (!!t && matchesRegion(name!, t))) &&
      (!query.trim() ||
        normalize(
          `${p.name} ${p.pano_id} ${name ?? ""} ${t ? provinceNames[t.plate] : ""}`,
        ).includes(normalize(query.trim())))
    );
  });
  const activeDistricts = new Set(filtered.map((point) => point.district));
  const matchingTerritories = territoryEntries.filter(
    ([name, t]) =>
      matchesRegion(name, t) &&
      (matchesQuery(name, t) || activeDistricts.has(name)),
  );
  const matchingNames = new Set(matchingTerritories.map(([name]) => name));
  const isFiltered = !!(province || district || query.trim());
  const panelDistricts = new Set(located.map((point) => point.district));
  const labelWidths = useMemo(() => {
    const context = document.createElement("canvas").getContext("2d");
    if (context) context.font = "600 11px Barlow";
    return new Map(
      territoryEntries.map(([name]) => [
        name,
        context?.measureText(name).width ?? name.length * 6.5,
      ]),
    );
  }, []);
  const candidates = useMemo(getPreparedLabels, []);
  // Panel pins always use supplied coordinates. District names are separate geographic
  // annotations placed inside their own polygon, never displaced into a neighbour.
  const visiblePoints = filtered
    .map((d) => ({
      ...d,
      x: d.x * view.scale + view.tx,
      y: d.y * view.scale + view.ty,
    }))
    .filter(
      (d) => d.x >= 12 && d.x <= MAP_W - 12 && d.y >= 12 && d.y <= MAP_H - 12,
    );
  const labelPositions = useMemo(
    () =>
      territoryEntries.flatMap(([name]) => {
        // Compact labels reveal narrow districts sooner; keep a readable minimum.
        for (const fontSize of [11, 10, 9]) {
          const width = (labelWidths.get(name)! * fontSize) / 11;
          const point = placePreparedLabel(
            candidates[name],
            width,
            fontSize,
            view.scale,
            located,
          );
          if (point)
            return [
              {
                name,
                width,
                fontSize,
                x: point.x * view.scale,
                y: point.y * view.scale,
              },
            ];
        }
        // No box fits cleanly at any size (narrow district): fall back to its
        // widest interior point at the smallest size instead of hiding the
        // name until the user zooms in — every district should be readable
        // at the initial view.
        const fallback = candidates[name]?.[0];
        if (!fallback) return [];
        const fontSize = 8;
        return [
          {
            name,
            width: (labelWidths.get(name)! * fontSize) / 11,
            fontSize,
            x: fallback.x * view.scale,
            y: fallback.y * view.scale,
          },
        ];
      }),
    [view.scale, located, labelWidths, candidates],
  );
  const regionLabels = labelPositions
    .map((label) => ({ ...label, x: label.x + view.tx, y: label.y + view.ty }))
    .filter(
      ({ name, x, y, width }) =>
        matchingNames.has(name) &&
        x > width / 2 + 8 &&
        x < MAP_W - width / 2 - 8 &&
        y > 20 &&
        y < MAP_H - 20,
    );
  const focusRegion = (plate: string, name: string) => {
    const entries = territoryEntries.filter(
      ([key, t]) => (!plate || t.plate === plate) && (!name || key === name),
    );
    if (!plate && !name) {
      setView({ scale: 1, tx: 0, ty: 0 });
      return;
    }
    const points = entries.flatMap(([, t]) =>
      ringsOf(t.geom)
        .flat()
        .map(([lon, lat]) => project(lon, lat)),
    );
    const minX = Math.min(...points.map((p) => p.x)),
      maxX = Math.max(...points.map((p) => p.x));
    const minY = Math.min(...points.map((p) => p.y)),
      maxY = Math.max(...points.map((p) => p.y));
    const scale = Math.max(
      1,
      Math.min(
        ZOOM_MAX,
        (MAP_W - 120) / (maxX - minX),
        (MAP_H - 100) / (maxY - minY),
      ),
    );
    setView({
      scale,
      tx: MAP_W / 2 - ((minX + maxX) / 2) * scale,
      ty: MAP_H / 2 - ((minY + maxY) / 2) * scale,
    });
  };

  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<{
    x: number;
    y: number;
    tx: number;
    ty: number;
  } | null>(null);

  const toSvgPoint = useCallback((clientX: number, clientY: number) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return { ux: MAP_W / 2, uy: MAP_H / 2 };
    return {
      ux: ((clientX - rect.left) / rect.width) * MAP_W,
      uy: ((clientY - rect.top) / rect.height) * MAP_H,
    };
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
      const delta =
        e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 620 : 1);
      zoomAt(ux, uy, Math.exp(-Math.max(-150, Math.min(150, delta)) * 0.0025));
    };
    svg.addEventListener("wheel", handler, { passive: false });
    return () => svg.removeEventListener("wheel", handler);
  }, [toSvgPoint, zoomAt]);

  // Zoom seviyesinden bagimsiz surukleme (kullanici talebi: "sadece zoom atinca surukleme
  // yapabiliyorum, zoom atmadan da surukleyebileyim") — scale===ZOOM_MIN kosulu kaldirildi.
  // setPointerCapture bazi durumlarda (gecersiz pointerId, zaten birakilmis pointer) firlatabilir —
  // bu, surukleme baslatmayi engellemesin diye try/catch'e alindi.
  const onPointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
    try {
      (e.target as Element).setPointerCapture(e.pointerId);
    } catch {
      // yakalama takibi olmadan da devam eder, yalnizca eleman disina cikildiginda surukleme kesilebilir
    }
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
      <div className="map-filter-bar" aria-label="Harita filtreleri">
        <label>
          İl
          <select
            value={province}
            onChange={(e) => {
              setProvince(e.target.value);
              setDistrict("");
              focusRegion(e.target.value, "");
            }}
          >
            <option value="">Tüm iller</option>
            {Object.entries(provinceNames)
              .sort((a, b) => a[1].localeCompare(b[1], "tr"))
              .map(([plate, name]) => (
                <option value={plate} key={plate}>
                  {name}
                </option>
              ))}
          </select>
        </label>
        <label>
          İlçe
          <select
            value={district}
            onChange={(e) => {
              const name = e.target.value;
              const plate = name ? TERRITORY[name].plate : province;
              setProvince(plate);
              setDistrict(name);
              focusRegion(plate, name);
            }}
          >
            <option value="">Tüm ilçeler</option>
            {territoryEntries
              .filter(([, t]) => !province || t.plate === province)
              .sort((a, b) => a[0].localeCompare(b[0], "tr"))
              .map(([name]) => (
                <option key={name}>{name}</option>
              ))}
          </select>
        </label>
        <label className="map-search">
          Bölgede ara
          <input
            type="search"
            placeholder="İl, ilçe, pano adı veya kodu"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        {isFiltered && (
          <button
            type="button"
            onClick={() => {
              setProvince("");
              setDistrict("");
              setQuery("");
              focusRegion("", "");
            }}
          >
            Temizle
          </button>
        )}
      </div>
      <div className="map-result-summary" aria-live="polite">
        <strong>{filtered.length} pano</strong>
        <span>
          {matchingTerritories.length} ilçe ·{" "}
          {isFiltered ? "Filtrelenmiş görünüm" : "ADM ve GDZ hizmet bölgesi"}
        </span>
      </div>
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
          onPointerCancel={onPointerUp}
          onPointerLeave={onPointerUp}
          style={{ cursor: "grab" }}
        >
          <rect
            className="geo-frame"
            x={1}
            y={1}
            width={MAP_W - 2}
            height={MAP_H - 2}
            rx={12}
          />
          <g
            transform={`translate(${view.tx} ${view.ty}) scale(${view.scale})`}
          >
            {/* Draw all fills first, then one solid orange boundary layer. */}
            {territoryEntries.map(([name, t]) => (
              <path
                key={`t-${name}`}
                className={`${panelDistricts.has(name) ? "geo-district" : "geo-territory"} ${isFiltered && !matchingNames.has(name) ? "map-muted" : ""} ${hovered === name ? "map-hovered" : ""}`}
                onPointerEnter={() => setHovered(name)}
                onPointerLeave={() => setHovered(null)}
                fillRule="evenodd"
                d={mapGeometry[name].path}
                vectorEffect="non-scaling-stroke"
              >
                <title>{`${name}, ${provinceNames[t.plate]} · ${COMPANY[t.company]}`}</title>
              </path>
            ))}

            <path
              className="geo-boundaries"
              d={boundaryPath}
              vectorEffect="non-scaling-stroke"
            />
          </g>
          <g className="geo-area-labels" aria-hidden="true">
            {regionLabels.map(({ name, x, y, fontSize }) => (
              <text
                key={name}
                className="geo-area-name"
                style={{ fontSize }}
                x={x}
                y={y}
                textAnchor="middle"
                dominantBaseline="central"
              >
                {name}
              </text>
            ))}
          </g>
          <g className="geo-annotations">
            {visiblePoints.map(({ x, y, p, district: location }) => {
              const prio = effectivePrio(p);
              const fider = outagePanels.get(p.pano_id);
              return (
                <Link
                  className="geo-marker"
                  key={p.pano_id}
                  to={`/pano/${p.pano_id}`}
                  onPointerEnter={() => setHovered(location ?? null)}
                  onPointerLeave={() => setHovered(null)}
                  onFocus={() => setHovered(location ?? null)}
                  onBlur={() => setHovered(null)}
                  aria-label={`${p.name} (${p.pano_id}), ${location ?? "ilçe eşleşmedi"}, risk ${p.risk_score}`}
                >
                  <title>{`${p.name} (${p.pano_id}) · Konum: ${location ?? "sınır dışında"} · Risk: ${p.risk_score}`}</title>
                  <circle className="geo-hit-area" cx={x} cy={y} r={11} />
                  {fider ? (
                    <circle className="geo-kesinti" cx={x} cy={y} r={13}>
                      <title>{`Üst şebeke kesintisi: ${fider}`}</title>
                    </circle>
                  ) : null}
                  <circle
                    className={prio ? "geo-dot" : "geo-dot normal"}
                    style={prio ? { fill: PRIO_COLOR[prio] } : undefined}
                    cx={x}
                    cy={y}
                    r={5.5}
                  />
                </Link>
              );
            })}
          </g>
          <g className="geo-compass" transform={`translate(${MAP_W - 46}, 40)`}>
            <line x1={0} y1={14} x2={0} y2={-14} />
            <path d="M -6 -6 L 0 -16 L 6 -6" />
            <text y={26} textAnchor="middle">
              K
            </text>
          </g>
        </svg>
        <div className="map-hover-readout" aria-live="polite">
          {hovered ? (
            <>
              <strong>{hovered}</strong>
              <span>
                {provinceNames[TERRITORY[hovered].plate]} ·{" "}
                {COMPANY[TERRITORY[hovered].company]}
              </span>
            </>
          ) : (
            <>
              <strong>
                {district ||
                  (province ? provinceNames[province] : "Ege hizmet bölgesi")}
              </strong>
              <span>İlçe bilgisi için haritanın üzerine gelin</span>
            </>
          )}
        </div>
        <div className="geo-zoom">
          <button
            type="button"
            onClick={() => zoomAt(MAP_W / 2, MAP_H / 2, 1.4)}
            aria-label="Yakınlaştır"
          >
            +
          </button>
          <button
            type="button"
            onClick={() => zoomAt(MAP_W / 2, MAP_H / 2, 1 / 1.4)}
            aria-label="Uzaklaştır"
          >
            −
          </button>
          {(view.scale > ZOOM_MIN || view.tx !== 0 || view.ty !== 0) && (
            <button
              type="button"
              onClick={() => setView({ scale: 1, tx: 0, ty: 0 })}
              aria-label="Haritayı sıfırla"
            >
              ⟲
            </button>
          )}
        </div>
      </div>
      {isFiltered && filtered.length === 0 && (
        <p className="map-empty">
          Bu seçimde konumu eşleşen pano bulunamadı. İlçe sınırlarını
          inceleyebilir veya filtreleri temizleyebilirsiniz.
        </p>
      )}
      {isFiltered && filtered.length > 0 && (
        <div className="map-panel-results">
          {filtered.map(({ p, district: name }) => (
            <Link to={`/pano/${p.pano_id}`} key={p.pano_id}>
              <strong>{p.name}</strong>
              <span>
                {p.pano_id} · {name ?? "İlçe eşleşmedi"}
              </span>
              <span>Risk {p.risk_score} →</span>
            </Link>
          ))}
        </div>
      )}
      <p className="dim small geo-note">
        İlçe sınırları: UN OCHA HDX{" "}
        <a
          href="https://data.humdata.org/dataset/cod-ab-tur"
          target="_blank"
          rel="noreferrer"
        >
          COD-AB-TUR
        </a>{" "}
        (CC BY-IGO), sadeleştirilmiş. Noktalar sağlanan koordinatları gösterir;
        örnek veride ilçe merkezi hassasiyetindedir. İlçe adları kendi sınırları
        içinde yer alır; çok dar ilçelerde ad daha küçük puntoyla gösterilir.
        İl/ilçe filtresi
        konumu sınırlarla eşleştirir. Mahalle verisi bulunmuyor. Fare
        tekerleğiyle veya +/− ile yakınlaştırabilir, sürükleyerek
        kaydırabilirsiniz.
        {missing > 0 &&
          ` ${missing} pano konum verisi olmadığı için haritada gösterilmiyor.`}
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
                {list.length} pano
                {attention ? `, ${attention} ilgi bekliyor` : ""}
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
                      style={
                        prio ? { background: PRIO_COLOR[prio] } : undefined
                      }
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
