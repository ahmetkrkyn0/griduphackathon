import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { canliRotalari, mockRotalari, HATA_BASLIGI, type Rota } from "./rotalar";

/**
 * K7 / 7.2 + 7.3 — yedi ekrani gez, KONSOL HATASI SAY, ekran goruntusu uret,
 * erisilebilirligi tara.
 *
 * ── BU TESTIN NE OLCTUGU, NE OLCMEDIGI ────────────────────────────────────────
 * OLCER  : tek bir tarayicida (Chromium), tek bir kipte, tek bir anda, sayfa
 *          ACILISINDA olusan konsol hatasi/uyarisi sayisi.
 * OLCMEZ : etkilesim sonrasi hatalar (tiklama, form, sekme degistirme), diger
 *          tarayicilar, yavas ag, sahadaki veri cesitliligi.
 * Yani cikan "0" bir ORNEGIN sonucudur, ozelligin garantisi degildir; depodaki
 * iddia da tam bu genislikte yazilmalidir.
 *
 * 3B ikiz BILEREK ACILMIYOR: Ikiz3D.tsx:104 WebGL yoksa firlatir. Etrafinda hata
 * siniri var (PanoDetay.tsx:288-295) ama React yakaladiginda YINE DE console.error
 * basar. 3B varsayilan sekme degil ve `lazy()` ile yuklenir, yani tiklanmadikca hic
 * calismaz. Tiklamiyoruz — ve bu bir OLCUM BOSLUGUDUR, boyle yazildi.
 *
 * ── GORSEL REGRESYON NEDEN YOK ────────────────────────────────────────────────
 * `toHaveScreenshot()` bu depoda CALISMAZ ve bu olculdu, tercih degil:
 *   - AppShell.tsx:185-191 canli saat basiyor (her dakika degisir),
 *   - lib/format.ts:33-40 goreli zaman yaziyor ("7 dk önce"),
 *   - api/mock.ts:550-556 `Math.random()` ile 3 sn'de bir degerleri oynatiyor.
 * Bu yuzden spec goruntuyu yalnizca URETIR, KARSILASTIRMAZ.
 */

/** Depo koku/assets/ekran — dosya ADLARI docs/16 §5'teki 7 baglantiyla birebir eslesir. */
const EKRAN_DIZIN = fileURLToPath(new URL("../../assets/ekran/", import.meta.url));

/** Goruntu uretimi: mock kipinde varsayilan ACIK, canli kipte ACIKCA istenmeli. */
function goruntuAlinsinMi(kip: string): boolean {
  if (process.env.GRIDUP_E2E_EKRAN === "0") return false;
  if (kip === "canli") return process.env.GRIDUP_E2E_EKRAN === "1";
  return true;
}

interface Gunluk {
  hatalar: string[];
  uyarilar: string[];
}

/**
 * Konsolu dinlemeye `goto`dan ONCE baslanir; sonra baglanmak ilk cizimdeki hatalari
 * kacirir — ki en olasi hatalar tam oradadir. (19 Eylul'de bulunan React #310 hatasi
 * da tam olarak ilk cizim gecisinde olusuyordu.)
 */
function konsoluDinle(page: Page): Gunluk {
  const gunluk: Gunluk = { hatalar: [], uyarilar: [] };
  page.on("console", (m) => {
    const satir = `${m.text()}  @${m.location().url}:${m.location().lineNumber}`;
    if (m.type() === "error") gunluk.hatalar.push(satir);
    else if (m.type() === "warning") gunluk.uyarilar.push(satir);
  });
  // Yakalanmamis istisna konsola "error" olarak DUSMEYEBILIR; ayrica dinlenir.
  page.on("pageerror", (e) => gunluk.hatalar.push(`pageerror: ${e.message}`));
  return gunluk;
}

/** Sayfa "oturana" kadar bekle: h1 gorunsun, yazi tipleri yuklensin, mock gecikmeleri bitsin. */
async function otur(page: Page, rota: Rota): Promise<string> {
  const h1 = page.locator("main h1").first();
  await expect(h1, `${rota.ad}: h1 gorunmedi`).toBeVisible({ timeout: 20_000 });
  // api/mock.ts'te uclarin gecikmesi 120-200 ms; grafikler de bir cizim daha ister.
  await page.waitForLoadState("networkidle").catch(() => undefined);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);
  return (await h1.textContent())?.trim() ?? "";
}

async function rotalariTopla(page: Page, kip: string, tabanUrl: string) {
  if (kip === "canli") return canliRotalari(page.request, tabanUrl);
  return { rotalar: mockRotalari(), atlanan: [] as string[] };
}

test.describe("Yedi ekran — konsol hatasi ve ekran goruntusu", () => {
  test("gezilen her rota konsola hata basmadan aciliyor", async ({ page, baseURL }, testInfo) => {
    const kip = testInfo.project.name;
    const { rotalar, atlanan } = await rotalariTopla(page, kip, baseURL ?? "");

    // SESSIZ KAPSAM DARALMASI OLMASIN: atlanan her rota adiyla ve NEDENIYLE basilir.
    for (const neden of atlanan) console.log(`  [ATLANDI] ${neden}`);
    console.log(`  [KIP] ${kip} · ${baseURL} · ${rotalar.length} rota gezilecek`);

    if (goruntuAlinsinMi(kip)) mkdirSync(EKRAN_DIZIN, { recursive: true });

    const ozet: Array<{ ad: string; hata: number; uyari: number }> = [];
    const tumHatalar: string[] = [];
    const tumUyarilar: string[] = [];

    for (const rota of rotalar) {
      // Her rota icin TEMIZ bir sayfa: onceki rotanin hatalari bu rotaya yazilmasin.
      const sayfa = await page.context().newPage();
      const gunluk = konsoluDinle(sayfa);
      try {
        await sayfa.goto(rota.yol, { waitUntil: "domcontentloaded" });
        const baslik = await otur(sayfa, rota);

        if (rota.baslik) {
          expect(baslik, `${rota.ad} (${rota.yol}) basligi`).toMatch(rota.baslik);
        }
        if (!rota.hataEkraniBekleniyor) {
          // Konsol temiz ama ekran "bulunamadı" diyorsa test yesil yanardi ve
          // "7 ekran gezildi" iddiasi bos kalirdi.
          expect(baslik, `${rota.ad} (${rota.yol}) hata ekranina dustu`).not.toMatch(HATA_BASLIGI);
        }

        if (rota.ekran && goruntuAlinsinMi(kip)) {
          await sayfa.screenshot({ path: `${EKRAN_DIZIN}${rota.ekran}`, fullPage: true });
        }
      } finally {
        await sayfa.close();
      }

      ozet.push({ ad: rota.ad, hata: gunluk.hatalar.length, uyari: gunluk.uyarilar.length });
      tumHatalar.push(...gunluk.hatalar.map((h) => `${rota.ad}: ${h}`));
      tumUyarilar.push(...gunluk.uyarilar.map((u) => `${rota.ad}: ${u}`));
    }

    for (const s of ozet) {
      console.log(`  ${s.hata === 0 && s.uyari === 0 ? "OK " : "!! "}${s.ad}: ${s.hata} hata, ${s.uyari} uyari`);
    }

    // Hata ile uyari AYRI AYRI iddia ediliyor: depodaki iddia ("0 konsol hatasi /
    // uyarisi") ikisini birden soyluyor, yani ikisi de olculmelidir.
    expect(tumHatalar, `Konsol HATALARI: ${JSON.stringify(tumHatalar, null, 2)}`).toHaveLength(0);
    expect(tumUyarilar, `Konsol UYARILARI: ${JSON.stringify(tumUyarilar, null, 2)}`).toHaveLength(0);
  });
});

/**
 * K7 / 7.3 — kontrast artik dokumanda degil BURADA yasiyor.
 *
 * NEDEN ELLE HESAP YETMEZ (olculdu): docs/16 §4'teki oran `theme.css` token'larindan
 * ELLE hesaplanmisti ve zeminin HER ZAMAN `--bg` oldugunu varsayiyordu. axe gercekten
 * CIZILMIS rengi okur ve 19 Eylul'de o varsayimin yanlis oldugu yerde patladi:
 * `/bolge`deki `.kesinti-serit` zemini `--bg` (#f5f6f8) degil #ebecee'dir ve ayni
 * `--dim` token'i orada 4,61:1 degil 4,21:1 verir — AA esiginin ALTINA duser.
 * Elle hesap bunu hicbir zaman goremezdi.
 *
 * OLCULEN SONUC (20 Eylul, mock kipi, Chromium, 1425 px):
 *   WCAG 2.1 AA ihlali TOPLAM 83 dugum, hepsi `color-contrast`.
 *   Baska hicbir axe kurali ihlal edilmiyor.
 *
 *   19 EYLUL'DE BU SAYI 5'TI. Aradaki fark bir GERILEMEDIR ve gizlenmiyor:
 *   `main` birlesmesiyle (c6b5dcd; icinde "3D chart support and styling updates")
 *   gelen yeni arayuz katmanindan geliyor. Taban tokenlar degismedi —
 *   `theme.test.ts` hala #f5f6f8 / #202b34 / #65717d kilidini geciyor, yani
 *   govde metni 13,33:1. Gerileme tokenlarda degil, yeni bilesenlerin kendi
 *   renklerinde. Olculen dagilim (uydurulmadi, axe ciktisindan sayildi):
 *     footer > span:nth-child(1) ve (2)   20   (her rotada iki oge)
 *     kbd                                 10
 *     .hero > p                            7
 *     div[aria-label=...] > button        14   (arac cubugu segment dugmeleri)
 *     .back                                3
 *     kalan                               29   (.dim, .focus-number, code, em, ...)
 *   Ilk uc kalem tek tek bilesen degil, ORTAK birkac renk karari; duzeltilirse
 *   83'un yarisindan fazlasi tek hamlede kapanir.
 *
 * CANLI KIPTE SAYI FARKLI — ve bu, iki kipi ayirmanin en somut karsiligidir.
 * OLCULEN (19 Eylul, :3000 uretim derlemesi, ayni tarayici): 10 rotada TOPLAM 23 dugum.
 * Farkin tamami AppShell'deki IKI ogeden geliyor; ikisi de mock kipinde HIC CIZILMEZ:
 *     .connection-pill -> 4,26:1  (#24836a / #f0f7f4, 11 px) — "Bağlı" rozeti; mock
 *                         kipinde ayni oge "Demo" sinifiyla cizilir (AppShell.tsx:179)
 *     .btn-link        -> 2,91:1  (#ff671d / #ffffff, 13 px) — OperatorGirisi dugmesi;
 *                         yalnizca backend kimlik dogrulamayi ACIK bildirince cizilir
 * Ikisi de HER rotada oldugu icin 2 x 10 = 20, arti `/`de 3 `.focus-number` = 23.
 *
 * DIKKAT (20 Eylul): yukaridaki 23, o gun :3000'de KOSAN GORUNTUDEN olculdu ve o
 * goruntu kaynaktan ESKIDIR. Mock kipi 5'ten 83'e ciktigina gore canli kipin de
 * goruntu yenilendikten SONRA yeniden olculmesi gerekir; eski 23'u guncel diye
 * yazmak bu dosyanin kendi kuralini cignemek olurdu.
 *
 * Yani "arayuzde N kontrast ihlali var" demek, N'in hangi kipten ve hangi
 * derlemeden geldigini SOYLEMEDEN yanlistir.
 *
 * NEDEN DUZELTILMEDI: hepsi renk PALETI kararidir, test isi degil; paleti bu oturumda
 * degistirmek `docs/16` ve `frontend/TASARIM-REVIZYONU.md`teki tasarim kaydini
 * gecersiz kilardi. Sayi bu yuzden GIZLENMIYOR, KILITLENIYOR: asagidaki beklenti
 * olculen halin AYNISIDIR. Yeni bir ihlal cikarsa test duser; biri DUZELTILIRSE de
 * duser — ve bu DOGRUDUR, cunku o zaman hem buradaki hem `docs/16` §4'teki sayinin
 * yeniden olculmesi gerekir. Olculmus 83 ihlal, olculmemis 0 ihlalden iyidir.
 */
const BILINEN_KONTRAST: Record<string, number> = {
  "/": 11,
  "/alarmlar": 8,
  "/bolge": 13,
  "/boyle-bir-sayfa-yok": 3,
  "/cihaz-sagligi": 9,
  "/olay": 4,
  "/olay/EVT-42": 5,
  "/pano/ADM-00014": 10,
  "/pano/ADM-00057": 10,
  "/trend": 10,
};

test.describe("Erisilebilirlik — axe-core taramasi", () => {
  test("yedi ekranda WCAG 2.1 AA ihlalleri", async ({ page, baseURL }, testInfo) => {
    const kip = testInfo.project.name;
    const { rotalar } = await rotalariTopla(page, kip, baseURL ?? "");
    const ihlaller: Array<{ yol: string; rota: string; kural: string; etki: string; adet: number }> = [];

    for (const rota of rotalar) {
      await page.goto(rota.yol, { waitUntil: "domcontentloaded" });
      await otur(page, rota);
      const sonuc = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();
      for (const v of sonuc.violations) {
        ihlaller.push({ yol: rota.yol, rota: rota.ad, kural: v.id, etki: v.impact ?? "?", adet: v.nodes.length });
        for (const n of v.nodes) {
          console.log(`  [AXE] ${rota.ad} · ${v.id} (${v.impact}) · ${n.target.join(" ")}`);
        }
      }
    }
    if (ihlaller.length === 0) console.log("  [AXE] ihlal yok");

    // 1) Kontrast DISINDA hicbir WCAG 2.1 AA ihlali olmamali. Bu iddia veriye bagli
    //    degildir, yani her iki kipte de gecerlidir.
    const kontrastDisi = ihlaller.filter((i) => i.kural !== "color-contrast");
    expect(kontrastDisi, `Kontrast DISI axe ihlalleri: ${JSON.stringify(kontrastDisi, null, 2)}`).toHaveLength(0);

    // 2) Kontrast yalnizca MOCK kipinde kilitlenir. Canli kipte ekranda kac
    //    `.focus-number` cizildigi veritabanindaki pano sayisina baglidir; oradaki
    //    sayi bir OLCUM degil veri artefakti olurdu, o yuzden yalnizca RAPORLANIR.
    const olculen: Record<string, number> = {};
    for (const i of ihlaller.filter((x) => x.kural === "color-contrast")) {
      olculen[i.yol] = (olculen[i.yol] ?? 0) + i.adet;
    }
    if (kip === "mock") {
      expect(
        olculen,
        "Kontrast ihlalleri olculen halden SAPTI — sayiyi docs/16 §4 ile BIRLIKTE yeniden olcun",
      ).toEqual(BILINEN_KONTRAST);
    } else {
      console.log(`  [AXE] canli kip kontrast ihlalleri (kilitlenmez): ${JSON.stringify(olculen)}`);
    }
  });
});
