#!/usr/bin/env bash
# S1 — Gevşek bağlantı (rapor §8.2, ~90 sn): K'yı artıracak şekilde ısıtıcı sürülür,
# mutlak sıcaklık HÂLÂ limit altında. Beklenen: K/K0 = 1,4 → P3, "tahmini N gün içinde 70 K".
source "$(dirname "${BASH_SOURCE[0]}")/_ortak.sh"

renk_baslik "S1 — Gevşek bağlantı (DSYA-3 L2)"
yigin_kontrol

if ! panoalgo_var_mi; then
  senaryo_engelli_uyarisi "S1" "Gevşek bağlantı" "$FRONTEND_BASE/pano/ADM-00014"
  echo "  (Örnek veri modunda ADM-00014/Efeler TM-14 zaten bu senaryoyu canlandırır.)"
  exit 2
fi

PANO_ID="${1:-SIM-00001}"
renk_ok "Senaryo oynatılıyor: $PANO_ID, S1_loose_conn, hız x60"
python3 -m sim.panosim --scenario S1_loose_conn --point DSYA3_L2 --pano "$PANO_ID" --speed 60 --duration 90 --mqtt "${GRIDUP_MQTT:-localhost:1883}"

echo
echo "İzleyin: $FRONTEND_BASE/pano/$PANO_ID (alarm konsolunda P3 kartı: Neden/Ne yapmalı/Ne kadar acil dolu olmalı)"
echo "Karşılaştırma: $FRONTEND_BASE/trend/$PANO_ID → I²-ΔT dağılımı, ilk/son yarı farklı eğim"
