import { useEffect, useState } from "react";
import { api } from "../api/client";
import { errorText } from "../api/errors";
import type { Alarm, AlarmState, Prio } from "../api/types";
import { AlarmNedeni } from "../components/AlarmNedeni";
import { PRIO_NAME } from "../lib/labels";
import { prioRank } from "../lib/worklist";
import { useFleet } from "../state/fleet";

// Kimlik dogrulama henuz yok (yol haritasi: LDAP); onay/raf kontrol odasi adina kaydedilir.
const OPERATOR = "kontrol-odasi";
const REFRESH_MS = 15_000;

type ViewFilter = "acik" | "rafta" | "hepsi";
const VIEW_STATE: Record<ViewFilter, string> = { acik: "active,acked", rafta: "shelved", hepsi: "active,acked,shelved,cleared" };
const VIEW_LABEL: Record<ViewFilter, string> = { acik: "Açık", rafta: "Rafta", hepsi: "Tümü" };
const PRIOS: Prio[] = ["P1", "P2", "P3", "SYS"];

function exportAlarmsCsv(alarmList: Alarm[], nameOf: (id: string) => string) {
  const headers = ["Zaman", "Pano ID", "Pano Adı", "Öncelik", "Kod", "Nokta", "Durum", "Açıklama", "Tavsiye", "Sınır Saati (TTL)"];
  const rows = alarmList.map((a) => [
    `"${a.raised_at}"`,
    `"${a.pano_id}"`,
    `"${(nameOf(a.pano_id) || "").replace(/"/g, '""')}"`,
    `"${a.prio}"`,
    `"${a.code}"`,
    `"${a.reason?.point ?? ""}"`,
    `"${a.state}"`,
    `"${(a.text ?? a.reason?.basis ?? "").replace(/"/g, '""')}"`,
    `"${(a.advice ?? "").replace(/"/g, '""')}"`,
    `"${a.ttl_h != null ? a.ttl_h : ""}"`,
  ]);
  const csvContent = "\uFEFF" + [headers.join(";"), ...rows.map((r) => r.join(";"))].join("\r\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const dateStr = new Date().toISOString().slice(0, 10);
  link.setAttribute("href", url);
  link.setAttribute("download", `gridup-vardiya-raporu-${dateStr}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/** ISA-18.2 alarm konsolu: oncelik/zaman/konum, Neden/Ne yapmali/Ne kadar acil, onay/raf, eskalasyon. */
export function AlarmKonsolu() {
  const { panels } = useFleet();
  const [view, setView] = useState<ViewFilter>("acik");
  const [prioFilter, setPrioFilter] = useState<Set<Prio>>(new Set());
  const [search, setSearch] = useState("");
  const [alarms, setAlarms] = useState<Alarm[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Record<string, string>>({});

  const load = () => {
    api
      .alarms({ state: VIEW_STATE[view], limit: 500 })
      .then((list) => {
        setAlarms(list);
        setError(null);
      })
      .catch((e) => setError(errorText(e)));
  };

  useEffect(() => {
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);

  const togglePrio = (p: Prio) =>
    setPrioFilter((prev) => {
      const next = new Set(prev);
      next.has(p) ? next.delete(p) : next.add(p);
      return next;
    });

  const nameOf = (panoId: string) => panels.find((p) => p.pano_id === panoId)?.name ?? panoId;

  const q = search.trim().toLowerCase();
  const visible = (alarms ?? [])
    .filter((a) => prioFilter.size === 0 || prioFilter.has(a.prio))
    .filter((a) => {
      if (!q) return true;
      const pName = nameOf(a.pano_id).toLowerCase();
      const pId = a.pano_id.toLowerCase();
      const code = a.code.toLowerCase();
      const pt = (a.reason?.point ?? "").toLowerCase();
      const text = (a.text ?? a.reason?.basis ?? "").toLowerCase();
      return pName.includes(q) || pId.includes(q) || code.includes(q) || pt.includes(q) || text.includes(q);
    })
    .sort((a, b) => prioRank(a.prio) - prioRank(b.prio) || Date.parse(b.raised_at) - Date.parse(a.raised_at));

  const onAck = async (alarm: Alarm, note: string) => {
    setBusyId(alarm.id);
    try {
      await api.ack(alarm.id, { by: OPERATOR, channel: "ui", note: note || undefined });
      setMessages((m) => ({ ...m, [alarm.id]: "Onaylandı." }));
      load();
    } catch (e) {
      setMessages((m) => ({ ...m, [alarm.id]: `Onaylanamadı: ${errorText(e)}` }));
    } finally {
      setBusyId(null);
    }
  };

  const onShelve = async (alarm: Alarm, minutes: number, reason: string) => {
    setBusyId(alarm.id);
    try {
      await api.shelve(alarm.id, { by: OPERATOR, minutes, reason });
      setMessages((m) => ({ ...m, [alarm.id]: "Rafa alındı." }));
      load();
    } catch (e) {
      setMessages((m) => ({ ...m, [alarm.id]: `Rafa alınamadı: ${errorText(e)}` }));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <main className="page">
      <div className="hero">
        <h1>Alarm konsolu</h1>
        <p>ISA-18.2 yaşam döngüsü: açık, rafta ve temizlenmiş alarmlar; her kart üç soruyu cevaplar.</p>
      </div>

      <div className="console-toolbar">
        <div className="search-wrap">
          <span className="search-icon" aria-hidden="true">🔍</span>
          <input
            type="search"
            className="search-input"
            placeholder="Alarm, pano veya nokta ara…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Alarmlarda ara"
          />
          {search && (
            <button type="button" className="search-clear" onClick={() => setSearch("")} aria-label="Aramayı temizle">
              ✕
            </button>
          )}
        </div>

        <div className="console-filters" role="group" aria-label="Durum">
          {(Object.keys(VIEW_STATE) as ViewFilter[]).map((v) => (
            <button key={v} type="button" aria-pressed={view === v} onClick={() => setView(v)}>
              {VIEW_LABEL[v]}
            </button>
          ))}
          <span className="dim small">·</span>
          {PRIOS.map((p) => (
            <button key={p} type="button" aria-pressed={prioFilter.has(p)} onClick={() => togglePrio(p)}>
              {PRIO_NAME[p]}
            </button>
          ))}
        </div>

        {visible.length > 0 && (
          <button
            type="button"
            className="btn-export"
            onClick={() => exportAlarmsCsv(visible, nameOf)}
            title="Mevcut alarmları Excel uyumlu CSV formatında indir"
          >
            📥 CSV İndir (Vardiya Raporu)
          </button>
        )}
      </div>

      {error && <p className="dim">{error}</p>}
      {!alarms && !error && <p className="dim">Yükleniyor…</p>}
      {alarms && visible.length === 0 && (
        <p className="console-empty">{search ? `"${search}" ile eşleşen alarm yok.` : "Bu filtrede alarm yok."}</p>
      )}

      <ul className="console-list">
        {visible.map((a) => (
          <li key={a.id} className="console-card">
            <AlarmCard alarm={a} panoName={nameOf(a.pano_id)} onAck={onAck} onShelve={onShelve} busy={busyId === a.id} message={messages[a.id] ?? null} state={a.state} />
          </li>
        ))}
      </ul>
    </main>
  );
}

function AlarmCard({
  alarm,
  panoName,
  onAck,
  onShelve,
  busy,
  message,
  state,
}: {
  alarm: Alarm;
  panoName: string;
  onAck: (alarm: Alarm, note: string) => void;
  onShelve: (alarm: Alarm, minutes: number, reason: string) => void;
  busy: boolean;
  message: string | null;
  state: AlarmState;
}) {
  return (
    <AlarmNedeni
      alarm={alarm}
      panoName={panoName}
      onAck={state === "active" ? onAck : undefined}
      onShelve={state === "active" || state === "acked" ? onShelve : undefined}
      ackBusy={busy}
      shelveBusy={busy}
      message={message}
    />
  );
}
