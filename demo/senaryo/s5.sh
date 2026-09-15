#!/usr/bin/env bash
# S5 — Koruma sağlığı (rapor §8.2, ~30 sn): TVOC-2 sensör durum biti (PDU 222) düşer.
# Beklenen: "Pano korumasız: X2:4 dedektörü arızalı" — operasyonu anlama kanıtı.
source "$(dirname "${BASH_SOURCE[0]}")/_ortak.sh"

renk_baslik "S5 — Koruma sağlığı kaybı"
yigin_kontrol

PANO_ID="${1:-SIM-00005}"
SURE="${2:-30}"
DEDEKTOR="${3:-X2:4}"

if ! senaryo_oynat "S5_prot_health" "$PANO_ID" "$SURE" --detector "$DEDEKTOR"; then
  senaryo_engelli_uyarisi "S5" "Koruma sağlığı" "$FRONTEND_BASE/pano/GDZ-00231"
  echo "  (Örnek veri modunda GDZ-00231/Bornova DM-3 zaten bu senaryoyu canlandırır: P1, X2:4 arızalı.)"
  exit 2
fi

echo
echo "İzleyin: $FRONTEND_BASE/pano/$PANO_ID → 'Ark koruması dedektör arızası, pano sessizce korumasız' (P1)"
echo "Telemetride tvoc.sensor_x2 register'ında $DEDEKTOR'ün biti 0'dır (PDU 222); kalan dedektörler 1."
