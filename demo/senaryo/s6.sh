#!/usr/bin/env bash
# S6 — Haberleşme kopması (rapor §8.2, ~45 sn): ağ kablosu çekilir (veya sim durdurulur).
# Beklenen: kenar tamponlar, heartbeat alarmı (ALM-COMMS-LOST); kablo takılınca veri boşluksuz dolar.
source "$(dirname "${BASH_SOURCE[0]}")/_ortak.sh"

renk_baslik "S6 — Haberleşme kopması"
yigin_kontrol

if ! panoalgo_var_mi; then
  senaryo_engelli_uyarisi "S6" "Haberleşme kopması" "$FRONTEND_BASE/pano/GDZ-00410"
  echo "  (Örnek veri modunda GDZ-00410/Karşıyaka TM-9 zaten bu senaryoyu canlandırır: SYS, 7 dk sessiz.)"
  exit 2
fi

PANO_ID="${1:-SIM-00006}"
renk_ok "$PANO_ID için yayın 45 sn durduruluyor (heartbeat_timeout_min=5 aşılmayabilir, kısa demo)"
renk_uyari "Gerçek demoda: docker compose -f deploy/compose.yaml stop panosim  (birkaç dakika bekle)  sonra 'start' ile geri getir"
python3 -m sim.panosim --scenario S6_comms_loss --pano "$PANO_ID" --speed 60 --duration 45 --mqtt "${GRIDUP_MQTT:-localhost:1883}"

echo
echo "İzleyin: $FRONTEND_BASE/ → filoda SYS rozeti, sonra veri geri gelince boşluksuz dolmalı (backfill)"
