import { useState } from "react";
import { Link } from "react-router-dom";
import type { Alarm, AlarmSignal } from "../api/types";
import { ago, measure, ttlText } from "../lib/format";
import { CHANNEL_TEXT, adviceText, alarmText, hypText, signalLabel, unitText } from "../lib/labels";
import { PrioMark } from "./PrioMark";

interface Props {
  alarm: Alarm;
  /** Panonun adı/kimliği: yalnızca alarm konsolu gibi çoklu-pano listelerinde gösterilir. */
  panoName?: string;
  onAck?: (alarm: Alarm, note: string) => void;
  onShelve?: (alarm: Alarm, minutes: number, reason: string) => void;
  ackBusy?: boolean;
  shelveBusy?: boolean;
  message?: string | null;
}

function SignalRow({ signal }: { signal: AlarmSignal }) {
  // "_ok" ile biten etiketler bayraktir (1 = saglam): esikle kiyaslanmaz, durum olarak yazilir.
  if (signal.tag.endsWith("_ok")) {
    return (
      <div className="sig">
        <span>{signalLabel(signal.tag)}</span>
        <b>{signal.value ? "Sağlam" : "Arızalı"}</b>
      </div>
    );
  }
  return (
    <div className="sig">
      <span>{signalLabel(signal.tag)}</span>
      <span>
        <b>
          {measure(signal.value)} {unitText(signal.unit)}
        </b>
        {signal.threshold != null && <span className="dim"> eşik {measure(signal.threshold)}</span>}
      </span>
    </div>
  );
}

/** Her alarm uc soruyu cevaplar: Neden? Ne yapmali? Ne kadar acil? (rapor 6.5 L4)
 *  Buna karsi-olgusal dorduncu blok eklenir: Ne dogrulanmali? (hipotezin eksik kaniti). */
export function AlarmNedeni({ alarm, panoName, onAck, onShelve, ackBusy = false, shelveBusy = false, message = null }: Props) {
  const [note, setNote] = useState("");
  const [shelving, setShelving] = useState(false);
  const [minutes, setMinutes] = useState(60);
  const [reason, setReason] = useState("");

  const signals = alarm.reason?.signals ?? [];
  const verify = alarm.reason?.verify;
  const confirmed = verify ? verify.total - verify.missing.length : 0;
  const ttl = ttlText(alarm.ttl_h);
  const advice = adviceText(alarm.advice);
  const notified = (alarm.notified ?? []).map((channel) => CHANNEL_TEXT[channel] ?? channel);
  const canShelve = onShelve && alarm.prio !== "P1" && (alarm.state === "active" || alarm.state === "acked");
  // Y2 (olay modu, TASARIM-REVIZYONU.md §4): P1 + onaysizken bu kart gorsel olarak one cikar.
  const eventMode = alarm.prio === "P1" && alarm.state === "active";

  return (
    <div className={eventMode ? "qa qa-event" : "qa"}>
      <div className="qa-head">
        <PrioMark prio={alarm.prio} acked={alarm.state === "acked"} />
        <strong>{alarmText(alarm.code, alarm.text)}</strong>
        {panoName && (
          <Link className="pano" to={`/pano/${alarm.pano_id}`}>
            {panoName} <span className="dim">{alarm.pano_id}</span>
          </Link>
        )}
        <span className={eventMode ? "event-elapsed" : "dim"}>{ago(alarm.raised_at)}</span>
        {alarm.state === "shelved" && <span className="badge-shelved">rafta{alarm.shelved_until ? `, ${ago(alarm.shelved_until)} bitiyor` : ""}</span>}
        {alarm.prio === "P1" && alarm.event_id && (
          <Link className="event-link" to={`/olay/${alarm.event_id}`}>
            Kara kutuyu aç →
          </Link>
        )}
      </div>

      <section>
        <h3>Neden?</h3>
        <div>
          {signals.length === 0 && <p className="dim">Bu alarm için sinyal ayrıntısı gelmedi.</p>}
          {signals.map((signal) => (
            <SignalRow key={signal.tag} signal={signal} />
          ))}
          {alarm.reason?.basis && <p className="basis">Dayanak: {alarm.reason.basis}</p>}
        </div>
      </section>

      {verify && (
        <section>
          <h3>Ne doğrulanmalı?</h3>
          <div>
            <p className="dim small">
              {hypText(verify.hypothesis)} hipotezinin {verify.total} kanıtından {confirmed} tanesi görüldü.
              {verify.missing.length > 0 && " Aşağıdakiler de doğrulanırsa teşhis kesinleşir."}
            </p>
            {verify.missing.length === 0 ? (
              <p>Bu hipotezin tüm kanıtları toplandı; doğrulanacak başka kanıt yok.</p>
            ) : (
              verify.missing.map((code) => (
                <div className="sig" key={code}>
                  <span>{alarmText(code)}</span>
                  <span className="dim small">{code}</span>
                </div>
              ))
            )}
          </div>
        </section>
      )}

      <section>
        <h3>Ne yapmalı?</h3>
        <p>{advice ?? "Bu alarm için öneri tanımlı değil."}</p>
      </section>

      <section>
        <h3>Ne kadar acil?</h3>
        <div>
          {ttl ? (
            <div className="sig">
              <span>Sıcaklık sınırına tahmini</span>
              <b>{ttl}</b>
            </div>
          ) : (
            <p>{alarm.prio === "P1" ? "Hemen müdahale gerekir." : "Süre tahmini yok."}</p>
          )}
          {notified.length > 0 && (
            <p className="dim">
              Bildirildi: {notified.join(", ")}
              {alarm.escalation_level ? `, eskalasyon seviyesi ${alarm.escalation_level}` : ""}
            </p>
          )}
        </div>
      </section>

      <div className="actions">
        {alarm.state === "active" && onAck && (
          <>
            <input
              type="text"
              placeholder="Yorum (opsiyonel)"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              aria-label="Onay yorumu"
              style={{ minWidth: 180 }}
            />
            <button type="button" className="btn" disabled={ackBusy} onClick={() => onAck(alarm, note)}>
              {ackBusy ? "Onaylanıyor…" : "Onayla"}
            </button>
          </>
        )}
        {canShelve && !shelving && (
          <button type="button" className="btn ghost" onClick={() => setShelving(true)}>
            Rafa al
          </button>
        )}
        {alarm.state === "acked" && (
          <span className="dim">
            {alarm.acked_by ?? "Bilinmeyen kullanıcı"} onayladı{alarm.acked_at ? `, ${ago(alarm.acked_at)}` : ""}
          </span>
        )}
        {message && (
          <span className="dim" role="status">
            {message}
          </span>
        )}
      </div>

      {shelving && onShelve && (
        <div className="shelf-form">
          <label className="dim small" htmlFor={`min-${alarm.id}`}>
            Süre (dk)
          </label>
          <input id={`min-${alarm.id}`} type="number" min={1} max={480} value={minutes} onChange={(e) => setMinutes(Number(e.target.value))} style={{ width: 70 }} />
          <input type="text" placeholder="Gerekçe (≥3 karakter)" value={reason} onChange={(e) => setReason(e.target.value)} />
          <button
            type="button"
            className="btn"
            disabled={shelveBusy || reason.trim().length < 3}
            onClick={() => onShelve(alarm, minutes, reason.trim())}
          >
            {shelveBusy ? "Rafa alınıyor…" : "Onayla"}
          </button>
          <button type="button" className="btn ghost" onClick={() => setShelving(false)}>
            Vazgeç
          </button>
        </div>
      )}
    </div>
  );
}
