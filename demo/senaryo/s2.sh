#!/usr/bin/env bash
# S2 — Aşırı yük (rapor §8.2, ~45 sn): üç fazda akım artırılır, tüm fazlar birlikte ısınır.
# Beklenen: "Aşırı yük — arıza değil" hipotezi, K normal kalır (HYP-OVERLOAD, yanlış alarm önleme).
source "$(dirname "${BASH_SOURCE[0]}")/_ortak.sh"

renk_baslik "S2 — Aşırı yük"
yigin_kontrol

if ! panoalgo_var_mi; then
  senaryo_engelli_uyarisi "S2" "Aşırı yük" "$FRONTEND_BASE/pano/GDZ-00088"
  echo "  (Örnek veri modunda GDZ-00088/Yunusemre TM-21 zaten bu senaryoyu canlandırır.)"
  exit 2
fi

PANO_ID="${1:-SIM-00002}"
renk_ok "Senaryo oynatılıyor: $PANO_ID, S2_overload, hız x60"
python3 -m sim.panosim --scenario S2_overload --pano "$PANO_ID" --speed 60 --duration 45 --mqtt "${GRIDUP_MQTT:-localhost:1883}"

echo
echo "İzleyin: $FRONTEND_BASE/pano/$PANO_ID → 'Aşırı yük, arıza değil' önerisi görünmeli, K/K₀ normalde kalmalı"
