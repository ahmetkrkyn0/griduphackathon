#!/usr/bin/env bash
# S1 — Gevşek bağlantı (rapor §8.2, ~90 sn): K yavaşça %200 artar, mutlak sıcaklık HÂLÂ limit altında.
# Beklenen: K/K₀ eşiği sabit 70 K eşiğinden ÇOK ÖNCE geçilir (ölçüm: 209 saat öne alma, docs/12).
source "$(dirname "${BASH_SOURCE[0]}")/_ortak.sh"

renk_baslik "S1 — Gevşek bağlantı (DSYA-3 L2)"
yigin_kontrol

PANO_ID="${1:-SIM-00001}"
SURE="${2:-90}"

if ! senaryo_oynat "S1_loose_conn" "$PANO_ID" "$SURE" --point DSYA3_L2; then
  senaryo_engelli_uyarisi "S1" "Gevşek bağlantı" "$FRONTEND_BASE/pano/ADM-00014"
  echo "  (Örnek veri modunda ADM-00014/Efeler TM-14 zaten bu senaryoyu canlandırır.)"
  exit 2
fi

echo
echo "İzleyin: $FRONTEND_BASE/pano/$PANO_ID (alarm konsolunda kart: Neden/Ne yapmalı/Ne kadar acil dolu olmalı)"
echo "Karşılaştırma: $FRONTEND_BASE/trend/$PANO_ID → I²-ΔT dağılımı, ilk/son yarı farklı eğim"
echo "Vurgu: yukarıdaki dökümde ALM-K-WARN'ın simüle saati ile ALM-THR-TERM-ALM'ınkini karşılaştırın."
