#!/usr/bin/env bash
# DIN kutusunun STL'ini uretir. Sahip: Kisi C.
#
# NEDEN BETIK: STL bu teslimde URETILMEDI cunku gelistirme ortaminda OpenSCAD kurulu
# degil (docs/17 §6, sapma 3). Kaynak (.scad) parametrik ve tamdir; OpenSCAD kurulu
# herhangi bir makinede asagidaki tek komut yeterlidir. Betik, o komutu ve dogrulamayi
# bir arada tutar ki "STL nasil uretilir" sorusu sunum aninda aranmasin.
#
# Kurulum:
#   Windows : winget install OpenSCAD.OpenSCAD
#   macOS   : brew install --cask openscad
#   Linux   : sudo apt install openscad
#
# Kullanim: bash hardware/mekanik/uret-stl.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KAYNAK="$DIR/din-kutu.scad"
CIKTI="${1:-$DIR/din-kutu.stl}"

OPENSCAD="${OPENSCAD:-openscad}"
if ! command -v "$OPENSCAD" >/dev/null 2>&1; then
  for aday in \
    "/c/Program Files/OpenSCAD/openscad.exe" \
    "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"; do
    [ -x "$aday" ] && OPENSCAD="$aday" && break
  done
fi

if ! command -v "$OPENSCAD" >/dev/null 2>&1 && [ ! -x "$OPENSCAD" ]; then
  echo "OpenSCAD bulunamadi. Kurulum icin bu dosyanin basindaki nota bakin," >&2
  echo "ya da yolu elle verin: OPENSCAD=/yol/openscad bash $0" >&2
  exit 127
fi

echo "OpenSCAD: $OPENSCAD"
"$OPENSCAD" -o "$CIKTI" "$KAYNAK"

# Dogrulama: bos ya da bozuk bir STL sessizce gecmesin.
if [ ! -s "$CIKTI" ]; then
  echo "STL uretilemedi ya da bos: $CIKTI" >&2
  exit 1
fi
boyut=$(wc -c < "$CIKTI")
echo "Uretildi: $CIKTI ($((boyut / 1024)) KB)"
echo "Kontrol: bir dilimleyicide (PrusaSlicer/Cura) acip DIN ray klipsi ve J1-J10"
echo "         klemens kesiklerinin io-tablosu.md ile ortustugunu dogrulayin."
