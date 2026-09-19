import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Blackbox } from "../api/types";
import { GECMIS_AN, PANO, fleetState } from "../test/fixtures";
import { OlayAnalizi } from "./OlayAnalizi";

/**
 * REGRESYON KILIDI — K7 / 7.2'de yazilan e2e tezgahinin ILK KOSUSUNDA buldugu kusur.
 *
 * OLCULEN KUSUR (19 Eylul, duzeltmeden once): `generateIncidentNarrative`i saran
 * `useMemo`, `if (error)` / `if (!data)` erken donuslerinin ALTINDAYDI. Ilk cizimde
 * `data` null oldugu icin cagrilmiyor, veri gelince cagriliyordu; hook sayisi 9 -> 10
 * degisince React #310 firlatiyordu ("Rendered more hooks than during the previous
 * render") ve kara kutu ekrani TAMAMEN BOS kaliyordu — hem `npm run dev:mock`te hem
 * :3000 uretim derlemesinde.
 *
 * NEDEN BURADA DA TEST VAR (e2e zaten yakaliyorken): e2e tarayici + ayakta bir sunucu
 * ister ve elle kosulur. Bu test `npm test` ile HER SEFERINDE kosar. Kusur ancak
 * null -> veri GECISINDE ortaya cikiyor, o yuzden `blackbox` bilerek ASENKRON cozulur;
 * senkron bir taklit bu kusuru YAKALAMAZDI.
 */
const taklit = vi.hoisted(() => ({ blackbox: vi.fn(), panel: vi.fn(), alarms: vi.fn() }));

vi.mock("../api/client", () => ({ api: taklit, usingMocks: true }));
vi.mock("../state/fleet", () => ({ useFleet: () => fleetState({ panels: [PANO] }) }));

const KARA_KUTU: Blackbox = {
  event_id: "EVT-1",
  pano_id: PANO.pano_id,
  occurred_at: GECMIS_AN,
  code: "ALM-K-ALM",
  det_label: null,
  window_h: 72,
  series: { "t_conn.GIRIS_L1.t_c": [[Date.parse(GECMIS_AN), 61.4]] },
  timeline: [{ ts: GECMIS_AN, kind: "alarm", text: "ALM-K-ALM (P2, Giriş L1) oluştu" }],
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("OlayAnalizi — kara kutu", () => {
  it("null -> veri gecisinde cokmez (hook sirasi sabit kalir)", async () => {
    // Mikro gorev sinirini asan bir Promise: bilesen ONCE `data === null` ile,
    // SONRA veriyle cizilir. Kusurun ortaya ciktigi tek yol budur.
    taklit.blackbox.mockImplementation(
      () => new Promise((cozumle) => setTimeout(() => cozumle(KARA_KUTU), 0)),
    );
    taklit.panel.mockRejectedValue(new Error("on gorunus bu testte gerekli degil"));

    render(
      <MemoryRouter initialEntries={["/olay/EVT-1"]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/olay/:eventId" element={<OlayAnalizi />} />
        </Routes>
      </MemoryRouter>,
    );

    // Once yukleniyor hali (h1 YOK) — gecisin gerceklestiginin kaniti.
    expect(screen.getByText("Yükleniyor…")).toBeTruthy();

    // Sonra rapor. Cokseydi h1 hic gelmez, test burada zaman asimina ugrardi.
    const h1 = await screen.findByRole("heading", { level: 1 });
    expect(h1.textContent).toBe("Isıl direnç indeksi yüksek, gevşek veya oksitlenmiş bağlantı");
    // Anlati `useMemo`dan gelir — kusurun tam olarak bulundugu hook.
    expect(screen.getAllByText(/panosunda .* olayı kaydedilmiştir/).length).toBeGreaterThan(0);
  });

  it("olay bulunamazsa hata ekranina duser, bos sayfa birakmaz", async () => {
    taklit.blackbox.mockRejectedValue(new Error("API 404: olay yok"));
    render(
      <MemoryRouter initialEntries={["/olay/YOK"]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/olay/:eventId" element={<OlayAnalizi />} />
        </Routes>
      </MemoryRouter>,
    );
    const h1 = await screen.findByRole("heading", { level: 1 });
    expect(h1.textContent).toBe("Olay bulunamadı");
  });
});
