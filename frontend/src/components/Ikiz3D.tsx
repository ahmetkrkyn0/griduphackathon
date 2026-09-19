import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import {
  CSS2DObject,
  CSS2DRenderer,
} from "three/addons/renderers/CSS2DRenderer.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { api } from "../api/client";
import type { ConnPoint, PointState, Tvoc } from "../api/types";
import { num } from "../lib/format";
import { STATE_TEXT, pointLabel } from "../lib/labels";
import {
  BAR_Y,
  DSYA_COUNT,
  FIRST_SPARE_DSYA,
  GIRIS_N_X,
  N_BAR_Y,
  PANEL_MM,
  dsyaX,
  girisX,
  pointPos3d,
} from "../lib/panelGeometry";

// Panonun 3D dijital ikizi (TC2 spike'inin uretim hali, frontend/sketches/ikiz-3d.html).
// three.js npm'den paketlenir (GK4: CDN yok). Geometri 2D on gorunusle ayni kaynaktan gelir
// (lib/panelGeometry.ts). Renkler tema token'larindan okunur; durum API'den (kural 10).
// Zaman kaydirici (Y1, TASARIM-REVIZYONU.md §4): gecmis K/K0 degerini, API'nin BUGUN verdigi
// durum rengiyle 1.0 taban grisi arasinda interpolasyonla gosterir. Yeni bir esik UYDURULMAZ —
// yalnizca "bu nokta o zamandan bu zamana ne kadar yol almis" oranini, zaten API'nin belirledigi
// iki uc nokta (taban 1.0 ve suanki durum) arasinda gosterir (kural 10 ile catismaz).

interface Props {
  points: ConnPoint[];
  selected: string | null;
  onSelect: (pt: string) => void;
  tvoc?: Tvoc | null;
  panoId: string;
  /** Onaylanmis alarma bagli noktalar: halka animasyonu durur (Y6, calm technology). */
  ackedPoints?: ReadonlySet<string>;
}

interface Toggles {
  cover: boolean;
  coverage: boolean;
  labels: boolean;
  thermal: boolean;
}

interface SceneApi {
  /** Veriyi sahneye yansitir; arizali dedektor bulunursa true doner. */
  update: (
    points: ConnPoint[],
    selected: string | null,
    tvoc: Tvoc | null,
    ackedPoints?: ReadonlySet<string>,
  ) => boolean;
  setToggles: (t: Toggles) => void;
  focusOn: (pt: string) => void;
  home: () => void;
  front: () => void;
  /** Zaman kaydirici onizlemesi: t=null canli veriye doner, 0..1 gecmisteki ilerlemeyi gosterir. */
  previewPoint: (pt: string, t: number | null) => void;
}

const H = PANEL_MM.height;
const PHASES = ["L1", "L2", "L3"] as const;
const DETECTOR_X = [260, 640, 1020, 1390];
const HOME_OFFSET = new THREE.Vector3(1250, 580, 3100);
const HOME_TARGET = new THREE.Vector3(0, 720, 0);
const ALL_POINTS = [
  ...Array.from({ length: DSYA_COUNT }, (_, i) =>
    PHASES.map((p) => `DSYA${i + 1}_${p}`),
  ).flat(),
  "GIRIS_L1",
  "GIRIS_L2",
  "GIRIS_L3",
  "GIRIS_N",
];

const isAbnormal = (s: PointState) =>
  s === "warn" || s === "alarm" || s === "critical";

function buildScene(
  stage: HTMLDivElement,
  tip: HTMLDivElement,
  onPick: (pt: string) => void,
) {
  const css = getComputedStyle(stage);
  const tok = (name: string, fallback: string) =>
    css.getPropertyValue(name).trim() || fallback;
  const colors: Record<PointState, string> = {
    normal: tok("--dot", "#16a34a"),
    warn: tok("--p3", "#c99700"),
    alarm: tok("--p2", "#e3650d"),
    critical: tok("--p1", "#a51c1c"),
    stale: tok("--line", "#c7cac3"),
  };
  const ours = tok("--ours", "#2c63c9");
  const device = tok("--device", "#5d646a");

  // WebGL yoksa burada hata firlatir; bilesen 2D'ye yonlendiren mesaji gosterir.
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.domElement.setAttribute("role", "img");
  renderer.domElement.setAttribute(
    "aria-label",
    "Panonun 3D dijital ikizi. Ölçüm noktalarının durumu aşağıdaki tabloda da listelenir.",
  );
  stage.appendChild(renderer.domElement);

  const labelRenderer = new CSS2DRenderer();
  Object.assign(labelRenderer.domElement.style, {
    position: "absolute",
    inset: "0",
    pointerEvents: "none",
  });
  stage.appendChild(labelRenderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color("#edf0f2");
  const environmentRoom = new RoomEnvironment();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const environmentTarget = pmrem.fromScene(environmentRoom, 0.04);
  scene.environment = environmentTarget.texture;
  scene.environmentIntensity = 0.7;
  environmentRoom.dispose();
  pmrem.dispose();

  const camera = new THREE.PerspectiveCamera(32, 1, 10, 30000);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.minDistance = 700;
  controls.maxDistance = 8000;
  controls.maxPolarAngle = Math.PI * 0.52;
  camera.position.copy(HOME_TARGET).add(HOME_OFFSET);
  controls.target.copy(HOME_TARGET);

  scene.add(new THREE.HemisphereLight("#ffffff", "#c9d0d6", 0.85));
  const sun = new THREE.DirectionalLight("#ffffff", 1.65);
  sun.position.set(1800, 3200, 2600);
  sun.castShadow = true;
  sun.shadow.mapSize.set(1024, 1024);
  Object.assign(sun.shadow.camera, {
    left: -1600,
    right: 1600,
    top: 2000,
    bottom: -400,
    near: 100,
    far: 8000,
  });
  scene.add(sun);
  // Yumusak dolgu isigi: guclu yonlu isigin sert golgesini hafifletir, metal yuzeylerde gercekci
  // ikinci bir yansima olusturur (fotograf stuyosu "fill light" mantigi).
  const fill = new THREE.DirectionalLight("#dce6ec", 0.55);
  fill.position.set(-1600, 900, 1600);
  scene.add(fill);

  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(9000, 9000),
    new THREE.ShadowMaterial({ opacity: 0.12 }),
  );
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  scene.add(floor);

  // Fiziksel malzemeler: pano govdesi RAL 7035, bakir, izolator. Durum rengi degil, malzeme rengi.
  // Gercekcilik gecisi (kullanici istegi): govdeye boyali sacin hafif parlakligini veren clearcoat,
  // baralara/DIN raya/bakira daha metalik degerler.
  const mat = {
    ral7035: new THREE.MeshPhysicalMaterial({
      color: "#CDD1CC",
      roughness: 0.78,
      metalness: 0.08,
      clearcoat: 0.35,
      clearcoatRoughness: 0.45,
    }),
    ral7035glass: new THREE.MeshStandardMaterial({
      color: "#CDD1CC",
      roughness: 0.85,
      transparent: true,
      opacity: 0.28,
      depthWrite: false,
    }),
    plate: new THREE.MeshStandardMaterial({ color: "#E2E5E1", roughness: 0.9 }),
    bar: new THREE.MeshStandardMaterial({
      color: "#B7865F",
      roughness: 0.32,
      metalness: 0.85,
    }),
    rail: new THREE.MeshStandardMaterial({
      color: "#B8BCC0",
      roughness: 0.25,
      metalness: 0.9,
    }),
    copper: new THREE.MeshStandardMaterial({
      color: "#B97A4D",
      roughness: 0.3,
      metalness: 0.9,
    }),
    dsya: new THREE.MeshStandardMaterial({ color: "#454C53", roughness: 0.6 }),
    face: new THREE.MeshStandardMaterial({ color: "#D9DCDD", roughness: 0.7 }),
    fuseCap: new THREE.MeshStandardMaterial({
      color: "#1B1E20",
      roughness: 0.4,
    }),
    insul: new THREE.MeshStandardMaterial({ color: "#3A4046", roughness: 0.7 }),
    cable: new THREE.MeshStandardMaterial({ color: "#23272B", roughness: 0.8 }),
    capBody: new THREE.MeshStandardMaterial({
      color: "#26292b",
      roughness: 0.35,
      metalness: 0.2,
    }) /* gercek kompanzasyon kondansatoru: koyu/siyah govde (referans foto) */,
    screen: new THREE.MeshStandardMaterial({
      color: "#102527",
      roughness: 0.22,
      metalness: 0.25,
    }),
    device: new THREE.MeshStandardMaterial({ color: device, roughness: 0.6 }),
    ours: new THREE.MeshStandardMaterial({ color: "#F4F6F8", roughness: 0.5 }),
    oursAccent: new THREE.MeshStandardMaterial({
      color: ours,
      roughness: 0.4,
      emissive: ours,
      emissiveIntensity: 0.25,
    }),
    cover: new THREE.MeshStandardMaterial({
      color: "#E8F0F4",
      roughness: 0.05,
      transparent: true,
      opacity: 0.16,
      depthWrite: false,
    }),
  };

  // Govde koordinatlari: x 0..1600, y 0..1500 (yukari), z 0..450 (on yuz). Kok grup ortalar.
  const root = new THREE.Group();
  root.position.set(-PANEL_MM.width / 2, 0, -PANEL_MM.depth / 2);
  scene.add(root);

  function box(
    w: number,
    h: number,
    d: number,
    m: THREE.Material,
    x: number,
    y: number,
    z: number,
    round = 0,
    shadow = true,
  ) {
    const geo = round
      ? new RoundedBoxGeometry(w, h, d, 2, round)
      : new THREE.BoxGeometry(w, h, d);
    const mesh = new THREE.Mesh(geo, m);
    mesh.position.set(x + w / 2, y + h / 2, z + d / 2);
    mesh.castShadow = shadow;
    mesh.receiveShadow = true;
    root.add(mesh);
    return mesh;
  }
  const allLabels: CSS2DObject[] = [];
  const staticLabels: CSS2DObject[] = [];
  function label(text: string, x: number, y: number, z: number, cls = "") {
    const el = document.createElement("div");
    el.className = `i3-lbl ${cls}`.trim();
    el.textContent = text;
    const obj = new CSS2DObject(el);
    obj.position.set(x, y, z);
    root.add(obj);
    allLabels.push(obj);
    return obj;
  }
  /** Kucuk durum LED'i (guc/veri gostergesi) — gercekci detay, olculu parlaklikta. */
  function led(colorHex: string, x: number, y: number, z: number) {
    const m = new THREE.MeshStandardMaterial({
      color: colorHex,
      emissive: colorHex,
      emissiveIntensity: 1.4,
      roughness: 0.3,
    });
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(4.5, 10, 8), m);
    mesh.position.set(x, y, z);
    root.add(mesh);
    return mesh;
  }

  // Govde (on kapaklar acik)
  box(1600, 1500, 20, mat.ral7035, 0, 0, 0);
  box(20, 1500, 450, mat.ral7035, 0, 0, 0);
  box(20, 1500, 450, mat.ral7035, 1580, 0, 0);
  box(1600, 20, 450, mat.ral7035, 0, 1480, 0);
  box(1600, 20, 450, mat.ral7035, 0, 0, 0);
  box(1560, 12, 430, mat.plate, 20, 1150, 20);
  box(1560, 900, 6, mat.plate, 20, 350, 22);

  // Folded steel frame, recessed base and fasteners give the enclosure its physical scale.
  box(1600, 65, 450, mat.insul, 0, -65, 0, 4);
  for (const x of [25, 1545]) {
    box(30, 1460, 20, mat.rail, x, 20, 410);
    for (const y of [70, 380, 760, 1140, 1440]) {
      const bolt = new THREE.Mesh(
        new THREE.CylinderGeometry(7, 7, 5, 6),
        mat.rail,
      );
      bolt.rotation.x = Math.PI / 2;
      bolt.position.set(x + 15, y, 433);
      root.add(bolt);
    }
  }
  box(1500, 25, 26, mat.ral7035, 50, 1460, 410);
  box(1500, 25, 26, mat.ral7035, 50, 5, 410);
  // Perforated wiring ducts and earth rail. Their colors denote materials, not measured status.
  for (const x of [40, 1250]) {
    box(34, 970, 32, mat.plate, x, 160, 55);
    for (let y = 180; y < 1100; y += 28)
      box(25, 7, 2, mat.insul, x + 4, y, 88, 0, false);
  }
  box(1470, 20, 8, mat.copper, 65, 95, 140);
  for (let x = 90; x < 1500; x += 80)
    box(10, 10, 8, mat.rail, x, 100, 148, 1, false);

  const equipmentTextures: THREE.Texture[] = [];
  function nameplate(
    text: string,
    sub: string,
    w: number,
    h: number,
    x: number,
    y: number,
    z: number,
  ) {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 160;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = "#e5e9e9";
    ctx.fillRect(0, 0, 512, 160);
    ctx.fillStyle = "#34444f";
    ctx.font = "600 38px sans-serif";
    ctx.fillText(text, 20, 58);
    ctx.font = "23px sans-serif";
    ctx.fillText(sub, 20, 107);
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    equipmentTextures.push(texture);
    const mesh = new THREE.Mesh(
      new THREE.PlaneGeometry(w, h),
      new THREE.MeshStandardMaterial({ map: texture, roughness: 0.8 }),
    );
    mesh.position.set(x, y, z);
    root.add(mesh);
  }
  nameplate(
    "AG DAGITIM PANOSU",
    "1600 x 1500 x 450 mm",
    360,
    108,
    290,
    1400,
    32,
  );

  // Ust bolme: DIN ray, TVOC-2, Pano Beyni, modem, sigortalar, kompanzasyon, MPR-53CS
  // DIN ray: gercek TS35 profiline yakin siluet (duz kutu degil) — govde ic cekilmis, alt/ust
  // kenarlar one cikintili; parlak galvanizli celik malzeme.
  box(1480, 4, 10, mat.rail, 60, 1300, 38);
  box(1480, 27, 7, mat.rail, 60, 1304, 40);
  box(1480, 4, 10, mat.rail, 60, 1327, 38);
  box(170, 95, 70, mat.device, 90, 1270, 48, 6);
  // HMI dokunmatik ekran: ABB Arc Guard TVOC-2 govdesinin on yuzunun cogunu kaplayan
  // gercek ekran alani (tam olcu dokumantasyonu erisilemedi — makul oran tahmini,
  // TASARIM-REVIZYONU.md §15). Ekran + ince cerceve olarak modellendi, buton yok (dokunmatik).
  box(120, 66, 3, mat.insul, 105, 1284, 118, 2);
  box(112, 58, 2, mat.screen, 109, 1288, 121, 1);
  const tvocLed = led("#2ecc71", 250, 1350, 119);
  staticLabels.push(label("TVOC-2", 175, 1395, 90));
  box(150, 95, 64, mat.ours, 320, 1270, 48, 8);
  box(150, 12, 4, mat.oursAccent, 320, 1340, 112);
  led("#2ecc71", 340, 1350, 117);
  staticLabels.push(label("Pano Beyni", 395, 1405, 90, "ours"));
  box(120, 80, 55, mat.device, 520, 1275, 48, 6);
  led("#657a85", 632, 1345, 104);
  staticLabels.push(label("Modem", 580, 1385, 80));
  for (let i = 0; i < 5; i++) {
    box(28, 75, 60, mat.face, 700 + i * 36, 1280, 48, 3);
    box(16, 20, 8, mat.insul, 706 + i * 36, 1300, 108, 2);
    box(20, 4, 3, mat.rail, 704 + i * 36, 1342, 108, 0, false);
  }
  for (let i = 0; i < 3; i++) {
    const cx = 1030 + i * 110;
    const c = new THREE.Mesh(
      new THREE.CylinderGeometry(42, 42, 230, 32),
      mat.capBody,
    );
    c.position.set(cx, 1277, 250);
    c.castShadow = true;
    root.add(c);
    nameplate("CAP", "KOMPANZASYON", 45, 26, cx, 1280, 292);
    // Kondansator kivrim bantlari: govde uzerinde iki ince koyu halka.
    for (const ry of [1277 - 62, 1277 + 62]) {
      const band = new THREE.Mesh(
        new THREE.CylinderGeometry(42.6, 42.6, 9, 32),
        mat.insul,
      );
      band.position.set(cx, ry, 250);
      root.add(band);
    }
  }
  staticLabels.push(label("Kompanzasyon", 1140, 1430, 250));
  // ENTES MPR-53CS-DIN/96: dogrulanmis 96x96mm DIN panel format (urun sayfasi). On yuzde
  // 3 satirlik LCD (L1/L2/L3 degerleri) + sag altta 4 gezinme tusu — gercek cihaz duzenine
  // yakin sadelestirilmis temsil.
  box(96, 96, 30, mat.device, 1400, 1300, 420, 4);
  box(70, 46, 3, mat.insul, 1413, 1330, 450, 1);
  box(64, 40, 2, mat.screen, 1416, 1333, 453, 0);
  for (let i = 0; i < 4; i++)
    box(8, 8, 3, mat.insul, 1413 + i * 12, 1306, 450, 1);
  staticLabels.push(label("MPR-53CS", 1448, 1425, 450));

  // Ana baralar ve giris
  for (const p of PHASES) {
    const y = H - BAR_Y[p];
    box(1500, 100, 10, mat.bar, 50, y - 50, 140);
    box(1500, 100, 10, mat.bar, 50, y - 50, 158);
  }
  const nY = H - N_BAR_Y;
  box(1500, 60, 10, mat.bar, 50, nY - 30, 150);
  for (const x of [60, 1240])
    box(24, 520, 40, mat.insul, x - 12, H - BAR_Y.L3 - 60, 120);
  PHASES.forEach((p, i) => {
    const y = H - BAR_Y[p];
    box(50, 1480 - y, 10, mat.bar, girisX((i + 1) as 1 | 2 | 3) - 25, y, 180);
  });
  box(40, 1480 - nY, 10, mat.bar, GIRIS_N_X - 20, nY, 185);
  staticLabels.push(
    label("Ana baralar 2 × 100×10 mm", 1400, H - BAR_Y.L3 - 80, 200),
  );

  // DSYA seritleri, kablo pabuclari, kablolar
  const lugY = pointPos3d("DSYA1_L1")!.y;
  for (let n = 1; n <= DSYA_COUNT; n++) {
    const x = dsyaX(n);
    const spare = n >= FIRST_SPARE_DSYA;
    box(104, 660, 130, mat.dsya, x - 52, lugY + 40, 190, 6);
    for (const p of PHASES) {
      const fy = H - BAR_Y[p] - 60;
      box(80, 120, 8, mat.face, x - 40, fy, 320, 3);
      if (!spare) {
        // Sigorta govdesi + tutamak: DSYA bir MCB degil, NH bicak sigortali dikey yuk ayiricidir
        // (arastirma sonrasi duzeltildi — Etien DSYA urun sayfasi, TASARIM-REVIZYONU.md §15).
        // Yuzeyden disari dogru cikan silindirik sigorta govdesi + ucundaki cekme tutamagi.
        // Ceramic NH cartridge with metal blade contacts and a recessed lifting grip.
        box(52, 76, 36, mat.face, x - 26, fy + 22, 331, 3);
        box(62, 13, 42, mat.rail, x - 31, fy + 17, 329, 2);
        box(62, 13, 42, mat.rail, x - 31, fy + 94, 329, 2);
        box(14, 33, 7, mat.fuseCap, x - 7, fy + 44, 366, 2);
        for (const bx of [x - 30, x + 30]) {
          const screw = new THREE.Mesh(
            new THREE.CylinderGeometry(4, 4, 4, 6),
            mat.rail,
          );
          screw.rotation.x = Math.PI / 2;
          screw.position.set(bx, fy + 9, 331);
          root.add(screw);
        }
      }
    }
    staticLabels.push(
      label(spare ? `${n} yedek` : `DSYA-${n}`, x, lugY + 720, 330),
    );
    PHASES.forEach((_, i) => {
      const lx = x + (i - 1) * 30;
      box(20, 44, 16, mat.copper, lx - 10, lugY - 22, 250);
      // Baglanti civatasi: pabucun on yuzunde kucuk bir civata basi.
      const bolt = new THREE.Mesh(
        new THREE.CylinderGeometry(5, 5, 5, 8),
        mat.insul,
      );
      bolt.rotation.x = Math.PI / 2;
      bolt.position.set(lx, lugY - 4, 266 + 2.5);
      bolt.castShadow = true;
      root.add(bolt);
      if (!spare) {
        // Kablo: dumduz silindir yerine hafif sarkan (dogal agirlikla bukulen) bir tup.
        const yTop = lugY - 22,
          yBot = 20;
        const curve = new THREE.CatmullRomCurve3([
          new THREE.Vector3(lx, yBot, 258),
          new THREE.Vector3(lx + (i - 1) * 5, (yBot + yTop) / 2, 258 + 13),
          new THREE.Vector3(lx, yTop, 258),
        ]);
        const cab = new THREE.Mesh(
          new THREE.TubeGeometry(curve, 16, 9, 8, false),
          mat.cable,
        );
        cab.castShadow = true;
        root.add(cab);
      }
    });
  }
  staticLabels.push(label("Kablo bölgesi en az 400 mm", 700, 60, 420));

  // Bizim donanimimiz: ortam dugumleri ve termal dizi
  box(60, 40, 30, mat.ours, 770, 70, 390, 6);
  staticLabels.push(label("Ortam düğümü, alt", 800, 150, 420, "ours"));
  box(60, 40, 30, mat.ours, 900, 1420, 390, 6);
  staticLabels.push(label("Ortam düğümü, üst", 930, 1470, 420, "ours"));
  box(46, 28, 26, mat.ours, 777, 1110, 400, 5);
  staticLabels.push(
    label("Termal dizi, kapağın içinde", 800, 1060, 440, "ours"),
  );

  // Olcum noktasi dugumleri (25 nokta, sozlesme listesi)
  const nodeGeo = new RoundedBoxGeometry(34, 40, 30, 2, 6);
  const edgeGeo = new THREE.EdgesGeometry(new THREE.BoxGeometry(50, 56, 46));
  const haloGeo = new THREE.SphereGeometry(52, 24, 16);
  const edgeMat = new THREE.LineBasicMaterial({ color: ours });
  interface Node {
    pt: string;
    mesh: THREE.Mesh<RoundedBoxGeometry, THREE.MeshStandardMaterial>;
    halo: THREE.Mesh<THREE.SphereGeometry, THREE.MeshBasicMaterial>;
    edge: THREE.LineSegments;
    state: PointState;
    point: ConnPoint | null;
    acked: boolean;
    /** null = canli; 0..1 = zaman kaydiricisinin gosterdigi gecmis ilerleme (Y1). */
    previewT: number | null;
  }
  const nodes = new Map<string, Node>();
  const nodeByMesh = new Map<THREE.Object3D, Node>();
  for (const pt of ALL_POINTS) {
    const pos = pointPos3d(pt);
    if (!pos) continue;
    const mesh = new THREE.Mesh(
      nodeGeo,
      new THREE.MeshStandardMaterial({ color: colors.stale, roughness: 0.45 }),
    );
    mesh.position.set(pos.x, pos.y, pos.z);
    mesh.castShadow = true;
    const halo = new THREE.Mesh(
      haloGeo,
      new THREE.MeshBasicMaterial({
        transparent: true,
        opacity: 0,
        depthWrite: false,
      }),
    );
    halo.visible = false;
    const edge = new THREE.LineSegments(edgeGeo, edgeMat);
    edge.visible = false;
    mesh.add(halo, edge);
    root.add(mesh);
    const node: Node = {
      pt,
      mesh,
      halo,
      edge,
      state: "stale",
      point: null,
      acked: false,
      previewT: null,
    };
    nodes.set(pt, node);
    nodeByMesh.set(mesh, node);
  }
  const c0 = new THREE.Color("#3b528b");
  const c1 = new THREE.Color("#21918c");
  const c2 = new THREE.Color("#fde725");
  const c3 = new THREE.Color("#d62728");
  function getThermalColor(dt: number): THREE.Color {
    const c = new THREE.Color();
    if (dt <= 5) return c.copy(c0);
    if (dt <= 20) return c.lerpColors(c0, c1, (dt - 5) / 15);
    if (dt <= 40) return c.lerpColors(c1, c2, (dt - 20) / 20);
    if (dt <= 65) return c.lerpColors(c2, c3, (dt - 40) / 25);
    return c.copy(c3);
  }

  let thermalMode = false;
  const previewColor = new THREE.Color();
  /** Bir dugumun rengini/halkasini canli duruma veya zaman kaydirici onizlemesine gore boyar. */
  function paintNode(n: Node) {
    if (thermalMode && n.point) {
      const dt = Math.max(0, n.point.dt_c ?? 0);
      const thCol = getThermalColor(dt);
      n.mesh.material.color.copy(thCol);
      n.mesh.material.emissive.copy(thCol);
      n.mesh.material.emissiveIntensity = dt > 15 ? 0.35 : 0.05;
      n.halo.visible = false;
      return;
    }
    const stateColor = colors[n.state];
    const abnormal = isAbnormal(n.state);
    if (n.previewT != null && abnormal) {
      previewColor
        .set(colors.normal)
        .lerp(new THREE.Color(stateColor), n.previewT);
      n.mesh.material.color.copy(previewColor);
      n.mesh.material.emissive.copy(previewColor);
      n.mesh.material.emissiveIntensity = 0.3 * n.previewT;
      n.halo.visible = false;
      return;
    }
    n.mesh.material.color.set(stateColor);
    n.mesh.material.emissive.set(abnormal ? stateColor : "#000000");
    n.mesh.material.emissiveIntensity = abnormal ? 0.35 : 0;
    n.halo.material.color.set(stateColor);
    n.halo.visible = abnormal && !n.acked;
    n.halo.material.opacity = abnormal && !n.acked ? 0.22 : 0;
    n.halo.scale.setScalar(1);
  }
  const selectedLabel = label("", 0, 0, 0, "ours");
  selectedLabel.visible = false;

  // TVOC-2 ark dedektorleri ve kapsama konileri
  const detectors = DETECTOR_X.map((x, i) => {
    const id = `X2:${i + 1}`;
    const body = new THREE.Mesh(
      new THREE.CylinderGeometry(12, 12, 30, 16),
      new THREE.MeshStandardMaterial({ color: device, roughness: 0.6 }),
    );
    body.position.set(x, 1125, 380);
    root.add(body);
    const cone = new THREE.Mesh(
      new THREE.ConeGeometry(330, 700, 32, 1, true),
      new THREE.MeshBasicMaterial({
        color: ours,
        transparent: true,
        opacity: 0.07,
        side: THREE.DoubleSide,
        depthWrite: false,
      }),
    );
    cone.position.set(x, 1125 - 350, 380);
    cone.visible = false;
    root.add(cone);
    const tag = label(id, x, 1170, 395);
    tag.visible = false;
    return { id, body, cone, tag, broken: false };
  });

  // Saydam kapak (polikarbonat)
  const cover = box(1560, 720, 6, mat.cover, 20, 430, 436, 0, false);

  // --- Kamera gecisleri ve cizim dongusu ---
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let dirty = true;
  let fly: {
    p0: THREE.Vector3;
    t0: THREE.Vector3;
    p1: THREE.Vector3;
    t1: THREE.Vector3;
    k: number;
  } | null = null;
  const flyTo = (pos: THREE.Vector3, target: THREE.Vector3) => {
    fly = {
      p0: camera.position.clone(),
      t0: controls.target.clone(),
      p1: pos,
      t1: target,
      k: 0,
    };
  };
  // Dar ekranda (dikey oran) govde sigsin diye kamerayi geri cek.
  const fit = () => Math.max(1, 1.2 / camera.aspect);
  controls.addEventListener("change", () => {
    dirty = true;
  });

  // Ekranda cakisan etiketlerden onemsiz olani gizle: secili > arizali > bizim donanim > diger.
  const rank = (o: CSS2DObject) =>
    o === selectedLabel
      ? 0
      : o.element.classList.contains("bad")
        ? 1
        : o.element.classList.contains("ours")
          ? 2
          : 3;
  function declutter() {
    const placed: DOMRect[] = [];
    for (const o of [...allLabels].sort((a, b) => rank(a) - rank(b))) {
      const el = o.element;
      el.style.visibility = "";
      if (!o.visible || el.style.display === "none") continue;
      const r = el.getBoundingClientRect();
      if (
        placed.some(
          (p) =>
            r.left < p.right &&
            r.right > p.left &&
            r.top < p.bottom &&
            r.bottom > p.top,
        )
      )
        el.style.visibility = "hidden";
      else placed.push(r);
    }
  }

  const clock = new THREE.Clock();
  renderer.setAnimationLoop(() => {
    const dt = clock.getDelta();
    const t = clock.elapsedTime;
    if (fly) {
      fly.k = Math.min(1, fly.k + dt / (reduced ? 0.01 : 1.1));
      const e = 1 - Math.pow(1 - fly.k, 3);
      camera.position.lerpVectors(fly.p0, fly.p1, e);
      controls.target.lerpVectors(fly.t0, fly.t1, e);
      if (fly.k >= 1) fly = null;
      dirty = true;
    }
    controls.update();
    let pulsing = false;
    if (!reduced) {
      const s = Math.sin(t * 4);
      for (const n of nodes.values()) {
        if (!isAbnormal(n.state) || n.acked || n.previewT != null) continue;
        pulsing = true;
        n.halo.material.opacity = 0.14 + 0.12 * s;
        n.halo.scale.setScalar(n.state === "warn" ? 0.85 : 1 + 0.15 * s);
      }
      for (const d of detectors) {
        if (!d.broken || !d.cone.visible) continue;
        pulsing = true;
        d.cone.material.opacity = 0.14 + 0.08 * Math.sin(t * 5);
      }
    }
    if (!dirty && !pulsing) return;
    dirty = false;
    renderer.render(scene, camera);
    labelRenderer.render(scene, camera);
    declutter();
  });

  const resize = () => {
    const w = stage.clientWidth;
    const h = stage.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h);
    labelRenderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    dirty = true;
  };
  const observer = new ResizeObserver(resize);
  observer.observe(stage);
  resize();
  camera.position.copy(HOME_TARGET).addScaledVector(HOME_OFFSET, fit());

  // --- Isaretleme: surukleme ile tiklamayi ayir ---
  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  const meshes = [...nodes.values()].map((n) => n.mesh);
  const pick = (e: PointerEvent) => {
    const r = renderer.domElement.getBoundingClientRect();
    ndc.set(
      ((e.clientX - r.left) / r.width) * 2 - 1,
      -((e.clientY - r.top) / r.height) * 2 + 1,
    );
    ray.setFromCamera(ndc, camera);
    const hit = ray.intersectObjects(meshes, false)[0];
    return { node: hit ? nodeByMesh.get(hit.object) : undefined, r };
  };
  const onMove = (e: PointerEvent) => {
    const { node, r } = pick(e);
    renderer.domElement.style.cursor = node ? "pointer" : "";
    tip.hidden = !node;
    if (!node) return;
    const name = node.point?.label ?? pointLabel(node.pt);
    tip.textContent = node.point
      ? `${name}: ${num(node.point.t_c)} °C, ${STATE_TEXT[node.state]}`
      : `${name}: veri yok`;
    tip.style.left = `${e.clientX - r.left + 14}px`;
    tip.style.top = `${e.clientY - r.top + 10}px`;
  };
  let down: { x: number; y: number } | null = null;
  const onDown = (e: PointerEvent) => {
    down = { x: e.clientX, y: e.clientY };
  };
  const onUp = (e: PointerEvent) => {
    const start = down;
    down = null;
    if (!start || Math.hypot(e.clientX - start.x, e.clientY - start.y) > 5)
      return;
    const { node } = pick(e);
    if (node) onPick(node.pt);
  };
  const onLeave = () => {
    tip.hidden = true;
  };
  const canvas = renderer.domElement;
  canvas.addEventListener("pointermove", onMove);
  canvas.addEventListener("pointerdown", onDown);
  canvas.addEventListener("pointerup", onUp);
  canvas.addEventListener("pointerleave", onLeave);

  const api: SceneApi = {
    update(points, selected, tvoc, ackedPoints) {
      const byPt = new Map(points.map((p) => [p.pt, p]));
      for (const n of nodes.values()) {
        const p = byPt.get(n.pt) ?? null;
        n.point = p;
        n.state = p ? (p.state ?? "normal") : "stale";
        n.acked = ackedPoints?.has(n.pt) ?? false;
        paintNode(n);
        const sel = n.pt === selected;
        n.edge.visible = sel;
        n.mesh.scale.setScalar(sel ? 1.25 : 1);
      }
      const sel = selected ? nodes.get(selected) : undefined;
      selectedLabel.visible = !!sel;
      if (sel) {
        selectedLabel.position
          .copy(sel.mesh.position)
          .add(new THREE.Vector3(0, -70, 20));
        selectedLabel.element.textContent =
          sel.point?.label ?? pointLabel(sel.pt);
      }

      // TVOC-2 govde LED'i: koruma sagligi API'den geliyor (kural 10), renk burada uydurulmuyor.
      const tvocHealthy = tvoc?.prot_health_ok !== false;
      tvocLed.material.color.set(tvocHealthy ? "#2ecc71" : colors.critical);
      tvocLed.material.emissive.set(tvocHealthy ? "#2ecc71" : colors.critical);

      // Koruma sagligi: arizali dedektor etiketi API'den gelir (ornek: "X2:4").
      const brokenNo =
        tvoc?.prot_health_ok === false
          ? /X2:(\d)/.exec(tvoc.last_det_label ?? "")?.[1]
          : undefined;
      for (const [i, d] of detectors.entries()) {
        d.broken = brokenNo === String(i + 1);
        d.cone.material.color.set(d.broken ? colors.critical : ours);
        d.cone.material.opacity = d.broken ? 0.2 : 0.07;
        d.body.material.color.set(d.broken ? colors.critical : device);
        d.tag.element.className = d.broken ? "i3-lbl bad" : "i3-lbl";
        d.tag.element.textContent = d.broken
          ? `${d.id} arızalı, bu bölge korumasız`
          : d.id;
      }
      dirty = true;
      return brokenNo !== undefined;
    },
    setToggles({ cover: showCover, coverage, labels, thermal }) {
      cover.visible = showCover;
      for (const d of detectors) {
        d.cone.visible = coverage;
        d.tag.visible = coverage;
      }
      for (const l of staticLabels) l.visible = labels;
      if (thermalMode !== thermal) {
        thermalMode = thermal;
        for (const n of nodes.values()) paintNode(n);
      }
      dirty = true;
    },
    focusOn(pt) {
      const n = nodes.get(pt);
      if (!n) return;
      const target = n.mesh.getWorldPosition(new THREE.Vector3());
      flyTo(
        target
          .clone()
          .addScaledVector(new THREE.Vector3(650, 380, 1900), fit()),
        target,
      );
    },
    home() {
      flyTo(
        HOME_TARGET.clone().addScaledVector(HOME_OFFSET, fit()),
        HOME_TARGET.clone(),
      );
    },
    front() {
      flyTo(
        new THREE.Vector3(0, 750, 4200 * fit()),
        new THREE.Vector3(0, 750, 0),
      );
    },
    previewPoint(pt, t) {
      const n = nodes.get(pt);
      if (!n) return;
      n.previewT = t;
      paintNode(n);
      dirty = true;
    },
  };

  const dispose = () => {
    renderer.setAnimationLoop(null);
    observer.disconnect();
    canvas.removeEventListener("pointermove", onMove);
    canvas.removeEventListener("pointerdown", onDown);
    canvas.removeEventListener("pointerup", onUp);
    canvas.removeEventListener("pointerleave", onLeave);
    controls.dispose();
    const geometries = new Set<THREE.BufferGeometry>();
    const materials = new Set<THREE.Material>();
    scene.traverse((o) => {
      if (o instanceof THREE.Mesh || o instanceof THREE.LineSegments) {
        geometries.add(o.geometry);
        for (const m of Array.isArray(o.material) ? o.material : [o.material])
          materials.add(m);
      }
    });
    geometries.forEach((g) => g.dispose());
    materials.forEach((m) => m.dispose());
    equipmentTextures.forEach((texture) => texture.dispose());
    environmentTarget.dispose();
    renderer.dispose();
    stage.replaceChildren();
  };

  return { api, dispose };
}

interface HistorySample {
  t: number;
  k: number;
}

const HISTORY_DAYS = 14;

export function Ikiz3D({
  points,
  selected,
  onSelect,
  tvoc,
  panoId,
  ackedPoints,
}: Props) {
  const stageRef = useRef<HTMLDivElement>(null);
  const tipRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<SceneApi | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const previewedPt = useRef<string | null>(null);
  const autoCoverage = useRef(false);
  const [failed, setFailed] = useState(false);
  const [toggles, setToggles] = useState<Toggles>({
    cover: true,
    coverage: false,
    labels: true,
    thermal: false,
  });
  const [history, setHistory] = useState<HistorySample[]>([]);
  const [sliderPos, setSliderPos] = useState(1);

  useEffect(() => {
    const stage = stageRef.current;
    const tip = tipRef.current;
    if (!stage || !tip) return;
    let built: ReturnType<typeof buildScene>;
    try {
      built = buildScene(stage, tip, (pt) => onSelectRef.current(pt));
    } catch {
      setFailed(true);
      return;
    }
    sceneRef.current = built.api;
    return () => {
      sceneRef.current = null;
      previewedPt.current = null;
      built.dispose();
    };
  }, []);

  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;
    const broken = scene.update(points, selected, tvoc ?? null, ackedPoints);
    if (broken && !autoCoverage.current) {
      autoCoverage.current = true;
      setToggles((t) => ({ ...t, coverage: true }));
    }
  }, [points, selected, tvoc, ackedPoints]);

  useEffect(() => {
    sceneRef.current?.setToggles(toggles);
  }, [toggles]);

  // Y1: secili noktanin 14 gunluk K/K0 gecmisini cek. Yeni nokta secilince kaydirici "simdi"ye doner.
  useEffect(() => {
    setHistory([]);
    setSliderPos(1);
    if (!selected) return;
    const controller = new AbortController();
    const to = new Date();
    const from = new Date(to.getTime() - HISTORY_DAYS * 86_400_000);
    api
      .series(
        panoId,
        [`t_conn.${selected}.k_ratio`],
        from,
        to,
        "1h",
        controller.signal,
      )
      .then((data) => {
        const tag = `t_conn.${selected}.k_ratio`;
        const samples = (data[tag] ?? [])
          .filter((p): p is [number, number] => p[1] != null)
          .map(([t, k]) => ({ t, k }));
        setHistory(samples);
      })
      .catch(() => {
        if (!controller.signal.aborted) setHistory([]);
      });
    return () => controller.abort();
  }, [panoId, selected]);

  const focusPoint = selected
    ? (points.find((p) => p.pt === selected) ?? null)
    : null;
  const liveK = focusPoint?.k_ratio ?? null;
  const liveAbnormal = !!focusPoint?.state && isAbnormal(focusPoint.state);
  const showSlider =
    !!selected &&
    liveAbnormal &&
    liveK != null &&
    liveK > 1.02 &&
    history.length >= 2;
  const activeIdx =
    history.length > 0 ? Math.round(sliderPos * (history.length - 1)) : -1;
  const activeSample = activeIdx >= 0 ? history[activeIdx] : null;

  // Onizleme rengini sahneye yansit: t=null -> canli, aksi halde gecmis/canli oranini gonder.
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;
    if (previewedPt.current && previewedPt.current !== selected) {
      scene.previewPoint(previewedPt.current, null);
      previewedPt.current = null;
    }
    if (!selected) return;
    if (!showSlider || sliderPos >= 0.999 || !activeSample || liveK == null) {
      scene.previewPoint(selected, null);
      previewedPt.current = null;
      return;
    }
    const t = Math.min(1, Math.max(0, (activeSample.k - 1) / (liveK - 1)));
    scene.previewPoint(selected, t);
    previewedPt.current = selected;
  }, [selected, showSlider, sliderPos, activeSample, liveK]);

  const flip = (key: keyof Toggles) =>
    setToggles((t) => ({ ...t, [key]: !t[key] }));

  const timeReadout = !showSlider
    ? ""
    : sliderPos >= 0.999 || !activeSample
      ? `Şimdi · K/K₀ ${liveK != null ? num(liveK, 2) : "—"}`
      : (() => {
          const daysAgo = Math.max(
            0,
            Math.round((Date.now() - activeSample.t) / 86_400_000),
          );
          return `${daysAgo > 0 ? `${daysAgo} gün önce` : "Bugün"} · K/K₀ ${num(activeSample.k, 2)}`;
        })();

  return (
    <div className="i3">
      <div className="i3-stage" ref={stageRef} />
      <div className="i3-tip" ref={tipRef} hidden />
      {failed ? (
        <p className="i3-fail">
          Bu tarayıcıda 3D görünüm (WebGL) açılamadı. Ön görünüş aynı bilgiyi
          gösterir.
        </p>
      ) : (
        <div className="i3-controls">
          {showSlider && (
            <div
              className="i3-time"
              role="group"
              aria-label={`${pointLabel(selected!)} zaman kaydırıcısı`}
            >
              <span className="i3-time-edge">{HISTORY_DAYS} gün önce</span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.001}
                value={sliderPos}
                onChange={(e) => setSliderPos(Number(e.target.value))}
                aria-label={`Zaman: ${timeReadout}`}
              />
              <span className="i3-time-edge">Şimdi</span>
              <span className="i3-time-readout">{timeReadout}</span>
            </div>
          )}
          <div
            className="i3-bar"
            role="toolbar"
            aria-label="3D ikiz kontrolleri"
          >
            <button
              type="button"
              aria-pressed={toggles.cover}
              onClick={() => flip("cover")}
            >
              Saydam kapak
            </button>
            <button
              type="button"
              aria-pressed={toggles.coverage}
              onClick={() => flip("coverage")}
            >
              Ark koruma kapsaması
            </button>
            <button
              type="button"
              aria-pressed={toggles.labels}
              onClick={() => flip("labels")}
            >
              Etiketler
            </button>
            <button type="button" aria-pressed={toggles.thermal} onClick={() => flip("thermal")}>
              Termal görünüm
            </button>
            <span className="i3-sep" />
            <button type="button" onClick={() => sceneRef.current?.home()}>
              3/4 görünüş
            </button>
            <button type="button" onClick={() => sceneRef.current?.front()}>
              Önden
            </button>
            {selected && (
              <button
                type="button"
                onClick={() => sceneRef.current?.focusOn(selected)}
              >
                Seçili noktaya odaklan
              </button>
            )}
          </div>
          {toggles.thermal && (
            <div className="i3-thermal-scale" aria-label="Termal renk skalası">
              <span className="i3-thermal-bar" />
              <div className="i3-thermal-labels">
                <span>0 °C</span>
                <span>20 °C</span>
                <span>40 °C</span>
                <span>65+ °C ΔT</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
