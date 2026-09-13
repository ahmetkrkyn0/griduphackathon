const formatters = new Map<number, Intl.NumberFormat>();

function formatter(digits: number): Intl.NumberFormat {
  let f = formatters.get(digits);
  if (!f) {
    f = new Intl.NumberFormat("tr-TR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
    formatters.set(digits, f);
  }
  return f;
}

/** Turkce sayi bicimi: 1,64 · 2.410. Eksik deger "–". */
export function num(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "–";
  return formatter(digits).format(value);
}

/** Olcum degeri icin makul hassasiyet: tamsayi, kucuk oran (2 hane), digerleri (1 hane). */
export function measure(value: number): string {
  if (Number.isInteger(value)) return num(value, 0);
  return Math.abs(value) < 10 ? num(value, 2) : num(value, 1);
}

/** Sinira kalan sure: 48 saatin altinda saat, ustunde gun. */
export function ttlText(hours: number | null | undefined): string | null {
  if (hours == null) return null;
  if (hours < 1) return "1 saatten az";
  if (hours < 48) return `${Math.round(hours)} saat`;
  return `${Math.round(hours / 24)} gün`;
}

/** "10 sn önce", "7 dk önce", "3 sa önce", "2 gün önce". */
export function ago(iso: string, now = Date.now()): string {
  const seconds = Math.max(0, Math.round((now - Date.parse(iso)) / 1000));
  if (seconds < 60) return `${seconds} sn önce`;
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins} dk önce`;
  const hours = Math.floor(mins / 60);
  if (hours < 48) return `${hours} sa önce`;
  return `${Math.floor(hours / 24)} gün önce`;
}
