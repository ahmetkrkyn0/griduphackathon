#!/usr/bin/env bash
# S6 — Haberleşme kopması (rapor §8.2, ~45 sn): veri boşluğu oluşur.
# Beklenen: kenar tamponlar, heartbeat alarmı (ALM-COMMS-LOST); veri gelince boşluksuz dolar.
source "$(dirname "${BASH_SOURCE[0]}")/_ortak.sh"

renk_baslik "S6 — Haberleşme kopması"
yigin_kontrol

PANO_ID="${1:-SIM-00006}"
SURE="${2:-45}"

renk_uyari "ALM-COMMS-LOST'u MERKEZ üretir (heartbeat_timeout_min, sözleşme). Aşağıdaki kısa oynatmadaki"
renk_uyari "boşluk o eşiği aşmaz; alarmı canlı görmek için jüri demosunda şunu kullanın:"
echo "  docker compose -f '$COMPOSE_FILE' stop panosim   # birkaç dakika bekleyin"
echo "  docker compose -f '$COMPOSE_FILE' start panosim  # veri boşluksuz dolmalı"
echo

if ! senaryo_oynat "S6_comms_loss" "$PANO_ID" "$SURE"; then
  senaryo_engelli_uyarisi "S6" "Haberleşme kopması" "$FRONTEND_BASE/pano/GDZ-00410"
  echo "  (Örnek veri modunda GDZ-00410/Karşıyaka TM-9 zaten bu senaryoyu canlandırır: SYS, 7 dk sessiz.)"
  exit 2
fi

echo
echo "İzleyin: $FRONTEND_BASE/ → filoda SYS rozeti, sonra veri geri gelince boşluksuz dolmalı (backfill)"
echo "Not: boşluk süresince SAHTE DEĞER ÜRETİLMEZ — hiçbir mesaj yayınlanmaz (dürüstlük kuralı)."
