import type { APIRequestContext } from "@playwright/test";

/**
 * Gezilecek rotalarin TEK kaynagi (K7 / 7.2).
 *
 * SINIR — bu dizin `frontend/tsconfig.json`in `include`una GIRMEZ (["src", "vite.config.ts"]),
 * yani buradaki kod `npm run build` sirasinda TIP DENETIMINDEN GECMEZ. Playwright TS'i
 * esbuild ile yalnizca SOYAR, denetlemez. Bu yuzden burada tip oyunu yapilmadi:
 * duz nesneler ve acik alanlar.
 */
export interface Rota {
  /** Rapor ve hata mesajlarinda gorunen ad. */
  ad: string;
  yol: string;
  /** h1 bu kalibi tutmali. Verilmezse yalnizca "hata ekranina dusmedi" denetlenir. */
  baslik?: RegExp;
  /** `assets/ekran/` altindaki dosya adi. Verilmezse goruntu alinmaz. */
  ekran?: string;
  /** NotFound gibi BILEREK hata ekrani bekleyen rotalar. */
  hataEkraniBekleniyor?: boolean;
}

/** Hata/bos durum h1'leri — basarili sayilan bir rotada bunlardan biri cikarsa test duser. */
export const HATA_BASLIGI = /bulunamadı|alınamadı|Henüz pano yok/i;

/**
 * App.tsx'teki YEDI ekran (+ NotFound). Parametreli iki rota (pano, olay) kip basina
 * farkli kimlik ister: mock kipinde kimlikler src/api/mock.ts'te SABIT, canli kipte
 * veritabanindan gelir ve UYDURULAMAZ — o yuzden canli kipte API'den KESFEDILIR.
 */
const SABIT_ROTALAR: Rota[] = [
  { ad: "Alarm konsolu", yol: "/alarmlar", baslik: /^Alarm merkezi$/, ekran: "03-alarm-konsolu.png" },
  { ad: "Trend ve korelasyon", yol: "/trend", baslik: /^Trend ve korelasyon$/, ekran: "04-trend-korelasyon.png" },
  { ad: "Cihaz sagligi", yol: "/cihaz-sagligi", baslik: /^Cihaz sağlığı$/, ekran: "06-cihaz-sagligi.png" },
  { ad: "Bolge haritasi", yol: "/bolge", baslik: /^Bölge haritası$/, ekran: "07-bolge-haritasi.png" },
  // Olay SECICI (kimliksiz /olay). Kara kutunun kendisi asagida, parametreli olarak.
  { ad: "Olay secici", yol: "/olay", baslik: /^Olay analizi — kara kutu$/ },
  // App.tsx:34 `path="*"`. Burada hata ekrani DOGRU sonuctur; yine de konsol
  // hatasi uretmemeli — 404 sayfasi patliyorsa bu bir kusurdur.
  { ad: "Bulunamayan rota", yol: "/boyle-bir-sayfa-yok", baslik: /^Sayfa bulunamadı$/, hataEkraniBekleniyor: true },
];

/**
 * Mock kipi kimlikleri src/api/mock.ts'ten BIREBIR alindi:
 *   ADM-00014 "Efeler TM-14" — P2 / ALM-K-ALM / risk 72  (mock.ts:65)  -> ALARM hali
 *   ADM-00057 "Bodrum TM-2"  — P3 / ALM-TTL-14D / risk 31 (mock.ts:70) -> sakin hali
 *   EVT-42                    — ADM-00014 uzerindeki kara kutu olayi   (mock.ts:381)
 *
 * "normal" icin risk 20'lik GDZ-00410 DEGIL, ADM-00057 secildi: GDZ-00410'un
 * `comms_ok` alani false, yani ekranda "Bağlantı yok" yazar — bu normal bir pano
 * degil, KOPUK bir panodur ve "normal" adli bir goruntuye girmesi yaniltici olurdu.
 */
function mockRotalari(): Rota[] {
  return [
    { ad: "Filo listesi", yol: "/", baslik: /^Operasyon özeti$/, ekran: "01-filo-listesi.png" },
    { ad: "Pano detay (sakin)", yol: "/pano/ADM-00057", baslik: /^Bodrum TM-2$/, ekran: "02-pano-detay-normal.png" },
    { ad: "Pano detay (alarmli)", yol: "/pano/ADM-00014", baslik: /^Efeler TM-14$/, ekran: "02-pano-detay-alarm.png" },
    { ad: "Olay analizi (kara kutu)", yol: "/olay/EVT-42", ekran: "05-olay-analizi-kara-kutu.png" },
    ...SABIT_ROTALAR,
  ];
}

/**
 * Canli kip: kimlikler UYDURULMAZ, calisan yiginin API'sinden okunur.
 * Kimlik bulunamazsa o rota LISTEYE GIRMEZ ve `atlanan` icinde NEDENIYLE raporlanir —
 * sessizce dusurmek, "7 rota gezildi" iddiasini yalan yapardi.
 */
export async function canliRotalari(
  request: APIRequestContext,
  taban: string,
): Promise<{ rotalar: Rota[]; atlanan: string[] }> {
  const atlanan: string[] = [];
  const rotalar: Rota[] = [{ ad: "Filo listesi", yol: "/", baslik: /^Operasyon özeti$/ }];

  let panolar: Array<{ pano_id: string; name?: string; risk_score?: number }> = [];
  try {
    const res = await request.get(`${taban}/api/v1/panels?sort=risk&limit=50`);
    if (res.ok()) panolar = await res.json();
    else atlanan.push(`GET /api/v1/panels -> HTTP ${res.status()}`);
  } catch (e) {
    atlanan.push(`GET /api/v1/panels -> ${String(e)}`);
  }

  if (panolar.length > 0) {
    // En yuksek ve en dusuk riskli pano: "alarmli" ve "sakin" hallerin canli karsiligi.
    const sirali = [...panolar].sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0));
    const alarmli = sirali[0];
    const sakin = sirali[sirali.length - 1];
    rotalar.push({ ad: `Pano detay (alarmli, ${alarmli.pano_id})`, yol: `/pano/${alarmli.pano_id}` });
    if (sakin.pano_id !== alarmli.pano_id) {
      rotalar.push({ ad: `Pano detay (sakin, ${sakin.pano_id})`, yol: `/pano/${sakin.pano_id}` });
    } else {
      atlanan.push("Pano detay (sakin): yiginda tek pano var, ikinci bir pano yok");
    }
  } else {
    atlanan.push("Pano detay: API hic pano dondurmedi");
  }

  let olayId: string | null = null;
  try {
    const res = await request.get(`${taban}/api/v1/alarms?state=active,acked,shelved,cleared&limit=500`);
    if (res.ok()) {
      const list: Array<{ event_id?: string | null }> = await res.json();
      olayId = list.find((a) => a.event_id)?.event_id ?? null;
    } else {
      atlanan.push(`GET /api/v1/alarms -> HTTP ${res.status()}`);
    }
  } catch (e) {
    atlanan.push(`GET /api/v1/alarms -> ${String(e)}`);
  }

  if (olayId) rotalar.push({ ad: `Olay analizi (kara kutu, ${olayId})`, yol: `/olay/${olayId}` });
  else atlanan.push("Olay analizi (kara kutu): yiginda `event_id` tasiyan alarm yok");

  rotalar.push(...SABIT_ROTALAR);
  return { rotalar, atlanan };
}

export { mockRotalari };
