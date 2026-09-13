// Kod -> Turkce metin. contracts/alarm-codes.yaml ASCII metin tasir; arayuz dili Turkce (GK8).
// ESIK DEGERI YOK (kural 10): sayilar API'nin reason.signals[].threshold alanindan gelir.
// labels.test.ts, sozlesmedeki her kodun burada karsiligi oldugunu denetler.

import type { NotifyChannel, PointState, Prio } from "../api/types";

export const PRIO_NAME: Record<Prio, string> = {
  P1: "Kritik",
  P2: "Alarm",
  P3: "Uyarı",
  INFO: "Bilgi",
  SYS: "Sistem",
};

export const STATE_TEXT: Record<PointState, string> = {
  normal: "Normal",
  warn: "Uyarı",
  alarm: "Alarm",
  critical: "Kritik",
  stale: "Veri eski",
};

export const CHANNEL_TEXT: Record<NotifyChannel, string> = {
  sms: "SMS",
  whatsapp: "WhatsApp",
  call: "sesli arama",
  scada: "SCADA",
  relay: "yerel röle",
};

export const ALARM_TEXT: Record<string, string> = {
  "ALM-THR-TERM-WARN": "Terminal sıcaklık artışı uyarı sınırını aştı",
  "ALM-THR-TERM-ALM": "Terminal sıcaklık artışı alarm sınırını aştı",
  "ALM-THR-BUS-ALM": "Bara sıcaklık artışı tavlanma sınırını aştı",
  "ALM-THR-PHASE-DIF": "Benzer yükte fazlar arası sıcaklık farkı yüksek",
  "ALM-K-WARN": "Isıl direnç indeksi yükseliyor, bağlantı direnci artışı şüphesi",
  "ALM-K-ALM": "Isıl direnç indeksi yüksek, gevşek veya oksitlenmiş bağlantı",
  "ALM-TTL-14D": "Bağlantı iki hafta içinde terminal sınırına ulaşabilir",
  "ALM-DEW-WARN": "Çiy noktası marjı daralıyor",
  "ALM-DEW-ALM": "Çiy noktası marjı çok düşük, yoğuşma riski",
  "ALM-I-OVER": "Faz akımı anma değerinin üstünde",
  "ALM-NEUTRAL-THD": "Nötr akımı ve akım THD birlikte arttı, harmonik kaynaklı nötr ısınması",
  "ALM-ARC-TRIP": "Ark koruması (TVOC-2) açtı",
  "ALM-PROT-HEALTH": "Ark koruması dedektör arızası, pano sessizce korumasız",
  "ALM-PD-TREND": "Kısmi deşarj darbe sayısı ve genliği artıyor (OG)",
  "ALM-DQ-FROZEN": "Sensör değeri donmuş",
  "ALM-DQ-JUMP": "Sensörde fiziksel olmayan değişim hızı",
  "ALM-DQ-BELOW-AMBIENT": "Bağlantı sıcaklığı ortamın altında, sensör yerinden düşmüş olabilir",
  "ALM-NODE-LOST": "Sensör düğümü sessiz",
  "ALM-COMMS-LOST": "Merkez bağlantısı koptu",
  "ALM-DOOR-UNAUTH": "Planlı iş emri olmadan kapak açıldı",
  "ALM-LASTGASP": "Besleme kesildi (son nefes mesajı)",
  "ALM-PANEL-TEMP": "Pano iç ortam sıcaklığı alarm sınırının üstünde",
};

export const HYP_TEXT: Record<string, string> = {
  "HYP-LOOSE-CONN": "Gevşek bağlantı",
  "HYP-OVERLOAD": "Aşırı yük, arıza değil",
  "HYP-CONDENSE": "Yoğuşma",
  "HYP-HARMONIC": "Harmonik kaynaklı nötr ısınması",
  "HYP-PD": "İzolasyon bozulması (OG)",
  "HYP-ARC": "Ark olayı",
  "HYP-PROT-LOSS": "Koruma sağlığı kaybı",
  "HYP-SELF-FAULT": "İzleme sistemi arızası",
  "HYP-NORMAL": "Normal",
};

// Anahtar: sozlesmedeki hypotheses[].advice metninin kendisi (API bu metni gonderir).
export const ADVICE_TEXT: Record<string, string> = {
  "Planli bakimda tork kontrolu ve temizlik; kritik evrede yuk azaltma onerisi":
    "Planlı bakımda tork kontrolü ve temizlik yapın; kritik evrede yük azaltmayı değerlendirin.",
  "Yuk transferi / fider duzenleme onerisi": "Yük aktarımı veya fider düzenlemesi önerilir.",
  "Anti-kondensasyon isiticisi ac; conta ve havalandirma kontrolu":
    "Anti-kondensasyon ısıtıcısını açın; conta ve havalandırmayı kontrol edin.",
  "Guc kalitesi incelemesi": "Güç kalitesi incelemesi yapın.",
  "Offline test planla": "Enerjisiz (offline) izolasyon testi planlayın.",
  "Kritik alarm; olay oncesi 72 saatlik kara kutu raporu. Reset SAHADA yapilir.":
    "Kritik alarm. Olay öncesi 72 saatlik kara kutu raporunu inceleyin. Reset yalnızca sahada yapılır.",
  "Dedektor/fiber bakimi — pano korumasiz": "Dedektör ve fiber bakımı gerekiyor; pano şu an korumasız.",
  "Uzaktan diagnostik; gerekirse saha ziyareti. ARIZA ALARMI DEGIL.":
    "Uzaktan tanılama yapın, gerekirse saha ziyareti planlayın. Bu bir arıza alarmı değil.",
};

const FIELD_TEXT: Record<string, string> = {
  t_c: "sıcaklığı",
  dt_c: "ortam üstü sıcaklık artışı",
  k: "ısıl direnci",
  k_ratio: "ısıl direnç indeksi",
  ttl_h: "sınıra kalan süre",
};

const ENV_TEXT: Record<string, string> = {
  t_low_c: "Alt ortam sıcaklığı",
  rh_low_pct: "Alt bağıl nem",
  td_low_c: "Çiy noktası",
  td_margin_k: "Çiy noktası marjı",
  t_up_c: "Üst ortam sıcaklığı",
  rh_up_pct: "Üst bağıl nem",
  dt_air_k: "Üst ile alt hava sıcaklık farkı",
  voc_idx: "Gaz/VOC indeksi",
};

const ELEC_TEXT: Record<string, string> = {
  i_ph: "faz akımı",
  u_ph: "faz gerilimi",
  thd_i: "akım THD",
  i_n: "Nötr akımı",
  cosphi: "Güç faktörü",
  unbal_pct: "Faz dengesizliği",
};

const TVOC_TEXT: Record<string, string> = {
  prot_health_ok: "Ark koruması sağlık durumu",
  trips: "Ark koruması trip sayısı",
  state: "Ark koruması sistem durumu",
};

const UNIT_TEXT: Record<string, string> = {
  "K/K0": "K/K₀",
  h: "saat",
  min: "dk",
};

/** GIRIS_L2 -> "Giriş L2", DSYA3_L2 -> "DSYA-3 L2" (backend views.point_label ile ayni). */
export function pointLabel(pt: string): string {
  if (pt.startsWith("GIRIS_")) return `Giriş ${pt.slice("GIRIS_".length)}`;
  const match = /^DSYA(\d)_(L\d)$/.exec(pt);
  return match ? `DSYA-${match[1]} ${match[2]}` : pt;
}

export function alarmText(code: string, fallback?: string): string {
  return ALARM_TEXT[code] ?? fallback ?? code;
}

export function hypText(code: string | undefined): string {
  if (!code) return "Bilinmiyor";
  return HYP_TEXT[code] ?? code;
}

export function adviceText(advice: string | undefined): string | null {
  if (!advice || advice === "-") return null;
  return ADVICE_TEXT[advice] ?? advice;
}

/** Telemetri etiketi -> okunur ad: "t_conn.DSYA3_L2.k_ratio" -> "DSYA-3 L2 ısıl direnç indeksi". */
export function signalLabel(tag: string): string {
  const parts = tag.split(".");
  const [group, field, index] = parts;
  if (group === "t_conn" && parts.length === 3 && FIELD_TEXT[index]) return `${pointLabel(field)} ${FIELD_TEXT[index]}`;
  if (group === "env" && ENV_TEXT[field]) return ENV_TEXT[field];
  if (group === "elec" && ELEC_TEXT[field]) {
    return parts.length === 3 ? `L${Number(index) + 1} ${ELEC_TEXT[field]}` : ELEC_TEXT[field];
  }
  if (group === "tvoc" && TVOC_TEXT[field]) return TVOC_TEXT[field];
  if (tag === "last_rx_age_min") return "Son veriden bu yana geçen süre";
  return tag;
}

export function unitText(unit: string | undefined): string {
  if (!unit) return "";
  return UNIT_TEXT[unit] ?? unit;
}

/** "1600kVA-dahili" -> "1600 kVA dahili". */
export function panoTypeText(type: string | undefined): string | null {
  if (!type) return null;
  return type.replace(/^(\d+)kVA-(.+)$/, "$1 kVA $2");
}
