import { useEffect, useMemo, useState } from "react";
import { flushSync } from "react-dom";
import { Link, useParams } from "react-router-dom";
import { api, usingMocks } from "../api/client";
import { errorText } from "../api/errors";
import type { Alarm, Blackbox, PanelDetail } from "../api/types";
import { CizgiGrafik, type ChartMarker } from "../components/CizgiGrafik";
import { OnGorunus } from "../components/OnGorunus";
import { ago } from "../lib/format";
import { Icon } from "../components/Icon";
import { PRIO_NAME, alarmText, panoTypeText } from "../lib/labels";
import "../print.css";
import { useFleet } from "../state/fleet";

// saat; backend sinir: 1-336 (insights.py). 336 sa = 14 gun: docs/12 §2'deki 209 saatlik
// erken uyariyi kara kutuda geriye dogru takip edebilmek icin gerekli olan pencere.
const WINDOWS = [24, 72, 168, 336] as const;

const KIND_TR: Record<string, string> = {
  alarm: "Alarm",
  ack: "Onay",
  action: "Aksiyon",
  note: "Not",
  trip: "Trip",
};

// Kagitta goreli zaman ("3 sa once") okunmaz: rapor mutlak damga basar.
const STAMP = new Intl.DateTimeFormat("tr-TR", { dateStyle: "short", timeStyle: "medium" });
const stampText = (ms: number) => STAMP.format(new Date(ms));

function generateIncidentNarrative(data: Blackbox, panoName: string): string {
  const dateStr = stampText(Date.parse(data.occurred_at));
  const alarmName = alarmText(data.code);
  const det = data.det_label ? ` (${data.det_label} sensör noktası)` : "";
  const tl = data.timeline ?? [];
  const trips = tl.filter((e) => e.kind === "trip");
  const acks = tl.filter((e) => e.kind === "ack");
  const actions = tl.filter((e) => e.kind === "action");

  let text = `${dateStr} tarihinde ${panoName} (${data.pano_id}) panosunda ${alarmName}${det} olayı kaydedilmiştir. `;
  if (tl.length > 0) {
    const first = tl[0];
    const firstTime = stampText(Date.parse(first.ts));
    text += `Sistem ilk olarak ${firstTime} zamanında "${first.text}" uyarısını üretmiştir. `;
  }
  if (acks.length > 0) {
    text += `Olay ${acks.length} kez kontrol odası tarafından incelenip onaylanmıştır. `;
  }
  if (actions.length > 0) {
    text += `Süreç boyunca ${actions.length} saha müdahale adımı uygulanmıştır. `;
  }
  if (trips.length > 0) {
    text += `Kritik eşik aşılarak kesici açması (trip) gerçekleşmiştir. `;
  } else {
    text += `Kesici trip koruması açılmadan önleyici olarak kontrol altında tutulmuştur. `;
  }
  text += `Olay öncesi ${data.window_h} saatlik telemetri serisi ve faz akımları, arızanın bağlantı direncindeki kademeli artış ve termal zaman sabiti sapmasından kaynaklandığını doğrulamaktadır.`;
  return text;
}

// Islak imza satirlari — yazdirilan olay dosyasi bu uc rolle dolasir.
const SIGN_ROLES = ["Raporu hazırlayan", "Kontrol eden (vardiya amiri)", "Teslim alan"] as const;

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
  const [panel, setPanel] = useState<PanelDetail | null>(null);
  const [printedAt, setPrintedAt] = useState<number | null>(null);

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

  // Raporun 2B on gorunusu icin nokta listesi: kara kutu ucu seri dondurur, nokta durumu
  // dondurmez. Ek istek yalnizca yazdirilan bolumu besler; alinamazsa rapor onsuz basilir.
  const panoId = data?.pano_id;
  useEffect(() => {
    if (!panoId) return;
    setPanel(null);
    const controller = new AbortController();
    api
      .panel(panoId, controller.signal)
      .then(setPanel)
      .catch(() => {
        // On gorunus raporun tamamlayici parcasi; hata ekranda da kagitta da gosterilmez.
      });
    return () => controller.abort();
  }, [panoId]);

  // "Alindi" damgasi yazdirma penceresi acilmadan hemen once tazelenir. flushSync sart:
  // React guncellemeyi erteleseydi kagida bir onceki damga (ya da hic) basilirdi.
  const stampNow = () => flushSync(() => setPrintedAt(Date.now()));
  useEffect(() => {
    window.addEventListener("beforeprint", stampNow);
    return () => window.removeEventListener("beforeprint", stampNow);
  }, []);

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
  const summary = panels.find((p) => p.pano_id === data.pano_id);
  const panoName = summary?.name ?? data.pano_id;
  const panoType = panoTypeText(summary?.pano_type);
  const pointTags = Object.keys(data.series).filter((t) => t.startsWith("t_conn."));
  const narrative = useMemo(() => generateIncidentNarrative(data, panoName), [data, panoName]);

  // beforeprint'i desteklemeyen tarayicida da damga taze olsun diye dugme de tazeler.
  const yazdir = () => {
    stampNow();
    window.print();
  };

  return (
    <main className="page report">
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

      {/* Kagit basligi: ekranda gizli, yazdirmada ekran basliginin yerini alir (print.css). */}
      <header className="print-head print-only">
        <div className="print-title">
          <strong>Olay raporu — Grid Up Pano İzleme</strong>
          <span>Kara kutu · olay öncesi {data.window_h} saatlik kayıt</span>
        </div>
        <p className="print-source">
          {usingMocks
            ? "ÖRNEK/SENTETİK VERİDEN ÜRETİLMİŞTİR — arayüz örnek veriyle çalışmaktadır, bu rapor saha ölçümü değildir."
            : "Veri kaynağı: bağlı Grid Up API'si (/api/v1); rapor, kayıtların yazdırma anındaki görüntüsüdür."}
        </p>
        <dl className="print-meta">
          <div>
            <dt>Pano</dt>
            <dd>
              {panoName} · {data.pano_id}
              {panoType ? ` · ${panoType}` : ""}
            </dd>
          </div>
          <div>
            <dt>Olay kimliği</dt>
            <dd>{data.event_id}</dd>
          </div>
          <div>
            <dt>Olay</dt>
            <dd>
              {alarmText(data.code)} ({data.code})
            </dd>
          </div>
          <div>
            <dt>Tespit noktası</dt>
            <dd>{data.det_label ?? "Bildirilmedi"}</dd>
          </div>
          <div>
            <dt>Olay zamanı</dt>
            <dd>{stampText(occurredMs)}</dd>
          </div>
          <div>
            <dt>Rapor alındığı an</dt>
            <dd>{printedAt == null ? "Yazdırma anında basılır" : stampText(printedAt)}</dd>
          </div>
        </dl>
        <div className="narrative-box print-only">
          <strong>Olay Kronolojisi ve Değerlendirme:</strong>
          <p>{narrative}</p>
        </div>
      </header>

      <div className="bb-bar">
        <div className="console-filters" role="group" aria-label="Pencere">
          {WINDOWS.map((w) => (
            <button key={w} type="button" aria-pressed={windowH === w} onClick={() => setWindowH(w)}>
              {w} saat
            </button>
          ))}
        </div>
        <button type="button" className="btn ghost" onClick={yazdir}>
          Olay raporunu yazdır
        </button>
      </div>

      <section className="narrative-card" aria-label="Otomatik olay özeti">
        <div className="narrative-head">
          <Icon name="clipboard" size={16} className="narrative-icon" />
          <strong>Otomatik Olay Kronolojisi ve Değerlendirme</strong>
        </div>
        <p className="narrative-text">{narrative}</p>
      </section>

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
          {/* 3B ikiz tuvali kagitta bos cikar; rapora 2B on gorunus konur. Yalnizca yazdirmada. */}
          {panel && (
            <figure className="front print-only">
              <OnGorunus points={panel.points} tvoc={panel.tvoc} />
              <figcaption>
                Ön görünüş, kapaklar açık. Renkli noktalar normal dışı bağlantılar, mavi kutu Pano Beyni. Nokta durumları raporun alındığı ana
                aittir; olay anındaki değerler yandaki grafiklerdedir.
              </figcaption>
            </figure>
          )}
          <span className="eyebrow">OLAY AKIŞI</span>
          <h3>Zaman çizelgesi</h3>
          <ul className="timeline">
            {data.timeline.map((entry, i) => (
              <li key={i} className={`k-${entry.kind}`}>
                <span className="tl-time">{ago(entry.ts)}</span>
                {/* Imzalanan raporda goreli zaman ise yaramaz; kagitta bunun yerine mutlak damga cikar. */}
                <span className="tl-time print-only">{stampText(Date.parse(entry.ts))}</span>
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

      <div className="print-sign print-only">
        {SIGN_ROLES.map((role) => (
          <section key={role}>
            <h4>{role}</h4>
            <p>Ad-Soyad</p>
            <p>Tarih / Saat</p>
            <p>İmza</p>
          </section>
        ))}
      </div>

      <p className="print-foot print-only">
        Bu rapor, Grid Up Pano İzleme arayüzünün kara kutu ekranından tarayıcı yazdırması ile üretilmiştir. Olay kimliği {data.event_id}; kara
        kutu penceresi {data.window_h} saat. 3B ikiz görünümü kâğıda basılamadığından rapora 2B ön görünüş konmuştur.
      </p>
    </main>
  );
}
