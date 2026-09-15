#!/usr/bin/env bash
# S2 — Aşırı yük (rapor §8.2, ~45 sn): üç fazda akım artırılır, tüm fazlar birlikte ısınır.
# Beklenen: "Aşırı yük — arıza değil" hipotezi, K normal kalır (HYP-OVERLOAD, yanlış alarm önleme).
source "$(dirname "${BASH_SOURCE[0]}")/_ortak.sh"

renk_baslik "S2 — Aşırı yük"
yigin_kontrol

PANO_ID="${1:-SIM-00002}"
SURE="${2:-45}"

if ! senaryo_oynat "S2_overload" "$PANO_ID" "$SURE"; then
  senaryo_engelli_uyarisi "S2" "Aşırı yük" "$FRONTEND_BASE/pano/GDZ-00088"
  echo "  (Örnek veri modunda GDZ-00088/Yunusemre TM-21 zaten bu senaryoyu canlandırır.)"
  exit 2
fi

echo
echo "İzleyin: $FRONTEND_BASE/pano/$PANO_ID → 'Aşırı yük, arıza değil' önerisi görünmeli, K/K₀ normalde kalmalı"
echo "Vurgu: ALM-I-OVER çıkar ama ALM-K-ALM ÇIKMAZ. Etiketin not_expect alanı tam olarak bunu ölçer."
