#!/usr/bin/env bash
# S5 — Koruma sağlığı (rapor §8.2, ~30 sn): TVOC-2 simülatöründe sensör durum biti (PDU 222) 0 yapılır.
# Beklenen: "Pano korumasız: X2:4 dedektörü arızalı" — operasyonu anlama kanıtı.
source "$(dirname "${BASH_SOURCE[0]}")/_ortak.sh"

renk_baslik "S5 — Koruma sağlığı kaybı"
yigin_kontrol

if ! panoalgo_var_mi; then
  senaryo_engelli_uyarisi "S5" "Koruma sağlığı" "$FRONTEND_BASE/pano/GDZ-00231"
  echo "  (Örnek veri modunda GDZ-00231/Bornova DM-3 zaten bu senaryoyu canlandırır: P1, X2:4 arızalı.)"
  exit 2
fi

PANO_ID="${1:-SIM-00005}"
renk_ok "Senaryo oynatılıyor: $PANO_ID, S5_prot_health, hız x60"
python3 -m sim.panosim --scenario S5_prot_health --detector X2:4 --pano "$PANO_ID" --speed 60 --duration 30 --mqtt "${GRIDUP_MQTT:-localhost:1883}"

echo
echo "İzleyin: $FRONTEND_BASE/pano/$PANO_ID → 'Ark koruması dedektör arızası, pano sessizce korumasız' (P1)"
