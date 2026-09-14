#!/usr/bin/env bash
# S0 — Normal gün (rapor §8.2, ~60 sn): 24 saatlik yük profili hızlandırılmış oynatılır.
# Beklenen: Filo yeşil; I²-ΔT grafiğinde tek eğim ("yüksek yük ≠ arıza" mesajı).
source "$(dirname "${BASH_SOURCE[0]}")/_ortak.sh"

renk_baslik "S0 — Normal gün"
yigin_kontrol

if ! panoalgo_var_mi; then
  senaryo_engelli_uyarisi "S0" "Normal gün" "$FRONTEND_BASE/"
  exit 2
fi

PANO_ID="${1:-SIM-00001}"
renk_ok "Senaryo oynatılıyor: $PANO_ID, S0_normal, hız x60"
python3 -m sim.panosim --scenario S0_normal --pano "$PANO_ID" --speed 60 --duration 60 --mqtt "${GRIDUP_MQTT:-localhost:1883}"

echo
echo "İzleyin: $FRONTEND_BASE/pano/$PANO_ID  (Trend & Korelasyon: $FRONTEND_BASE/trend/$PANO_ID)"
