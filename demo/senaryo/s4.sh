#!/usr/bin/env bash
# S4 — Ark olayı (rapor §8.2, ~60 sn): LED flaşı → TVOC-2 simülatöründe trip sayacı (PDU 149) ve
# dedektör bitleri değişir. Beklenen: P1 → telefona SMS + WhatsApp, SCADA'da alarm biti,
# kara kutuda olay öncesi ısınma.
source "$(dirname "${BASH_SOURCE[0]}")/_ortak.sh"

renk_baslik "S4 — Ark olayı (TVOC-2 tripi)"
yigin_kontrol

if ! panoalgo_var_mi; then
  senaryo_engelli_uyarisi "S4" "Ark olayı" "$FRONTEND_BASE/olay"
  echo "  (Örnek veri modunda GDZ-00512/Selçuk TM-1 → Kara Kutu ekranında bu senaryo hazır: EVT-60.)"
  exit 2
fi

PANO_ID="${1:-SIM-00004}"
renk_ok "Senaryo oynatılıyor: $PANO_ID, S4_arc, hız x60"
python3 -m sim.panosim --scenario S4_arc --pano "$PANO_ID" --speed 60 --duration 60 --mqtt "${GRIDUP_MQTT:-localhost:1883}"

echo
echo "İzleyin: $FRONTEND_BASE/alarmlar → P1 kartı; telefonda gerçek SMS/WhatsApp (bkz. deploy/runtime/sms-log.txt)"
echo "Kara kutu: $FRONTEND_BASE/olay → olay öncesi 72 saatlik sinyaller + zaman çizelgesi"
