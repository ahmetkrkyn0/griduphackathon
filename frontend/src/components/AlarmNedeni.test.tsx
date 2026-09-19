import { cleanup, render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { ALARM_REASONSIZ, ALARM_TAM } from "../test/fixtures";
import { AlarmNedeni } from "./AlarmNedeni";

/**
 * K7 / 7.1 — alarm kartinin iki kilidi: (1) dort baslik, (2) eksik `reason` ile cokmeme.
 *
 * ORTAM: bu dosya .tsx oldugu icin jsdom'da kosar (vite.config.ts `environmentMatchGlobs`).
 * Varsayilan "node" ortaminda kosmasi HATA olurdu — global `environment: "jsdom"` ise
 * 38 node testini kirdigi olculdu; gerekce vite.config.ts'te yazili.
 *
 * `globals` kapali (tsconfig/vite): describe/it/expect vitest'ten IMPORT edilir.
 * Ayni sebeple @testing-library'nin OTOMATIK temizligi de devreye GIRMEZ (global bir
 * `afterEach` bulamaz), bu yuzden `cleanup()` asagida ELLE cagriliyor. Cagrilmazsa
 * ikinci render birinciyi belgeden silmez ve `getByRole` "found multiple" ile duser.
 */
afterEach(cleanup);

/**
 * AlarmNedeni `<Link>` cizer (satir 66, 73); router olmadan React Router firlatir.
 * `future` bayraklari App.tsx:15'tekilerle AYNI: verilmezse React Router stderr'e iki
 * uyari basar ve "0 konsol hatasi" olcen bir iste kendi testimiz gurultu uretmis olur.
 */
function ciz(ui: ReactElement) {
  return render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{ui}</MemoryRouter>);
}

describe("AlarmNedeni — dort baslik", () => {
  it("dordunu de, SORU ISARETLERIYLE gosterir", () => {
    ciz(<AlarmNedeni alarm={ALARM_TAM} />);

    // Metinler AlarmNedeni.tsx:80/92/113/118'den BIREBIR alindi. Soru isaretleri
    // kaldirilirsa bu test duser — Yapilacaklar.md:414 onlari isaretsiz yazmisti,
    // esas alinan KODDUR.
    const basliklar = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(basliklar).toEqual(["Neden?", "Ne doğrulanmalı?", "Ne yapmalı?", "Ne kadar acil?"]);
  });

  it("dorduncu baslik `reason.verify` varsa cizilir — fikstur onu tasiyor", () => {
    // Bu test, ustteki testin YANLIS SEYI olcmedigini kanitlar: "Ne doğrulanmalı?"
    // kosullu bir bloktur (AlarmNedeni.tsx:90) ve fiksturun `verify` alanina baglidir.
    expect(ALARM_TAM.reason?.verify).toBeDefined();
    ciz(<AlarmNedeni alarm={ALARM_TAM} />);
    expect(screen.getByText(/3 kanıtından 2 tanesi görüldü/)).toBeTruthy();
  });
});

describe("AlarmNedeni — eksik `reason` alani", () => {
  it("cokmez; UC baslik cizer ve dordunculeri sessizce dusurmez", () => {
    ciz(<AlarmNedeni alarm={ALARM_REASONSIZ} />);

    const basliklar = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    // UC, dort degil. Bu bir KUSUR DEGIL, olculen davranistir: dogrulanacak kanit
    // listesi gelmediyse bos bir "Ne doğrulanmalı?" blogu cizmek yanlis olurdu.
    expect(basliklar).toEqual(["Neden?", "Ne yapmalı?", "Ne kadar acil?"]);
  });

  it("sinyal listesi yerine ACIKLAYICI metin yazar, bos blok birakmaz", () => {
    ciz(<AlarmNedeni alarm={ALARM_REASONSIZ} />);
    expect(screen.getByText("Bu alarm için sinyal ayrıntısı gelmedi.")).toBeTruthy();
    // `advice` da yok: "tanimli degil" yazar, `undefined` basmaz.
    expect(screen.getByText("Bu alarm için öneri tanımlı değil.")).toBeTruthy();
  });
});
