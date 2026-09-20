#!/usr/bin/env bash
# demo/senaryo/*.sh betiklerinin ortak yardımcıları.
# Sahip: Kişi C. Bu dosya tek başına çalıştırılmaz; `source _ortak.sh` ile kullanılır.
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$DEMO_DIR/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deploy/compose.yaml"
API_BASE="${GRIDUP_API:-http://localhost:8000}"
FRONTEND_BASE="${GRIDUP_FRONTEND:-http://localhost:3000}"
MQTT_TARGET="${GRIDUP_MQTT:-localhost:1883}"

renk_baslik() { printf '\n\033[1;34m== %s ==\033[0m\n' "$1"; }
renk_ok()     { printf '\033[1;32m✓ %s\033[0m\n' "$1"; }
renk_uyari()  { printf '\033[1;33m! %s\033[0m\n' "$1"; }
renk_hata()   { printf '\033[1;31m✗ %s\033[0m\n' "$1"; }

# Yığının ayakta olup olmadığını kontrol eder; değilse net bir mesajla çıkar (sessizce başarısız olmaz).
yigin_kontrol() {
  if ! curl -fsS "$API_BASE/health" >/dev/null 2>&1; then
    renk_hata "Backend $API_BASE/health yanıt vermiyor. Önce şunu çalıştırın:"
    echo "  docker compose -f '$COMPOSE_FILE' up -d --build"
    exit 1
  fi
  renk_ok "Backend ayakta ($API_BASE)"
}

# ---------------------------------------------------------------- Python bulma
#
# Ekibin üçü de Windows'ta. Orada `python3` çoğu zaman Microsoft Store kısayoludur:
# vardır, çalıştırılır, hiçbir şey yapmadan çıkar. Bu yüzden "komut var mı" değil
# "gerçekten Python mu" diye bakıyoruz (Y7).
PYTHON=""
python_bul() {
  [ -n "$PYTHON" ] && return 0
  local aday
  for aday in "${GRIDUP_PYTHON:-}" python3 python py; do
    [ -z "$aday" ] && continue
    if [ "$aday" = "py" ]; then
      if command -v py >/dev/null 2>&1 && py -3 -c "import sys" >/dev/null 2>&1; then
        PYTHON="py -3"; return 0
      fi
    elif command -v "$aday" >/dev/null 2>&1 && "$aday" -c "import sys" >/dev/null 2>&1; then
      PYTHON="$aday"; return 0
    fi
  done
  return 1
}

# panoalgo repoda yaşıyor; kurulum ZORUNLU DEĞİL, yola eklemek yeterli.
export PYTHONPATH="$REPO_ROOT/libs/panoalgo${PYTHONPATH:+:$PYTHONPATH}"

# Senaryo oynatma bu makinede host Python'ıyla mümkün mü?
host_senaryo_hazir_mi() {
  python_bul || return 1
  # shellcheck disable=SC2086  # PYTHON "py -3" olabilir, bölünmesi gerekiyor
  $PYTHON -c "import paho.mqtt.client, yaml, jsonschema, panoalgo.scenarios" >/dev/null 2>&1 || return 1
  # shellcheck disable=SC2086
  $PYTHON "$REPO_ROOT/sim/panosim.py" --help 2>/dev/null | grep -q -- "--scenario"
}

# Host uygun değilse aynı senaryo, yığının kendi imajında koşturulabilir.
docker_senaryo_hazir_mi() {
  command -v docker >/dev/null 2>&1 && docker compose -f "$COMPOSE_FILE" ps panosim >/dev/null 2>&1
}

senaryo_engelli_uyarisi() {
  local kod="$1" ad="$2" rota="$3"
  renk_uyari "$kod ($ad) bu makinede oynatılamıyor: ne host Python'ı ne de Docker hazır."
  echo "  Gerekenlerden biri:"
  echo "    a) Host Python 3.12+: pip install -r '$REPO_ROOT/sim/requirements.txt'"
  echo "       (panoalgo'yu kurmanıza gerek yok, betik PYTHONPATH ile ekliyor)"
  echo "    b) Docker: docker compose -f '$COMPOSE_FILE' up -d --build"
  echo "  Alternatif — örnek veriyle aynı senaryoyu gözleyin:"
  echo "    cd frontend && npm run dev:mock   # sonra $rota adresine gidin"
}

# senaryo_oynat S1_loose_conn SIM-00001 90 --point DSYA3_L2
#   $1 senaryo kimliği · $2 pano · $3 duvar saati süresi (sn) · kalanlar ek bayraklar
senaryo_oynat() {
  local senaryo="$1" pano="$2" sure="$3"; shift 3
  if host_senaryo_hazir_mi; then
    renk_ok "Senaryo oynatılıyor (host Python): $pano, $senaryo, ${sure} sn"
    # shellcheck disable=SC2086
    $PYTHON "$REPO_ROOT/sim/panosim.py" \
      --scenario "$senaryo" --pano "$pano" --duration "$sure" \
      --mqtt "$MQTT_TARGET" "$@"
  elif docker_senaryo_hazir_mi; then
    renk_ok "Senaryo oynatılıyor (docker): $pano, $senaryo, ${sure} sn"
    docker compose -f "$COMPOSE_FILE" run --rm --no-deps panosim \
      python panosim.py \
      --scenario "$senaryo" --pano "$pano" --duration "$sure" \
      --mqtt "mosquitto:1883" "$@"
  else
    return 2
  fi
}

# backend_alarm_dokumu SIM-00004
#
# panosim yalnizca KENDI kenar tespitini sayar ve senaryo biter bitmez "beklenenlerden
# 0/1 gorundu" yazabilir. Oysa backend'in alarm tiki (ALARM_TICK_S, varsayilan 5 sn)
# senaryonun BITISINDEN SONRA calisir. 20 Eylul'de S4'te olculdu: panosim 0/1 dedi,
# backend ALM-ARC-TRIP'i 20 saniye sonra yukseltti ve Telegram'a dustu. Jurinin
# ekraninda bu iki satir arasinda kalmamak icin gercegi backend'e soruyoruz.
backend_alarm_dokumu() {
  local pano="$1" bekle="${GRIDUP_TIK_BEKLE:-25}"
  echo
  renk_ok "Backend alarm tiki bekleniyor (${bekle} sn) — panosim'in sayimi kenar tarafidir"
  sleep "$bekle"

  local json
  if ! json="$(curl -fsS "$API_BASE/api/v1/alarms?pano_id=$pano" 2>/dev/null)"; then
    renk_uyari "Alarm ucu okunamadi; arayuzden bakin: $FRONTEND_BASE/alarmlar"
    return 0
  fi

  if ! python_bul; then
    renk_uyari "Python yok, ham yanit: $json"
    return 0
  fi

  # shellcheck disable=SC2086
  printf '%s' "$json" | $PYTHON -c '
import json, sys
alarms = json.load(sys.stdin)
if not alarms:
    print("  Backend bu pano icin alarm yukseltmedi.")
    raise SystemExit
print(f"  Backend {len(alarms)} alarm yukseltti:")
for a in alarms:
    kanal = a.get("notified") or "-"
    if isinstance(kanal, (list, tuple)):
        kanal = ", ".join(str(k) for k in kanal) or "-"
    prio = str(a.get("prio", "?"))
    code = str(a.get("code", "?"))
    state = str(a.get("state", "?"))
    print(f"    {prio:4} {code:20} {state:8} bildirim: {kanal}")
'
}
