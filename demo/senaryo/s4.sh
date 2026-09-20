#!/usr/bin/env bash
# S4 — Ark olayı (rapor §8.2, ~60 sn): TVOC-2 trip sayacı (PDU 149) artar.
# Beklenen: P1 → telefona SMS + WhatsApp, SCADA'da alarm biti, kara kutuda olay öncesi ısınma.
source "$(dirname "${BASH_SOURCE[0]}")/_ortak.sh"

renk_baslik "S4 — Ark olayı (TVOC-2 tripi)"
yigin_kontrol

PANO_ID="${1:-SIM-00004}"
SURE="${2:-60}"

if ! senaryo_oynat "S4_arc" "$PANO_ID" "$SURE"; then
  senaryo_engelli_uyarisi "S4" "Ark olayı" "$FRONTEND_BASE/olay"
  echo "  (Örnek veri modunda GDZ-00512/Selçuk TM-1 → Kara Kutu ekranında bu senaryo hazır: EVT-60.)"
  exit 2
fi

backend_alarm_dokumu "$PANO_ID"

echo
echo "İzleyin: $FRONTEND_BASE/alarmlar → P1 kartı; SMS sanal modeme düşer (gerçek donanım değil): deploy/runtime/sms-log.txt"
echo "Kara kutu: $FRONTEND_BASE/olay → olay öncesi 72 saatlik sinyaller + zaman çizelgesi"
echo "Cihaz tarafı: aynı tripi Modbus düzeyinde de göstermek için"
echo "  docker compose -f '$COMPOSE_FILE' run --rm -p 5021:5021 tvoc-sim python tvoc2_sim.py --slave-id 10 --trip-after 20"
