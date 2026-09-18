import { useEffect, useState } from "react";
import { api } from "../api/client";
import { clearToken, getToken, onTokenChange, setToken } from "../api/session";
import type { AuthStatus } from "../api/types";

/**
 * Ust cubuktaki operator girisi (F-19).
 *
 * NEDEN TAM EKRAN BIR GIRIS KAPISI DEGIL: kimlik dogrulama yalnizca YAZMA uclarini
 * (onay / raf) koruyor; filo listesi, pano detayi, trend, kara kutu ve cihaz sagligi
 * belirtec istemiyor (bilincli sinir, docs/15 §5). Tum uygulamayi kilitlemek, sunucunun
 * gercekte uyguladigi kuraldan DAHA KATI bir kapi cizmek olurdu ve arayuz sunucunun
 * soylemedigi bir sey soylemis olurdu.
 *
 * NE YAPMIYOR: rol bazli gizleme. Izleyici rolundeki bir kullaniciya onay dugmesi yine
 * gorunur, basinca 403 alir. Yetki karari SUNUCUDADIR (dogru yer orasidir); eksik olan
 * arayuz cilasidir ve contracts/changes/2026-09-18-kimlik-dogrulama.md'de yazilidir.
 */
export function OperatorGirisi() {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [token, setLocalToken] = useState<string | null>(getToken());
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");

  useEffect(() => onTokenChange(() => setLocalToken(getToken())), []);

  useEffect(() => {
    const controller = new AbortController();
    api
      .authStatus(controller.signal)
      .then(setStatus)
      .catch(() => setStatus(null)); // backend kapali: sessiz kal, sahte bir durum uydurma
    return () => controller.abort();
  }, []);

  // Durum okunamadiysa hicbir sey cizme: "kapali" demek de "acik" demek de yanlis olurdu.
  if (status === null) return null;

  if (!status.enabled) {
    return (
      <span className="dim small" title="GRIDUP_OPERATORS tanimsiz; onay/raf belirtecsiz kabul edilir ve denetim izine 'anonim' yazilir">
        kimlik doğrulama kapalı
      </span>
    );
  }

  if (token) {
    return (
      <span className="small">
        operatör girişi yapıldı{" "}
        <button type="button" className="btn-link" onClick={() => clearToken()}>
          çıkış
        </button>
      </span>
    );
  }

  if (!open) {
    return (
      <button type="button" className="btn-link small" onClick={() => setOpen(true)}>
        operatör girişi
      </button>
    );
  }

  return (
    <form
      className="small"
      onSubmit={(event) => {
        event.preventDefault();
        const value = draft.trim();
        if (!value) return;
        setToken(value);
        setDraft("");
        setOpen(false);
      }}
    >
      <label htmlFor="operator-token" className="dim">
        Operatör belirteci{" "}
      </label>
      <input
        id="operator-token"
        type="password"
        autoComplete="off"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        aria-describedby="operator-token-not"
      />
      <button type="submit">Gir</button>
      <button type="button" className="btn-link" onClick={() => setOpen(false)}>
        vazgeç
      </button>
      <span id="operator-token-not" className="dim" style={{ display: "block" }}>
        Belirteç bu sekmede tutulur, sekme kapanınca silinir.
      </span>
    </form>
  );
}
