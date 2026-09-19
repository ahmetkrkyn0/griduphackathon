import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { FleetState } from "../state/fleet";
import { KPI, PANO, fleetState } from "../test/fixtures";
import { FiloListesi } from "./FiloListesi";

/**
 * K7 / 7.1 — filo listesi BOS yanitta cokuyor mu?
 *
 * TUZAK (olculdu): FiloListesi API'den veri ALMIYOR. `../api/client`'i import bile
 * etmiyor; verisi `useFleet()` context'inden geliyor (FiloListesi.tsx:45). Yani
 * `vi.mock("../api/client")` bu testte HICBIR SEY yapmazdi — taklit edilmesi gereken
 * modul `../state/fleet`.
 *
 * Bos liste tek basina bir sey kanitlamaz: asil risk BOS ile HATA'nin ve BOS ile
 * YUKLENIYOR'un ayni ekrana dusmesidir. Operator "pano yok" ile "veri gelmedi"yi
 * ayirt edemezse sessiz bir kesintiyi normal sanir. Uc dal da ayri ayri olculuyor.
 */
const durum = vi.hoisted(() => ({ value: {} as FleetState }));

vi.mock("../state/fleet", () => ({ useFleet: () => durum.value }));

afterEach(cleanup);

function ciz(over: Partial<FleetState>) {
  durum.value = fleetState(over);
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <FiloListesi />
    </MemoryRouter>,
  );
}

describe("FiloListesi — bos yanit", () => {
  it("bos pano listesinde cokmez, kendi bos durumunu cizer", () => {
    ciz({ panels: [], loaded: true, error: null });
    // Metin FiloListesi.tsx:101'den birebir.
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Henüz pano yok");
    expect(screen.getByText("İlk pano veri gönderdiğinde burada görünecek.")).toBeTruthy();
    // Tablo HIC cizilmemeli: bos bir tablo "envanter bos mu, filtre mi tutmadi"
    // sorusunu cevapsiz birakirdi.
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("bos yanit ile HATA ayni ekrana dusmez", () => {
    ciz({ panels: [], loaded: true, error: "API'ye ulaşılamadı" });
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Filo verisi alınamadı");
    expect(screen.getByText("API'ye ulaşılamadı")).toBeTruthy();
  });

  it("bos yanit ile HENUZ YUKLENMEDI de ayni ekrana dusmez", () => {
    // `loaded` false iken panels de bostur; ayrim YALNIZCA `loaded` bayragindan gelir
    // (FiloListesi.tsx:77). Bayrak dusurulurse bos filo "yukleniyor" gibi donup kalir.
    ciz({ panels: [], loaded: false });
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Operasyon verileri yükleniyor");
  });

  it("dolu yanitta envanter tablosu cizilir — bos durum testi bos yere gecmiyor", () => {
    // Bu test olmadan ustteki uc test, bilesen HER ZAMAN "Henüz pano yok" cizse bile
    // gecerdi. Dolu yol da cizildigi icin bos dal gercekten bir SECIMDIR.
    // (Bu dal RiskMatrisi -> useChartWidth -> ResizeObserver'i calistirir; jsdom'da o
    // API yok, src/test/setup.ts'teki koltuk degnegi bu yuzden var.)
    ciz({ panels: [PANO], loaded: true, kpi: KPI });
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Operasyon özeti");
    expect(screen.getByRole("table")).toBeTruthy();
    expect(screen.getAllByText(PANO.name).length).toBeGreaterThan(0);
  });
});
