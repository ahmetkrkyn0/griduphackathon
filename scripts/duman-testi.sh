#!/usr/bin/env bash
# Duman testi — yigin ayaga kalktiktan sonra "gercekten calisiyor mu" denetimi.
#
# Sahip: Kisi B (CODEOWNERS /scripts/). PLAN.md T4.4'un tekrarlanabilir hali:
# temiz makine testi her seferinde elle tiklanmasin diye betige donusturuldu.
#
# Kullanim (repo kokunden, yigin ayaktayken):
#   docker compose -f deploy/compose.yaml up -d --build
#   bash scripts/duman-testi.sh
#
# Tam temiz makine testi icin once volume'lari da silin:
#   docker compose -f deploy/compose.yaml down -v
#
# Cikis kodu: 0 = hepsi gecti, 1 = en az bir kontrol kaldi.
set -uo pipefail

COMPOSE="${GRIDUP_COMPOSE:-deploy/compose.yaml}"
API="${GRIDUP_API:-http://localhost:8000}"
FRONTEND="${GRIDUP_FRONTEND:-http://localhost:3000}"
GRAFANA="${GRIDUP_GRAFANA:-http://localhost:3001}"
PY="${GRIDUP_PYTHON:-python}"

gecti=0
kaldi=0
kontrol() {
  local ad="$1"; shift
  if "$@" >/dev/null 2>&1; then
    printf '  \033[1;32m✓\033[0m %s\n' "$ad"; gecti=$((gecti + 1))
  else
    printf '  \033[1;31m✗\033[0m %s\n' "$ad"; kaldi=$((kaldi + 1))
  fi
}

baslik() { printf '\n\033[1;34m== %s ==\033[0m\n' "$1"; }

# Ham Modbus TCP FC03 istegi; cevap gelirse 0, gelmezse 1 doner.
modbus_okur() {  # $1 port, $2 birim, $3 register
  "$PY" - "$1" "$2" "$3" <<'PYEOF'
import socket, struct, sys
port, unit, reg = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
frame = struct.pack(">HHHBBHH", 1, 0, 6, unit, 3, reg, 1)
with socket.create_connection(("localhost", port), timeout=5) as s:
    s.settimeout(5)
    s.sendall(frame)
    try:
        answer = s.recv(256)
    except socket.timeout:
        answer = b""
sys.exit(0 if len(answer) > 9 and answer[7] == 0x03 else 1)
PYEOF
}

# "Cevap YOK" denetimi: sessiz olmasi gerekene sorar, sessizse 0 doner.
modbus_sessiz() {  # $1 port, $2 birim, $3 register
  "$PY" - "$1" "$2" "$3" <<'PYEOF'
import socket, struct, sys
port, unit, reg = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
frame = struct.pack(">HHHBBHH", 1, 0, 6, unit, 3, reg, 1)
with socket.create_connection(("localhost", port), timeout=5) as s:
    s.settimeout(4)
    s.sendall(frame)
    try:
        answer = s.recv(256)
    except socket.timeout:
        answer = b""
# Bos = sessiz (dogru). Istisna cevabi (0x83) da BASARISIZLIKTIR: kilavuz 1.3
# "cevap vermez" der, "hata doner" demez — bkz. sim/tests/test_tvoc2_server.py.
sys.exit(0 if not answer else 1)
PYEOF
}

port_acik() { "$PY" -c "import socket,sys; socket.create_connection(('localhost',int(sys.argv[1])),timeout=5).close()" "$1"; }

# K3: yayinlanan telemetri zaman damgasi duvar saatiyle hizali mi?
# Eski davranista (SIM_SPEED=60 + simule ts) 11 dakikalik bir kosuda damgalar duvar
# saatinin 10,5 saat ONUNE geciyordu ve arayuzun `to = new Date()` pencereli grafikleri
# yeni veriyi HIC gormuyordu. NOT: pano DETAY ucu `last_seen` degil `ts` doner.
# DIKKAT: burada heredoc KULLANILAMAZ. Borudan gelen JSON ile heredoc ayni stdin'i
# ister; heredoc kazanir ve json.load betigin kendisini okumaya calisir. -c ile veriyoruz.
ts_duvar_saatinde() {
  curl -fsS "$API/api/v1/panels/ADM-00001" | "$PY" -c '
import json, sys
from datetime import datetime, timedelta, timezone
stamp = json.load(sys.stdin).get("ts")
if not stamp:
    sys.exit(1)
sapma = abs(datetime.fromisoformat(stamp) - datetime.now(timezone.utc))
sys.exit(0 if sapma <= timedelta(minutes=5) else 1)
'
}

baslik "Servisler"
for servis in timescaledb mosquitto backend frontend grafana panosim mpr-sim tvoc-sim gsm-modem; do
  kontrol "$servis calisiyor" \
    bash -c "docker compose -f '$COMPOSE' ps '$servis' --format '{{.State}}' | grep -q running"
done

baslik "Uc noktalar"
kontrol "backend /health ok"       bash -c "curl -fsS '$API/health' | grep -q '\"ok\":[[:space:]]*true'"
kontrol "API dokumani acik"        curl -fsS "$API/docs"
kontrol "frontend nginx yanit"     curl -fsS "$FRONTEND/"
kontrol "grafana yanit"            curl -fsS "$GRAFANA/api/health"
kontrol "Modbus TCP :502 dinliyor" port_acik 502
kontrol "IEC 104 :2404 dinliyor"   port_acik 2404
kontrol "MPR-53CS sim :5020"       port_acik 5020
kontrol "TVOC-2 sim :5021"         port_acik 5021

baslik "Veri akisi"
kontrol "ingest: reddedilen 0, dusen 0, yazilan > 0" \
  bash -c "curl -fsS '$API/health' | $PY -c \"import json,sys; h=json.load(sys.stdin)['ingest']; sys.exit(0 if h['rejected']==0 and h['dropped']==0 and h['written']>0 else 1)\""
kontrol "en az 3 pano API'de gorunuyor" \
  bash -c "curl -fsS '$API/api/v1/panels' | $PY -c \"import json,sys; d=json.load(sys.stdin); r=d if isinstance(d,list) else d.get('items',[]); sys.exit(0 if len(r)>=3 else 1)\""
kontrol "kenar alanlari (k_ratio) pano detayina ulasiyor" \
  bash -c "curl -fsS '$API/api/v1/panels/ADM-00001' | grep -q k_ratio"
kontrol "zaman damgasi duvar saatinde (K3: gelecege kacmiyor)" ts_duvar_saatinde

baslik "Kulvar kanitlari"
kontrol "merkez dedektor etkin (TB2 Adim 4)" \
  bash -c "docker compose -f '$COMPOSE' logs backend | grep -q 'merkez dedektor etkin'"
kontrol "TVOC-2 fabrika ID 248 SESSIZ (istisna bile donmez)" modbus_sessiz 5021 248 1300
kontrol "MPR-53CS CT register'i okunuyor (0x8001)"           modbus_okur 5020 1 32769

printf '\n\033[1m SONUC: %d gecti, %d kaldi\033[0m\n' "$gecti" "$kaldi"
[ "$kaldi" -eq 0 ] || exit 1
