#!/usr/bin/env bash
# S0 — Normal gün (rapor §8.2, ~60 sn): sağlıklı panonun 7 günlük yük profili hızlandırılmış oynatılır.
# Beklenen: Filo yeşil; I²-ΔT grafiğinde tek eğim ("yüksek yük ≠ arıza" mesajı).
source "$(dirname "${BASH_SOURCE[0]}")/_ortak.sh"

renk_baslik "S0 — Normal gün"
yigin_kontrol

PANO_ID="${1:-SIM-00001}"
SURE="${2:-60}"

# --season yaz: CANLI demo YAZ gününü oynatır. Gerekçesi ölçülmüştür
# (scripts/threshold_sweep.py --seasons, sözleşme eşiği 3,0 / 1,0 K sabit):
#   kış 28,6 · geçiş 71,4 · YAZ 0,0 çiy olayı / 100 pano / gün.
# Çiy noktası marjı yazda medyan +10,17 K olduğu için eşiğe hiç yaklaşılmaz.
# Eşik DEĞİŞMEDİ, senaryo mevsimi değişti: "sağlıklı pano yeşil durur" mesajı
# canlı demoda artık çiy uyarısıyla bölünmüyor. docs/12 §3'teki 71,4 sayısı
# senaryonun kendi mevsimiyle (geçiş) ölçülmeye devam eder — fixture'lar --season almaz.
if ! senaryo_oynat "S0_normal" "$PANO_ID" "$SURE" --season yaz; then
  senaryo_engelli_uyarisi "S0" "Normal gün" "$FRONTEND_BASE/"
  exit 2
fi

echo
echo "İzleyin: $FRONTEND_BASE/pano/$PANO_ID  (Trend & Korelasyon: $FRONTEND_BASE/trend/$PANO_ID)"
echo "Not: S0 yanlış alarm TABANIDIR ve bu koşu YAZ günüdür: beklenen alarm sayısı 0."
echo "     Geçiş mevsiminde aynı sağlıklı pano 100 pano/gün başına 71,4 çiy uyarısı üretir"
echo "     (docs/12 §3, sınır 150) — sayı algoritmayı değil iklimi ölçer; ölçüm docs/05 §11."
