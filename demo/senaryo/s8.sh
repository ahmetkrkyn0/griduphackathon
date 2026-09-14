#!/usr/bin/env bash
# S8 — Entegrasyon (rapor §8.2, ~30 sn): Modbus/IEC 104 istemcisinden bizim haritamız okunur.
# GERÇEK ve ÇALIŞIR: backend/app/scada/ (Kişi B) zaten mevcut. Bu betik istemci komutu ÇALIŞTIRMAZ
# (QModMaster/IEC 104 test istemcisi grafik arayüzlü, harici araçlardır); adımları ve bir
# komut satırı doğrulama örneğini yazdırır.
source "$(dirname "${BASH_SOURCE[0]}")/_ortak.sh"

renk_baslik "S8 — Entegrasyon (SCADA)"
yigin_kontrol

python_bul || PYTHON="python3"   # yalnızca yazdırılan örnek komut için

MODBUS_HOST="${GRIDUP_MODBUS_HOST:-localhost}"
MODBUS_PORT="${GRIDUP_MODBUS_PORT:-502}"
IEC104_PORT="${GRIDUP_IEC104_PORT:-2404}"

cat <<EOF

1) Modbus TCP (harita: contracts/modbus-map.yaml, doküman: docs/03-modbus-haritasi.md)
   QModMaster / Modbus Poll ile bağlanın: $MODBUS_HOST:$MODBUS_PORT
   Hızlı doğrulama (pymodbus kurulu bir Python ile):
     $PYTHON -c "
from pymodbus.client import ModbusTcpClient
c = ModbusTcpClient('$MODBUS_HOST', port=$MODBUS_PORT)
c.connect()
r = c.read_holding_registers(100, count=4, slave=1)  # conn_temp bloğu, ADM-00014
print('conn_temp[0:4] =', r.registers)
c.close()
"

2) IEC 60870-5-104 (harita: docs/04-iec104-haritasi.md, Could seviyesi)
   Bir IEC 104 test istemcisiyle $MODBUS_HOST:$IEC104_PORT adresine bağlanın, genel sorgulama
   (C_IC_NA_1) gönderin; noktaların Modbus haritasıyla birebir eşleştiğini gözlemleyin
   (ortak adres = birim, IOA = 1000 + PDU).

3) Arayüzle çapraz kontrol: $FRONTEND_BASE/pano/ADM-00014 → aynı anda gösterilen değerlerin
   Modbus/IEC 104 istemcisinde okunanla aynı olduğunu gösterin ("RTU'nuz bunu yarın okuyabilir").
EOF
