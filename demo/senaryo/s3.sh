#!/usr/bin/env bash
# S3 — Yoğuşma (rapor §8.2, ~60 sn): nemlendirici çalışır, çiy noktası marjı düşer.
# Beklenen: P2 → ısıtıcı rölesi OTOMATİK açılır → marj düzelir → alarm temizlenir.
source "$(dirname "${BASH_SOURCE[0]}")/_ortak.sh"

renk_baslik "S3 — Yoğuşma"
yigin_kontrol

if ! panoalgo_var_mi; then
  senaryo_engelli_uyarisi "S3" "Yoğuşma" "$FRONTEND_BASE/pano/ADM-00102"
  echo "  (Örnek veri modunda ADM-00102/Merkezefendi TM-7 zaten bu senaryoyu canlandırır.)"
  exit 2
fi

PANO_ID="${1:-SIM-00003}"
renk_ok "Senaryo oynatılıyor: $PANO_ID, S3_condense, hız x60"
python3 -m sim.panosim --scenario S3_condense --pano "$PANO_ID" --speed 60 --duration 60 --mqtt "${GRIDUP_MQTT:-localhost:1883}"

echo
echo "İzleyin: $FRONTEND_BASE/pano/$PANO_ID → ALM-DEW-ALM (P2), sonra 'ısıtıcı otomatik açıldı' notu, alarm temizlenmeli"
