import { useEffect, useState } from "react";
import { api } from "../api/client";
import { errorText } from "../api/errors";
import type { Alarm, AlarmState, Prio } from "../api/types";
import { AlarmNedeni } from "../components/AlarmNedeni";
import { Icon } from "../components/Icon";
import { ago } from "../lib/format";
import { PRIO_NAME, alarmText } from "../lib/labels";
import { prioRank } from "../lib/worklist";
import { useFleet } from "../state/fleet";

// F-19: onaylayanin adi artik ISTEMCIDEN gonderilmiyor. Sunucu onu dogrulanmis
// Authorization basligindan turetir (openapi v1.2.0); belirtec yoksa 401 doner ve
// giris kapisi cizilir (components/GirisKapisi.tsx).
const REFRESH_MS = 15_000;

type ViewFilter = "acik" | "rafta" | "hepsi";
const VIEW_STATE: Record<ViewFilter, string> = {
  acik: "active,acked",
  rafta: "shelved",
  hepsi: "active,acked,shelved,cleared",
};
const VIEW_LABEL: Record<ViewFilter, string> = {
  acik: "Açık",
  rafta: "Rafta",
  hepsi: "Tümü",
};
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
  const [alarms, setAlarms] = useState<Alarm[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Record<string, string>>({});
  const [query, setQuery] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

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

  const nameOf = (panoId: string) =>
    panels.find((p) => p.pano_id === panoId)?.name ?? panoId;

  const q = query.trim().toLocaleLowerCase("tr");
  const visible = (alarms ?? [])
    .filter((a) => prioFilter.size === 0 || prioFilter.has(a.prio))
    .filter((a) => {
      if (!q) return true;
      const pName = nameOf(a.pano_id).toLocaleLowerCase("tr");
      const pId = a.pano_id.toLocaleLowerCase("tr");
      const code = a.code.toLocaleLowerCase("tr");
      const text = alarmText(a.code, a.text).toLocaleLowerCase("tr");
      const pt = (a.reason?.point ?? "").toLocaleLowerCase("tr");
      return pName.includes(q) || pId.includes(q) || code.includes(q) || text.includes(q) || pt.includes(q);
    })
    .sort(
      (a, b) =>
        prioRank(a.prio) - prioRank(b.prio) ||
        Date.parse(b.raised_at) - Date.parse(a.raised_at),
    );
  const onAck = async (alarm: Alarm, note: string) => {
    setBusyId(alarm.id);
    try {
      await api.ack(alarm.id, { channel: "ui", note: note || undefined });
      setMessages((m) => ({ ...m, [alarm.id]: "Onaylandı." }));
      load();
    } catch (e) {
      setMessages((m) => ({
        ...m,
        [alarm.id]: `Onaylanamadı: ${errorText(e)}`,
      }));
    } finally {
      setBusyId(null);
    }
  };

  const onShelve = async (alarm: Alarm, minutes: number, reason: string) => {
    setBusyId(alarm.id);
    try {
      await api.shelve(alarm.id, { minutes, reason });
      setMessages((m) => ({ ...m, [alarm.id]: "Rafa alındı." }));
      load();
    } catch (e) {
      setMessages((m) => ({
        ...m,
        [alarm.id]: `Rafa alınamadı: ${errorText(e)}`,
      }));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <main className="page">
      <div className="hero">
        <span className="eyebrow">MÜDAHALE VE TAKİP</span>
        <h1>Alarm merkezi</h1>
        <p>
          Önceliğe göre sıralanan alarmları inceleyin. Neden, önerilen işlem ve
          süre için bir kayıt açın.
        </p>
      </div>

      <div className="console-filters" role="group" aria-label="Durum">
        {(Object.keys(VIEW_STATE) as ViewFilter[]).map((v) => (
          <button
            key={v}
            type="button"
            aria-pressed={view === v}
            onClick={() => setView(v)}
          >
            {VIEW_LABEL[v]}
          </button>
        ))}
        <span className="dim small">·</span>
        {PRIOS.map((p) => (
          <button
            key={p}
            type="button"
            aria-pressed={prioFilter.has(p)}
            onClick={() => togglePrio(p)}
          >
            {PRIO_NAME[p]}
          </button>
        ))}
        <label className="field-search alarm-search">
          <Icon name="search" size={16} />
          <input
            aria-label="Alarmlarda ara"
            placeholder="Pano veya alarm ara"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        {visible.length > 0 && (
          <button
            type="button"
            className="btn-export"
            onClick={() => exportAlarmsCsv(visible, nameOf)}
            title="Mevcut alarmları Excel uyumlu CSV formatında indir"
            style={{ marginLeft: "auto" }}
          >
            <Icon name="download" size={14} /> CSV İndir (Vardiya Raporu)
          </button>
        )}
      </div>

      {error && <p className="dim">{error}</p>}
      {!alarms && !error && <p className="dim">Yükleniyor…</p>}
      {alarms && visible.length === 0 && (
        <p className="console-empty">{query ? `"${query}" ile eşleşen alarm yok.` : "Bu filtrede alarm yok."}</p>
      )}

      <div className="results-heading">
        <span>{visible.length} alarm gösteriliyor</span>
        <span>Öncelik → Son olay</span>
      </div>
      <ul className="console-list alarm-register">
        {visible.map((a, i) => (
          <li key={a.id} className="console-card">
            <button
              className="alarm-summary"
              aria-expanded={
                expandedId === a.id || (expandedId === null && i === 0)
              }
              onClick={() =>
                setExpandedId(
                  expandedId === a.id || (expandedId === null && i === 0)
                    ? ""
                    : a.id,
                )
              }
            >
              <span className={`status-badge tone-${a.prio}`}>
                {PRIO_NAME[a.prio]}
              </span>
              <span className="alarm-summary-main">
                <strong>{alarmText(a.code, a.text)}</strong>
                <small>
                  {nameOf(a.pano_id)} · {a.pano_id}
                </small>
              </span>
              <span className="alarm-state">
                {
                  {
                    active: "Onay bekliyor",
                    acked: "Onaylandı",
                    shelved: "Rafta",
                    cleared: "Temizlendi",
                  }[a.state]
                }
              </span>
              <time>{ago(a.raised_at)}</time>
              <Icon name="chevron" size={16} />
            </button>
            {(expandedId === a.id || (expandedId === null && i === 0)) && (
              <div className="alarm-expanded">
                <AlarmCard
                  alarm={a}
                  panoName={nameOf(a.pano_id)}
                  onAck={onAck}
                  onShelve={onShelve}
                  busy={busyId === a.id}
                  message={messages[a.id] ?? null}
                  state={a.state}
                />
              </div>
            )}
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
