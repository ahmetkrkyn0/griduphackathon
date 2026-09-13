import type { Alarm, AlarmSignal } from "../api/types";
import { ago, measure, ttlText } from "../lib/format";
import { CHANNEL_TEXT, adviceText, alarmText, signalLabel, unitText } from "../lib/labels";
import { PrioMark } from "./PrioMark";

interface Props {
  alarm: Alarm;
  onAck?: (alarm: Alarm) => void;
  ackBusy?: boolean;
  ackMessage?: string | null;
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

/** Her alarm uc soruyu cevaplar: Neden? Ne yapmali? Ne kadar acil? (rapor 6.5 L4) */
export function AlarmNedeni({ alarm, onAck, ackBusy = false, ackMessage = null }: Props) {
  const signals = alarm.reason?.signals ?? [];
  const ttl = ttlText(alarm.ttl_h);
  const advice = adviceText(alarm.advice);
  const notified = (alarm.notified ?? []).map((channel) => CHANNEL_TEXT[channel] ?? channel);

  return (
    <div className="qa">
      <div className="qa-head">
        <PrioMark prio={alarm.prio} acked={alarm.state === "acked"} />
        <strong>{alarmText(alarm.code, alarm.text)}</strong>
        <span className="dim">{ago(alarm.raised_at)}</span>
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
          <button type="button" className="btn" disabled={ackBusy} onClick={() => onAck(alarm)}>
            {ackBusy ? "Onaylanıyor…" : "Onayla"}
          </button>
        )}
        {alarm.state === "acked" && (
          <span className="dim">
            {alarm.acked_by ?? "Bilinmeyen kullanıcı"} onayladı{alarm.acked_at ? `, ${ago(alarm.acked_at)}` : ""}
          </span>
        )}
        {ackMessage && (
          <span className="dim" role="status">
            {ackMessage}
          </span>
        )}
      </div>
    </div>
  );
}
