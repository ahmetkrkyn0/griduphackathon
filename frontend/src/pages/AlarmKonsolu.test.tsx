import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/errors";
import { ALARM_TAM, fleetState } from "../test/fixtures";
import { AlarmKonsolu } from "./AlarmKonsolu";

/**
 * K7 / 7.1 — "Onayla" belirtec YOKKEN ne yapiyor?
 *
 * NEDEN BU DOSYA: 401'i kullaniciya cevirme davranisi AlarmNedeni'nde DEGIL, burada
 * yasiyor (AlarmKonsolu.tsx:119-123 `catch` blogu). AlarmNedeni yalnizca `onAck`
 * cagirir; hatayi metne ceviren `errorText` + `setMessages` ikilisi bu sayfada.
 *
 * OLCULEN RISK: `api.ack` reddedince ekranda HICBIR SEY degismezse operator alarmi
 * onayladigini SANIR. Kilitlenen sey budur — 401'in kendisi degil, GORUNURLUGU.
 *
 * Taklit edilen sey `fetch` degil, `fetch`in ZATEN cevrilmis sonucudur: client.ts:26
 * her 4xx'i ApiError'a cevirir, biz de ApiError(401) firlatiriz. Boylece `errorText`
 * (api/errors.ts) gercek kod yolundan gecer, taklit edilmez.
 */
const taklit = vi.hoisted(() => ({ ack: vi.fn(), alarms: vi.fn(), shelve: vi.fn() }));

vi.mock("../api/client", () => ({ api: taklit, usingMocks: true }));

/**
 * `../state/fleet` de taklit edilir: AlarmKonsolu pano ADLARINI context'ten alir
 * (satir 59) ve gercek FleetProvider WebSocket acardi (stream.ts) — jsdom'da bu,
 * olcmek istedigimiz seyle ilgisi olmayan bir konsol gurultusu demekti.
 */
vi.mock("../state/fleet", () => ({ useFleet: () => fleetState({ panels: [] }) }));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function ciz() {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AlarmKonsolu />
    </MemoryRouter>,
  );
}

describe("AlarmKonsolu — belirtecsiz onay", () => {
  it("401'i operatorun okuyabilecegi tek satira cevirir, sessiz kalmaz", async () => {
    taklit.alarms.mockResolvedValue([ALARM_TAM]);
    taklit.ack.mockRejectedValue(new ApiError(401, "Operatör belirteci gerekli"));
    const user = userEvent.setup();
    ciz();

    // Ilk kart kendiliginden acilir (AlarmKonsolu.tsx:248 `expandedId === null && i === 0`).
    const onayla = await screen.findByRole("button", { name: "Onayla" });

    // TUZAK: "Onayla" metni IKI yerde var — onay (AlarmNedeni.tsx:149) ve rafa alma
    // formunun onayi (:183). Rafa alma formu acilmadigi surece TEK olmali. Bu assert,
    // testin yarin yanlis dugmeye basmasini engeller. Ayrica TAM STRING kullaniyoruz:
    // /Onayla/ regexi "Onaylanıyor…", "Onaylandı." ve PrioMark'in aria-label'ina da carpar.
    expect(screen.getAllByRole("button", { name: "Onayla" })).toHaveLength(1);

    await user.click(onayla);

    // Metin errorText() kalibindan gelir (api/errors.ts:13): "API <durum>: <detay>".
    expect(await screen.findByText("Onaylanamadı: API 401: Operatör belirteci gerekli")).toBeTruthy();
    expect(taklit.ack).toHaveBeenCalledTimes(1);
    // Istemci onaylayanin ADINI GONDERMEZ (F-19); sunucu onu belirtecten turetir.
    expect(taklit.ack).toHaveBeenCalledWith(ALARM_TAM.id, { channel: "ui", note: undefined });
  });

  it("basarisiz onaydan sonra dugme yeniden denenebilir kalir", async () => {
    // AlarmKonsolu.tsx:124-126'daki `finally { setBusyId(null) }` olmasaydi kart kalici
    // olarak "Onaylanıyor…" halinde kilitlenirdi — 401'den daha sinsi bir kusur.
    taklit.alarms.mockResolvedValue([ALARM_TAM]);
    taklit.ack.mockRejectedValue(new ApiError(401, "Operatör belirteci gerekli"));
    const user = userEvent.setup();
    ciz();

    await user.click(await screen.findByRole("button", { name: "Onayla" }));
    await screen.findByText(/Onaylanamadı/);

    expect(screen.getByRole("button", { name: "Onayla" }).hasAttribute("disabled")).toBe(false);
  });

  it("onay BASARILI olunca hata degil onay metni cikar", async () => {
    // Karsi ornek: ustteki testler, bilesen HER durumda "Onaylanamadı" yazsa bile gecerdi.
    taklit.alarms.mockResolvedValue([ALARM_TAM]);
    taklit.ack.mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    ciz();

    await user.click(await screen.findByRole("button", { name: "Onayla" }));
    expect(await screen.findByText("Onaylandı.")).toBeTruthy();
  });
});
