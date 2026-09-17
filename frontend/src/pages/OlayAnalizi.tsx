import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { errorText } from "../api/errors";
import type { Alarm, Blackbox } from "../api/types";
import { CizgiGrafik, type ChartMarker } from "../components/CizgiGrafik";
import { ago } from "../lib/format";
import { Icon } from "../components/Icon";
import { PRIO_NAME, alarmText } from "../lib/labels";
import { useFleet } from "../state/fleet";

const WINDOWS = [24, 72, 168] as const; // saat; backend sinir: 1-168 (insights.py)

const KIND_TR: Record<string, string> = {
  alarm: "Alarm",
  ack: "Onay",
  action: "Aksiyon",
  note: "Not",
  trip: "Trip",
};

/** TC3: kara kutu — bir olayin oncesindeki 72 saatlik sinyalleri ve zaman cizelgesini gosterir. */
export function OlayAnalizi() {
  const { eventId } = useParams();
  if (!eventId) return <OlaySecici />;
  return <KaraKutu eventId={eventId} />;
}

/** Olay kimligi elde degilken: alarmlarin event_id'lerinden bir secim listesi kurar. */
function OlaySecici() {
  const { panels } = useFleet();
  const [alarms, setAlarms] = useState<Alarm[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .alarms({ state: "active,acked,shelved,cleared", limit: 500 })
      .then(setAlarms)
      .catch((e) => setError(errorText(e)));
  }, []);

  const events = useMemo(() => {
    if (!alarms) return [];
    const seen = new Map<string, Alarm>();
    for (const a of alarms)
      if (a.event_id && !seen.has(a.event_id)) seen.set(a.event_id, a);
    return [...seen.values()].sort(
      (a, b) => Date.parse(b.raised_at) - Date.parse(a.raised_at),
    );
  }, [alarms]);

  const nameOf = (panoId: string) =>
    panels.find((p) => p.pano_id === panoId)?.name ?? panoId;

  return (
    <main className="page">
      <div className="hero">
        <h1>Olay analizi — kara kutu</h1>
        <p>
          Bir olayı seçin; olay öncesi sinyaller ve olayla ilgili tüm adımlar
          tek zaman çizelgesinde görünür.
        </p>
      </div>
      {error && <p className="dim">{error}</p>}
      {!alarms && !error && <p className="dim">Yükleniyor…</p>}
      {alarms && events.length === 0 && (
        <p className="console-empty">Henüz olay kaydı yok.</p>
      )}
      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>Olay kayıtları</h2>
            <p>{events.length} kayıt · En yeni olay önce</p>
          </div>
        </div>
        <div className="tbl-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>Öncelik</th>
                <th>Pano</th>
                <th>Olay</th>
                <th>Zaman</th>
                <th>İnceleme</th>
              </tr>
            </thead>
            <tbody>
              {events.map((a) => (
                <tr key={a.event_id}>
                  <td>
                    <span className={`status-badge tone-${a.prio}`}>
                      {PRIO_NAME[a.prio]}
                    </span>
                  </td>
                  <td>
                    <Link to={`/pano/${a.pano_id}`}>{nameOf(a.pano_id)}</Link>
                    <div className="dim small">{a.pano_id}</div>
                  </td>
                  <td>{alarmText(a.code, a.text)}</td>
                  <td className="numeric">{ago(a.raised_at)}</td>
                  <td>
                    <Link className="btn ghost" to={`/olay/${a.event_id}`}>
                      Olayı incele <Icon name="arrow" size={14} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}

function KaraKutu({ eventId }: { eventId: string }) {
  const { panels } = useFleet();
  const [windowH, setWindowH] = useState<(typeof WINDOWS)[number]>(72);
  const [data, setData] = useState<Blackbox | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    setError(null);
    const controller = new AbortController();
    api
      .blackbox(eventId, windowH, controller.signal)
      .then(setData)
      .catch((e) => !controller.signal.aborted && setError(errorText(e)));
    return () => controller.abort();
  }, [eventId, windowH]);

  if (error) {
    return (
      <main className="page">
        <Link to="/olay" className="back">
          Olay analizi
        </Link>
        <div className="empty">
          <h1>Olay bulunamadı</h1>
          <p>{error}</p>
        </div>
      </main>
    );
  }
  if (!data) {
    return (
      <main className="page">
        <Link to="/olay" className="back">
          Olay analizi
        </Link>
        <p className="empty">Yükleniyor…</p>
      </main>
    );
  }

  const occurredMs = Date.parse(data.occurred_at);
  const markers: ChartMarker[] = [{ tMs: occurredMs, label: "Olay" }];
  const panoName =
    panels.find((p) => p.pano_id === data.pano_id)?.name ?? data.pano_id;
  const pointTags = Object.keys(data.series).filter((t) =>
    t.startsWith("t_conn."),
  );

  return (
    <main className="page">
      <Link to="/olay" className="back">
        Olay analizi
      </Link>
      <header className="ident">
        <span className="plate">{data.pano_id}</span>
        <h1>{alarmText(data.code)}</h1>
      </header>
      <p className="statement">
        <Link to={`/pano/${data.pano_id}`}>{panoName}</Link>
        {data.det_label ? `, ${data.det_label}` : ""} — {ago(data.occurred_at)}
      </p>

      <div className="console-filters" role="group" aria-label="Pencere">
        {WINDOWS.map((w) => (
          <button
            key={w}
            type="button"
            aria-pressed={windowH === w}
            onClick={() => setWindowH(w)}
          >
            {w} saat
          </button>
        ))}
      </div>

      <div className="split event-investigation">
        <div>
          {pointTags.length > 0 && (
            <section className="phases">
              <h3>Bağlantı sinyalleri</h3>
              <CizgiGrafik
                markers={markers}
                series={[
                  {
                    key: "dt",
                    label: "ΔT (K)",
                    color: "#D9530F",
                    points:
                      data.series[
                        pointTags.find((t) => t.endsWith(".dt_c")) ?? ""
                      ] ?? [],
                    axis: "right",
                  },
                  {
                    key: "k",
                    label: "K/K₀",
                    color: "#003DA5",
                    points:
                      data.series[
                        pointTags.find((t) => t.endsWith(".k_ratio")) ?? ""
                      ] ?? [],
                  },
                ]}
                yLabelLeft="K/K₀"
                yLabelRight="ΔT (K)"
              />
            </section>
          )}

          <section className="phases">
            <h3>Faz akımları</h3>
            <CizgiGrafik
              markers={markers}
              series={[
                {
                  key: "i0",
                  label: "L1 (A)",
                  color: "#003DA5",
                  points: data.series["elec.i_ph.0"] ?? [],
                },
                {
                  key: "i1",
                  label: "L2 (A)",
                  color: "#D9530F",
                  points: data.series["elec.i_ph.1"] ?? [],
                },
                {
                  key: "i2",
                  label: "L3 (A)",
                  color: "#1F8A70",
                  points: data.series["elec.i_ph.2"] ?? [],
                },
              ]}
              yLabelLeft="A"
            />
          </section>

          <section className="phases">
            <h3>Ortam</h3>
            <CizgiGrafik
              markers={markers}
              series={[
                {
                  key: "td",
                  label: "Çiy noktası marjı (K)",
                  color: "#1F8A70",
                  points: data.series["env.td_margin_k"] ?? [],
                },
              ]}
              yLabelLeft="K"
            />
          </section>

          <section className="phases">
            <h3>Risk skoru</h3>
            <CizgiGrafik
              markers={markers}
              yDomainLeft={[0, 100]}
              yLabelLeft="Risk (0–100)"
              series={[
                {
                  key: "risk",
                  label: "Risk (0-100)",
                  color: "#7A4FBE",
                  points: data.series["risk.score"] ?? [],
                },
              ]}
            />
          </section>
        </div>

        <div className="event-timeline panel">
          <span className="eyebrow">OLAY AKIŞI</span>
          <h3>Zaman çizelgesi</h3>
          <ul className="timeline">
            {data.timeline.map((entry, i) => (
              <li key={i} className={`k-${entry.kind}`}>
                <span className="tl-time">{ago(entry.ts)}</span>
                <span className="tl-text">
                  <span className="dim small">
                    {KIND_TR[entry.kind] ?? entry.kind}
                  </span>{" "}
                  — {entry.text}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </main>
  );
}
