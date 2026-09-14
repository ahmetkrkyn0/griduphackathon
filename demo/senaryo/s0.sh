#!/usr/bin/env bash
# S0 — Normal gün (rapor §8.2, ~60 sn): sağlıklı panonun 7 günlük yük profili hızlandırılmış oynatılır.
# Beklenen: Filo yeşil; I²-ΔT grafiğinde tek eğim ("yüksek yük ≠ arıza" mesajı).
source "$(dirname "${BASH_SOURCE[0]}")/_ortak.sh"

renk_baslik "S0 — Normal gün"
yigin_kontrol

PANO_ID="${1:-SIM-00001}"
SURE="${2:-60}"

if ! senaryo_oynat "S0_normal" "$PANO_ID" "$SURE"; then
  senaryo_engelli_uyarisi "S0" "Normal gün" "$FRONTEND_BASE/"
  exit 2
fi

echo
echo "İzleyin: $FRONTEND_BASE/pano/$PANO_ID  (Trend & Korelasyon: $FRONTEND_BASE/trend/$PANO_ID)"
echo "Not: S0 yanlış alarm TABANIDIR. docs/12 §3 — 100 pano/gün başına 71,4 alarm (sınır 150),"
echo "     ağırlıklı olarak çiy noktası uyarıları. 'Sıfır alarm' beklemeyin; sınır içinde kalması beklenir."
