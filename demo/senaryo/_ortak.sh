#!/usr/bin/env bash
# demo/senaryo/*.sh betiklerinin ortak yardımcıları.
# Sahip: Kişi C. Bu dosya tek başına çalıştırılmaz; `source _ortak.sh` ile kullanılır.
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$DEMO_DIR/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deploy/compose.yaml"
API_BASE="${GRIDUP_API:-http://localhost:8000}"
FRONTEND_BASE="${GRIDUP_FRONTEND:-http://localhost:3000}"

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

# A'nın sentetik veri üreteci/senaryo modülünün bu depoda henüz var olup olmadığını kontrol eder.
# PLAN.md TA1/TA2 tamamlanmadan bu betikler senaryo OYNATAMAZ; bunu sessizce geçmek yerine
# açıkça söyler (STATUS.md karar #6 — dürüstlük kuralı, sessiz başarısızlık yok).
panoalgo_var_mi() {
  [ -f "$REPO_ROOT/sim/panosim.py" ] && [ -d "$REPO_ROOT/libs/panoalgo/panoalgo" ]
}

senaryo_engelli_uyarisi() {
  local kod="$1" ad="$2" rota="$3"
  renk_uyari "$kod ($ad) oynatılamıyor: sim/panosim.py ve libs/panoalgo/ (Kişi A, TA1/TA2) bu depoda henüz yok."
  echo "  Bu betik PLAN.md'de tanımlanan arayüze göre yazıldı ve A'nın simülatörü eklenince"
  echo "  çalışır hale gelecek (bkz. STATUS.md §6 madde 6). Şimdilik alternatif:"
  echo "  frontend'i örnek veriyle açıp aynı senaryoyu gözlemleyin:"
  echo "    cd frontend && npm run dev:mock   # sonra $rota adresine gidin"
}
