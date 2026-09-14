#!/usr/bin/env bash
# S7 — Ölçek (rapor §8.2, ~45 sn izleme): 1.000 sanal pano yük testi.
# GERÇEK ve ÇALIŞIR: loadtest/fleet.py (Kişi B) zaten mevcut ve bu depoda test edilmiş (docs/09).
source "$(dirname "${BASH_SOURCE[0]}")/_ortak.sh"

renk_baslik "S7 — Ölçek (1.000 sanal pano)"
yigin_kontrol

PANELS="${1:-1000}"
DURATION="${2:-60}"

renk_ok "loadtest/fleet.py başlatılıyor: $PANELS pano, $DURATION sn"
python3 "$REPO_ROOT/loadtest/fleet.py" --panels "$PANELS" --duration "$DURATION"

echo
echo "İzleyin: Grafana http://localhost:3001 → 'Ölçek' panosu (mesaj/s, CPU, RAM, p95, DB boyutu)"
echo "         Grafana 'Alarm KPI' panosu (alarm/100 pano/gün, öncelik dağılımı)"
echo "Temizlik: python3 loadtest/fleet.py --cleanup-only   (SIM-* verisini siler)"
