#!/usr/bin/env bash
# Yerel sertifika otoritesi ve mTLS tezgahinin sertifikalari (F-27, Kisi B).
#
#   bash scripts/sertifika-uret.sh                      # ADM-00001..3 + merkez
#   bash scripts/sertifika-uret.sh ADM-00001 ADM-00002  # yalnizca sayilan panolar
#   GRIDUP_CERT_DAYS=30 bash scripts/sertifika-uret.sh  # gecerlilik suresini kisalt
#
# Cikis kodu: 0 hepsi uretildi, 1 uretilemedi / dogrulanamadi.
#
# NEDEN YEREL CA: PLAN.md GK4 yigini internet kablosu cikarilmis halde calistirmayi
# sart kosar. Dis bir sertifika otoritesi (Let's Encrypt, kurumsal PKI) bu kurali
# dogrudan ihlal ederdi. CA burada uretilir, burada kalir ve atilabilir.
#
# BUNUN KANITLAMADIGI SEY — docs/15 §5.1'de de aynen yazili:
#   * "Cihaz kimligi dogrulanir" DEMEK DEGILDIR. CA, sertifikalar ve ozel anahtarlar
#     ayni betikle ayni makinede uretilir; deploy/certs/ dizinini okuyabilen herkes
#     gecerli bir pano sertifikasi basabilir. Broker'in dogruladigi sey kimlik degil,
#     BIZIM URETTIGIMIZ BIR ADDIR.
#   * Anahtarlar dosya sisteminde duz durur. Guvenli eleman / HSM YOKTUR; donanima
#     bagli cihaz kimligi (IDevID/LDevID) F-28'in konusudur ve kod yazilmamistir.
#   * Yenileme, rotasyon ve iptal (CRL/OCSP) YOKTUR. Sizan bir anahtarin degerini
#     sifirlamanin yolu bu betigi yeniden kosturmaktir — uc panoluk bir tezgahta
#     calisir, 100+ modulde calismaz.
#
# DOSYA IZINLERI: bilerek 0644 birakildi, `chmod 600` YAPILMIYOR. Iki olculmus sebep:
#   (a) Git Bash / NTFS'te `chmod 600` sessiz bir no-op'tur (core.fileMode=false);
#       koymak yanlis guven verir.
#   (b) Linux host'ta 0600 + kullanici sahipligi YIGINI KIRAR: eclipse-mosquitto
#       konteyneri uid 1883'e duser ve bind-mount'lanmis anahtari OKUYAMAZ.
#   Koruma dosya izni degil, dizin + git kuralidir (deploy/certs/.gitignore).

set -uo pipefail

# Git Bash `-subj "/CN=..."` argumanini bir Windows yoluna cevirir ve CN sessizce
# bozulur; CN bozulursa use_identity_as_username + ACL %u zinciri komple coker.
# Linux'ta zararsizdir.
#
# DIKKAT: bu degisken yol donusumunu KOMPLE kapatir, yani openssl'e POSIX bir mutlak
# yol ("/c/Users/...") verilirse openssl onu acamaz. Bu yuzden asagida butun openssl
# cagrilari deploy/certs icine `cd` edilmis halde GORELI yollarla yapilir; boylece
# ayni betik Git Bash'te de Linux'ta da ayni sekilde calisir.
export MSYS_NO_PATHCONV=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERT_DIR="$REPO_ROOT/deploy/certs"
DAYS="${GRIDUP_CERT_DAYS:-825}"
# Broker sertifikasinin SAN'i: konteyner adi (compose agi), localhost ve 127.0.0.1.
# Olcum betigi host'tan 127.0.0.1'e baglanir; SAN'da IP yoksa paho el sikismayi
# "IP address mismatch" ile reddeder (olculdu).
BROKER_SAN="DNS:mosquitto-mtls,DNS:localhost,IP:127.0.0.1"
BACKEND_CN="gridup-backend"
DEFAULT_PANOS=(ADM-00001 ADM-00002 ADM-00003)

hata() { printf '\033[1;31mHATA\033[0m %s\n' "$1" >&2; exit 1; }
bilgi() { printf '  \033[1;32m+\033[0m %s\n' "$1"; }
baslik() { printf '\n\033[1;34m== %s ==\033[0m\n' "$1"; }

command -v openssl >/dev/null 2>&1 || hata \
  "openssl bulunamadi. Windows'ta Git Bash ile gelir (/mingw64/bin/openssl).
       Broker imajinda openssl YOKTUR, sertifika konteynerde uretilemez."

# S5: eksik bir dosya yolunu Docker DIZIN olarak yaratir; sonra openssl uzerine
# yazamaz ve mTLS kipi elle silinmeden onarilamaz. Once bunu yakala.
for bozuk in ca.crt ca.key; do
  [ -d "$CERT_DIR/$bozuk" ] && hata "deploy/certs/$bozuk bir DIZIN (Docker yaratmis). Silin: rm -rf deploy/certs/$bozuk"
done

PANOS=("$@")
[ ${#PANOS[@]} -eq 0 ] && PANOS=("${DEFAULT_PANOS[@]}")

# CN'i kaliba zorla. Bozuk bir CN (bosluk, '/', '+', '#') ACL kalibinda ya hic
# eslesmez (her sey reddedilir) ya da joker uretip FAZLA yetki verir; iki durumda da
# "A, B'ye yazamiyor" gozlemi dogru cikar ama sebebi tasarladigimiz kural olmaz.
for pano in "${PANOS[@]}"; do
  [[ "$pano" =~ ^[A-Z]{3}-[0-9]{5}$ ]] || hata "gecersiz pano kimligi: '$pano' (beklenen bicim ABC-00001)"
done

mkdir -p "$CERT_DIR/broker" "$CERT_DIR/backend" "$CERT_DIR/pano" || hata "$CERT_DIR olusturulamadi"
[ -f "$CERT_DIR/.gitignore" ] || hata "deploy/certs/.gitignore YOK — koruma kalkmis, once onu geri koyun (git checkout deploy/certs/.gitignore)"

# MSYS_NO_PATHCONV yuzunden openssl'e mutlak yol verilemez: buradan sonrasi goreli.
cd "$CERT_DIR" || hata "$CERT_DIR'a girilemedi"

# CN'i uretilen sertifikadan GERI OKUYUP dogrular. Sessiz bozulmayi burada yakalariz.
cn_dogrula() {  # $1 sertifika yolu, $2 beklenen CN
  local okunan
  okunan="$(openssl x509 -in "$1" -noout -subject 2>/dev/null | sed -n 's/.*CN *= *\([^,]*\).*/\1/p' | tr -d '[:space:]')"
  [ "$okunan" = "$2" ] || hata "CN bozuldu: $1 icinde '$okunan', beklenen '$2' (MSYS yol donusumu?)"
}

# Istemci sertifikasi uretir: CSR -> yerel CA imzasi -> CN dogrulamasi.
# Var olan ve zinciri dogrulanan sertifika YENIDEN URETILMEZ: kanit dosyasindaki
# parmak izleri betik her kosuldugunda degisseydi olcum tekrar edilemez olurdu.
# Yenilemek icin: GRIDUP_CERT_YENILE=1 bash scripts/sertifika-uret.sh
istemci_uret() {  # $1 hedef dizin, $2 CN
  local dizin="$1" cn="$2"
  mkdir -p "$dizin"
  if [ "${GRIDUP_CERT_YENILE:-0}" != "1" ] && [ -f "$dizin/$cn.crt" ] && [ -f "$dizin/$cn.key" ] \
     && openssl verify -CAfile "ca.crt" "$dizin/$cn.crt" >/dev/null 2>&1; then
    cn_dogrula "$dizin/$cn.crt" "$cn"
    return 0
  fi
  openssl req -newkey rsa:2048 -nodes -keyout "$dizin/$cn.key" -out "$dizin/$cn.csr" \
    -subj "/O=Grid Up/OU=Pano Beyni/CN=$cn" >/dev/null 2>&1 || hata "$cn CSR uretilemedi"
  printf 'extendedKeyUsage=clientAuth\nkeyUsage=digitalSignature,keyEncipherment\nbasicConstraints=CA:FALSE\n' > "$dizin/$cn.ext"
  openssl x509 -req -in "$dizin/$cn.csr" -CA "ca.crt" -CAkey "ca.key" \
    -CAcreateserial -out "$dizin/$cn.crt" -days "$DAYS" -sha256 -extfile "$dizin/$cn.ext" >/dev/null 2>&1 \
    || hata "$cn sertifikasi imzalanamadi"
  rm -f "$dizin/$cn.csr" "$dizin/$cn.ext"
  cn_dogrula "$dizin/$cn.crt" "$cn"
}

baslik "Yerel sertifika otoritesi"
# GRIDUP_CERT_YENILE=1 CA'YI DA YENILER. Ilk yazimda yalnizca yaprak sertifikalari
# yeniliyordu ve bu, yukaridaki "sizan bir anahtarin degerini sifirlamanin yolu bu betigi
# yeniden kosturmaktir" cumlesini GECERSIZ kiliyordu: sizan ca.key gecerli kalirdi ve
# sizdiran taraf istedigi CN icin (merkez dahil) sertifika basmaya devam ederdi.
if [ "${GRIDUP_CERT_YENILE:-0}" = "1" ]; then
  rm -f "ca.crt" "ca.key" "ca.srl"
  bilgi "GRIDUP_CERT_YENILE=1: yerel CA ve butun sertifikalar sifirdan uretiliyor"
fi
if [ -f "ca.crt" ] && [ -f "ca.key" ]; then
  cn_dogrula "ca.crt" "gridup-yerel-ca"
  bilgi "var olan CA kullaniliyor ($(openssl x509 -in "ca.crt" -noout -enddate | cut -d= -f2))"
else
  openssl req -x509 -newkey rsa:3072 -sha256 -days "$DAYS" -nodes \
    -keyout "ca.key" -out "ca.crt" \
    -subj "/O=Grid Up/CN=gridup-yerel-ca" >/dev/null 2>&1 || hata "CA uretilemedi"
  cn_dogrula "ca.crt" "gridup-yerel-ca"
  bilgi "yeni CA uretildi: gridup-yerel-ca ($DAYS gun)"
fi

baslik "Broker sunucu sertifikasi"
# Broker konteynerine YALNIZCA bu dizin baglanir: ca.crt kopyasi + kendi cifti.
# Butun panolarin ozel anahtarini broker'a vermek sizintinin yaricapini buyuturdu.
cp "ca.crt" "broker/ca.crt"
if [ "${GRIDUP_CERT_YENILE:-0}" != "1" ] && [ -f "broker/broker.crt" ] && [ -f "broker/broker.key" ] \
   && openssl verify -CAfile "ca.crt" "broker/broker.crt" >/dev/null 2>&1; then
  cn_dogrula "broker/broker.crt" "mosquitto-mtls"
else
  openssl req -newkey rsa:2048 -nodes -keyout "broker/broker.key" -out "broker/broker.csr" \
    -subj "/O=Grid Up/CN=mosquitto-mtls" >/dev/null 2>&1 || hata "broker CSR uretilemedi"
  printf 'subjectAltName=%s\nextendedKeyUsage=serverAuth\nbasicConstraints=CA:FALSE\n' "$BROKER_SAN" > "broker/broker.ext"
  openssl x509 -req -in "broker/broker.csr" -CA "ca.crt" -CAkey "ca.key" \
    -CAcreateserial -out "broker/broker.crt" -days "$DAYS" -sha256 -extfile "broker/broker.ext" >/dev/null 2>&1 \
    || hata "broker sertifikasi imzalanamadi"
  rm -f "broker/broker.csr" "broker/broker.ext"
  cn_dogrula "broker/broker.crt" "mosquitto-mtls"
fi
bilgi "mosquitto-mtls  SAN: $BROKER_SAN"

baslik "Merkez istemci sertifikasi"
istemci_uret "backend" "$BACKEND_CN"
# Broker'daki ile ayni mantik: konteynere YALNIZCA bu dizin baglanir, bu yuzden CA
# kopyasi da icine konur. Boylece backend pano ozel anahtarlarini HIC gormez.
cp "ca.crt" "backend/ca.crt"
bilgi "$BACKEND_CN (deploy/mosquitto.acl icinde adiyla yazili)"

baslik "Pano sertifikalari"
for pano in "${PANOS[@]}"; do
  istemci_uret "pano/$pano" "$pano"
  bilgi "$pano"
done

baslik "Dogrulama"
kaldi=0
for crt in "broker/broker.crt" "backend/$BACKEND_CN.crt"; do
  openssl verify -CAfile "ca.crt" "$crt" >/dev/null 2>&1 \
    && bilgi "zincir dogrulandi: $(basename "$crt")" || { printf '  \033[1;31m-\033[0m zincir DOGRULANAMADI: %s\n' "$crt"; kaldi=$((kaldi+1)); }
done
for pano in "${PANOS[@]}"; do
  openssl verify -CAfile "ca.crt" "pano/$pano/$pano.crt" >/dev/null 2>&1 \
    && bilgi "zincir dogrulandi: $pano" || { printf '  \033[1;31m-\033[0m zincir DOGRULANAMADI: %s\n' "$pano"; kaldi=$((kaldi+1)); }
done

# GK9 kapisi: uretilen materyal gercekten git disinda mi? Bir gun .gitignore bozulursa
# betik burada durur, sertifikalar sessizce commit'lenmez.
# Yollar GORELI: MSYS_NO_PATHCONV acikken git'e mutlak bir POSIX yol verilirse
# ("/c/Users/...") git onu depo disinda sanir. cd deploy/certs yapildigi icin goreli
# yol dogru cozulur ve ayni satir Linux'ta da calisir.
for yol in "ca.key" "ca.crt" "ca.srl" "broker/broker.key" "pano/${PANOS[0]}/${PANOS[0]}.crt"; do
  git check-ignore -q "$yol" 2>/dev/null \
    || { printf '  \033[1;31m-\033[0m GIT DISINDA DEGIL: deploy/certs/%s\n' "$yol"; kaldi=$((kaldi+1)); }
done
[ "$kaldi" -eq 0 ] && bilgi "uretilen materyalin tamami git disinda (GK9)"

baslik "Parmak izleri (kanit dosyasina bunlar yazilir, PEM govdesi ASLA)"
for crt in "ca.crt" "broker/broker.crt" "backend/$BACKEND_CN.crt"; do
  printf '  %-16s %s\n' "$(openssl x509 -in "$crt" -noout -subject | sed -n 's/.*CN *= *//p')" \
    "$(openssl x509 -in "$crt" -noout -fingerprint -sha256 | cut -d= -f2)"
done
for pano in "${PANOS[@]}"; do
  printf '  %-16s %s\n' "$pano" "$(openssl x509 -in "pano/$pano/$pano.crt" -noout -fingerprint -sha256 | cut -d= -f2)"
done

if [ "$kaldi" -ne 0 ]; then
  printf '\n\033[1;31m%d dogrulama kaldi.\033[0m\n' "$kaldi"
  exit 1
fi
# Broker sertifikayi ACILISTA okur: yenilenen bir sertifika ancak yeniden baslatmayla
# devreye girer. Bu uyari olmadan olcum "KARARSIZ" doner ve sebebi sahada aranir.
if docker inspect -f '{{.State.Running}}' gridup-mosquitto-mtls 2>/dev/null | grep -q true; then
  printf '\n\033[1;33m UYARI\033[0m mosquitto-mtls CALISIYOR ve sertifikayi acilista okur.\n'
  printf '       Yenilenen sertifikalarin devreye girmesi icin yeniden baslatin:\n'
  printf '         docker compose -f deploy/compose.yaml --profile mtls restart mosquitto-mtls\n'
fi

printf '\n\033[1m Hazir. Tezgahi kaldirmak icin:\033[0m\n'
printf '   docker compose -f deploy/compose.yaml --profile mtls up -d mosquitto-mtls\n'
printf '   backend/.venv/Scripts/python scripts/mtls_yetki_testi.py\n'
