import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { ApiError, errorText } from "../api/errors";
import type { Alarm, ConnPoint, PanelDetail, SeriesResponse } from "../api/types";
import { AlarmNedeni } from "../components/AlarmNedeni";
import { CizgiGrafik } from "../components/CizgiGrafik";
import { OnGorunus } from "../components/OnGorunus";
import { PrioMark } from "../components/PrioMark";
import { ago, num, ttlText } from "../lib/format";
import { STATE_TEXT, alarmText, hypText, panoTypeText, pointLabel } from "../lib/labels";
import { phaseGroup } from "../lib/panelGeometry";
import { useNow } from "../lib/useNow";
import { panelStatement, primaryAlarm } from "../lib/worklist";
import { useFleet } from "../state/fleet";

// Kimlik dogrulama henuz yok (yol haritasi: LDAP); onay kontrol odasi adina kaydedilir.
const OPERATOR = "kontrol-odasi";
const DETAIL_REFRESH_MS = 30_000;

interface LoadError {
  status: number | null;
  text: string;
}

export function PanoDetay() {
  const { panoId = "" } = useParams();
  const { panels, touched } = useFleet();
  useNow(5000);

  const [detail, setDetail] = useState<PanelDetail | null>(null);
  const [loadError, setLoadError] = useState<LoadError | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [ackBusy, setAckBusy] = useState(false);
  const [shelveBusy, setShelveBusy] = useState(false);
  const [alarmMessage, setAlarmMessage] = useState<string | null>(null);

  useEffect(() => {
    setDetail(null);
    setLoadError(null);
    setSelected(null);
    setAlarmMessage(null);
  }, [panoId]);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const next = await api.panel(panoId, signal);
        setDetail(next);
        setLoadError(null);
      } catch (e) {
        if (signal?.aborted) return;
        setLoadError({ status: e instanceof ApiError ? e.status : null, text: errorText(e) });
      }
    },
    [panoId],
  );

  // Canli akista bu pano guncellenince yeniden yukle; akis yoksa periyodik yenile.
  const version = touched[panoId] ?? 0;
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load, version]);

  useEffect(() => {
    const timer = setInterval(() => void load(), DETAIL_REFRESH_MS);
    return () => clearInterval(timer);
  }, [load]);

  const onAck = async (alarm: Alarm, note: string) => {
    setAckBusy(true);
    setAlarmMessage(null);
    try {
      await api.ack(alarm.id, { by: OPERATOR, channel: "ui", note: note || undefined });
      setAlarmMessage("Onaylandı.");
      await load();
    } catch (e) {
      setAlarmMessage(
        e instanceof ApiError && e.status === 409
          ? "Bu alarm zaten onaylanmış veya temizlenmiş."
          : `Onaylanamadı: ${errorText(e)}`,
      );
    } finally {
      setAckBusy(false);
    }
  };

  const onShelve = async (alarm: Alarm, minutes: number, reason: string) => {
    setShelveBusy(true);
    setAlarmMessage(null);
    try {
      await api.shelve(alarm.id, { by: OPERATOR, minutes, reason });
      setAlarmMessage("Rafa alındı.");
      await load();
    } catch (e) {
      setAlarmMessage(
        e instanceof ApiError && e.status === 403
          ? "P1 alarm rafa alınamaz."
          : `Rafa alınamadı: ${errorText(e)}`,
      );
    } finally {
      setShelveBusy(false);
    }
  };

  if (loadError?.status === 404 || loadError?.status === 422) {
    return (
      <main className="page">
        <Link to="/" className="back">
          Filo
        </Link>
        <div className="empty">
          <h1>{panoId} bulunamadı</h1>
          <p>Bu kimlikle kayıtlı pano yok. Filo ekranından bir pano seçin.</p>
        </div>
      </main>
    );
  }

  if (!detail) {
    return (
      <main className="page">
        <Link to="/" className="back">
          Filo
        </Link>
        {loadError ? (
          <div className="empty">
            <h1>Pano verisi alınamadı</h1>
            <p>{loadError.text}. Sayfa 30 saniyede bir yeniden dener.</p>
          </div>
        ) : (
          <p className="empty">Pano yükleniyor…</p>
        )}
      </main>
    );
  }

  const alarms = detail.active_alarms ?? [];
  const primary = primaryAlarm(alarms);
  const others = alarms.filter((a) => a !== primary && a.state !== "cleared");
  const focus = selected ?? primary?.reason?.point ?? null;
  const group = focus ? phaseGroup(detail.points, focus) : [];
  const summary = panels.find((p) => p.pano_id === panoId);
  const subtitle = [panoTypeText(detail.pano_type), hypText(detail.risk_mode), `risk ${detail.risk_score ?? 0}`, `son veri ${ago(detail.ts)}`]
    .filter(Boolean)
    .join(", ");

  return (
    <main className="page">
      <Link to="/" className="back">
        Filo
      </Link>
      <header className="ident">
        <span className="plate">{detail.pano_id}</span>
        <h1>{detail.name ?? detail.pano_id}</h1>
        <span className="dim">{subtitle}</span>
        {summary && !summary.comms_ok && <span className="tag-bad">Bağlantı yok, veriler eski</span>}
      </header>

      <p className="statement">{panelStatement(detail, primary)}</p>
      {loadError && (
        <p className="dim" role="status">
          Son yenileme başarısız: {loadError.text}
        </p>
      )}

      <div className="split">
        <figure className="front">
          <OnGorunus points={detail.points} selected={focus} onSelect={setSelected} />
          <figcaption>
            Ön görünüş, kapaklar açık. Renkli noktalar normal dışı bağlantılar, mavi kutu Pano Beyni. Fazlarını
            karşılaştırmak için bir nokta seçin.
          </figcaption>
        </figure>

        <div>
          {primary ? (
            <AlarmNedeni alarm={primary} onAck={onAck} onShelve={onShelve} ackBusy={ackBusy} shelveBusy={shelveBusy} message={alarmMessage} />
          ) : (
            <p className="calm">Aktif alarm yok.</p>
          )}

          {others.length > 0 && (
            <section className="others">
              <h3>Diğer aktif alarmlar</h3>
              <ul>
                {others.map((a) => (
                  <li key={a.id}>
                    <PrioMark prio={a.prio} acked={a.state === "acked"} small />
                    <span>{alarmText(a.code, a.text)}</span>
                    <span className="dim">{ago(a.raised_at)}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {group.length > 0 && <FazKarsilastirma points={group} focus={focus} />}
          {focus && <NoktaTrendi panoId={panoId} point={focus} label={group.find((p) => p.pt === focus)?.label ?? pointLabel(focus)} />}
        </div>
      </div>

      <PanoOzeti detail={detail} />
      <OlcumTablosu points={detail.points} selected={focus} onSelect={setSelected} />
    </main>
  );
}

function FazKarsilastirma({ points, focus }: { points: ConnPoint[]; focus: string | null }) {
  const scale = Math.max(1, ...points.map((p) => p.dt_c));
  const groupName = points[0].pt.startsWith("GIRIS") ? "Giriş" : pointLabel(points[0].pt).split(" ")[0];
  return (
    <section className="phases">
      <h3>{groupName} faz karşılaştırması</h3>
      <p className="dim small">Ortam üstü sıcaklık artışı; çubuklar gruptaki en yüksek değere göre ölçeklenir.</p>
      {points.map((p) => {
        const state = p.state ?? "normal";
        return (
          <div key={p.pt} className={`ph st-${state}${p.pt === focus ? " focus" : ""}`}>
            <span>{p.label ?? pointLabel(p.pt)}</span>
            <span className="ph-track">
              <span className="ph-fill" style={{ width: `${(p.dt_c / scale) * 100}%` }} />
            </span>
            <span className="ph-v">{num(p.dt_c)} K</span>
          </div>
        );
      })}
    </section>
  );
}

const TREND_RANGES = [
  { days: 7, label: "7 gün", step: "30m" },
  { days: 14, label: "14 gün", step: "1h" },
  { days: 30, label: "30 gün", step: "2h" },
];

/** TC2: nokta tıklanınca gerçek zaman serisi trendi (K/K₀ ve ΔT), GET /panels/{id}/series. */
function NoktaTrendi({ panoId, point, label }: { panoId: string; point: string; label: string }) {
  const [rangeIdx, setRangeIdx] = useState(1);
  const [data, setData] = useState<SeriesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const range = TREND_RANGES[rangeIdx];

  useEffect(() => {
    setData(null);
    setError(null);
    const controller = new AbortController();
    const to = new Date();
    const from = new Date(to.getTime() - range.days * 86_400_000);
    api
      .series(panoId, [`t_conn.${point}.k_ratio`, `t_conn.${point}.dt_c`], from, to, range.step, controller.signal)
      .then(setData)
      .catch((e) => !controller.signal.aborted && setError(errorText(e)));
    return () => controller.abort();
  }, [panoId, point, range.days, range.step]);

  return (
    <section className="phases">
      <h3>{label} trendi</h3>
      <div className="chart-range" role="group" aria-label="Zaman aralığı">
        {TREND_RANGES.map((r, i) => (
          <button key={r.label} type="button" aria-pressed={i === rangeIdx} onClick={() => setRangeIdx(i)}>
            {r.label}
          </button>
        ))}
      </div>
      {error && <p className="dim small">{error}</p>}
      {!data && !error && <p className="dim small">Yükleniyor…</p>}
      {data && (
        <CizgiGrafik
          series={[
            { key: "k", label: "K/K₀", color: "#2C63C9", points: data[`t_conn.${point}.k_ratio`] ?? [] },
            { key: "dt", label: "Ortam üstü artış (K)", color: "#DD6418", points: data[`t_conn.${point}.dt_c`] ?? [], axis: "right" },
          ]}
          yLabelLeft="K/K₀"
          yLabelRight="ΔT (K)"
        />
      )}
    </section>
  );
}

function PanoOzeti({ detail }: { detail: PanelDetail }) {
  const env = detail.env ?? {};
  const elec = detail.elec ?? {};
  const health = detail.health ?? {};
  const tvoc = detail.tvoc;
  const facts: Array<{ k: string; v: string; bad?: boolean }> = [];

  if (elec.i_ph?.length) facts.push({ k: "Faz akımları", v: `${elec.i_ph.map((i) => num(i, 0)).join(" / ")} A` });
  if (elec.i_n != null) facts.push({ k: "Nötr akımı", v: `${num(elec.i_n, 0)} A` });
  if (elec.thd_i?.length) facts.push({ k: "En yüksek akım THD", v: `%${num(Math.max(...elec.thd_i))}` });
  if (elec.cosphi != null) facts.push({ k: "Güç faktörü", v: num(elec.cosphi, 2) });
  if (env.td_margin_k != null) facts.push({ k: "Çiy noktası marjı", v: `${num(env.td_margin_k)} K` });
  if (env.t_low_c != null && env.t_up_c != null) facts.push({ k: "Alt / üst ortam", v: `${num(env.t_low_c)} / ${num(env.t_up_c)} °C` });
  if (env.rh_low_pct != null) facts.push({ k: "Alt bağıl nem", v: `%${num(env.rh_low_pct, 0)}` });
  if (tvoc) {
    const broken = tvoc.prot_health_ok === false;
    const where = tvoc.last_det_label ? ` (${tvoc.last_det_label})` : "";
    facts.push({ k: "Ark koruması", v: broken ? `Dedektör arızalı${where}` : `Sağlam, ${tvoc.trips ?? 0} trip`, bad: broken });
  }
  if (health.nodes_total != null) facts.push({ k: "Sensör düğümleri", v: `${health.nodes_ok ?? 0} / ${health.nodes_total}`, bad: (health.nodes_ok ?? 0) < health.nodes_total });
  if (health.rssi_dbm != null) facts.push({ k: "Hücresel sinyal", v: `${num(health.rssi_dbm, 0)} dBm` });
  if (health.buffered) facts.push({ k: "Tamponda bekleyen", v: `${health.buffered} mesaj` });
  if (health.baseline_day != null) facts.push({ k: "Taban öğrenme", v: `${health.baseline_day}. gün` });
  if (health.fw) facts.push({ k: "Yazılım sürümü", v: health.fw });

  if (facts.length === 0) return null;
  return (
    <div className="facts" aria-label="Pano ölçüm özeti">
      {facts.map((f) => (
        <div key={f.k} className={f.bad ? "fact bad" : "fact"}>
          <div className="k">{f.k}</div>
          <div className="v">{f.v}</div>
        </div>
      ))}
    </div>
  );
}

function OlcumTablosu({ points, selected, onSelect }: { points: ConnPoint[]; selected: string | null; onSelect: (pt: string) => void }) {
  if (points.length === 0) return null;
  return (
    <details className="points">
      <summary>Tüm ölçüm noktaları ({points.length})</summary>
      <div className="tbl-wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th>Nokta</th>
              <th className="r">Sıcaklık</th>
              <th className="r">Ortam üstü artış</th>
              <th className="r">K/K₀</th>
              <th className="r">Sınıra</th>
              <th>Durum</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => {
              const state = p.state ?? "normal";
              return (
                <tr key={p.pt} className={p.pt === selected ? "sel" : undefined}>
                  <td>
                    <button type="button" className="linklike" onClick={() => onSelect(p.pt)}>
                      {p.label ?? pointLabel(p.pt)}
                    </button>
                  </td>
                  <td className="r">{num(p.t_c)} °C</td>
                  <td className="r">{num(p.dt_c)} K</td>
                  <td className="r">{num(p.k_ratio, 2)}</td>
                  <td className="r">{ttlText(p.ttl_h) ?? "–"}</td>
                  <td>
                    <span className={`state st-${state}`}>{STATE_TEXT[state]}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </details>
  );
}
