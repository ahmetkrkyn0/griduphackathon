#!/usr/bin/env bash
# S3 — Yoğuşma (rapor §8.2, ~60 sn): kış gecesi nem yükselir, yüzey çiy noktasının altına iner.
# Beklenen: P2 → ısıtıcı rölesi önerisi → marj düzelir → alarm temizlenir.
source "$(dirname "${BASH_SOURCE[0]}")/_ortak.sh"

renk_baslik "S3 — Yoğuşma"
yigin_kontrol

PANO_ID="${1:-SIM-00003}"
SURE="${2:-60}"

if ! senaryo_oynat "S3_condense" "$PANO_ID" "$SURE"; then
  senaryo_engelli_uyarisi "S3" "Yoğuşma" "$FRONTEND_BASE/pano/ADM-00102"
  echo "  (Örnek veri modunda ADM-00102/Merkezefendi TM-7 zaten bu senaryoyu canlandırır.)"
  exit 2
fi

echo
echo "İzleyin: $FRONTEND_BASE/pano/$PANO_ID → ALM-DEW-ALM (P2), çiy noktası marjı grafiği"
