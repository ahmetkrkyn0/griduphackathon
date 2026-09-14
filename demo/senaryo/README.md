# demo/senaryo/ — Belirlenimli demo betikleri (T5.1)

**Sahip:** Kişi C. Rapor §8.2'deki S0–S8 akışının komut satırı karşılığı.

| Betik | Senaryo | Durum |
|---|---|---|
| `s0.sh` | Normal gün | ⏳ A'nın simülatörünü bekliyor |
| `s1.sh` | Gevşek bağlantı | ⏳ A'nın simülatörünü bekliyor |
| `s2.sh` | Aşırı yük | ⏳ A'nın simülatörünü bekliyor |
| `s3.sh` | Yoğuşma | ⏳ A'nın simülatörünü bekliyor |
| `s4.sh` | Ark olayı | ⏳ A'nın simülatörünü bekliyor |
| `s5.sh` | Koruma sağlığı | ⏳ A'nın simülatörünü bekliyor |
| `s6.sh` | Haberleşme kopması | ⏳ A'nın simülatörünü bekliyor |
| `s7.sh` | Ölçek (1.000 pano) | ✅ **Çalışır** (`loadtest/fleet.py` mevcut) |
| `s8.sh` | Entegrasyon (SCADA) | ✅ **Çalışır** (bilgilendirme + doğrulama komutu) |

## Dürüstlük notu

`s0`–`s6` betikleri PLAN.md TA1/TA2'nin tanımladığı arayüze göre yazıldı
(`python -m sim.panosim --scenario ...`), ama bu depoda **A'nın sentetik veri üreteci
(`libs/panoalgo/`) ve `sim/panosim.py` henüz yok** — bu yazının yazıldığı anda `sim/` dizininde
yalnızca bir yer tutucu (`hello_publisher.py`) var. Bu betikler çalıştırıldığında bunu sessizce
geçmez; net bir uyarı basıp örnek-veri modunda aynı senaryoyu nasıl gözlemleyeceğinizi söyler
(`frontend`'de her senaryonun karşılığı zaten hazır bir pano olarak var — bkz. `frontend/src/api/mock.ts`).

A'nın simülatörü tamamlanınca yalnızca `--scenario` bayrağının gerçek adını (varsa) `_ortak.sh`
veya betiklerin kendisinde güncellemek yeterli olmalı; komut satırı arayüzü PLAN.md'deki TA1
örneğiyle (`python -m sim.panosim --panels 3 --speed 60 --mqtt mosquitto:1883`) tutarlı tutuldu.

## Kullanım

```bash
# Yığın ayaktayken:
docker compose -f deploy/compose.yaml up -d --build

# Herhangi bir senaryo:
./demo/senaryo/s1.sh                # varsayılan pano kimliğiyle
./demo/senaryo/s1.sh ADM-00099       # belirli bir pano kimliğiyle

# Ölçek ve entegrasyon (bugün çalışır):
./demo/senaryo/s7.sh 1000 60
./demo/senaryo/s8.sh
```

Ortam değişkenleri: `GRIDUP_API`, `GRIDUP_FRONTEND`, `GRIDUP_MQTT`, `GRIDUP_MODBUS_HOST`,
`GRIDUP_MODBUS_PORT`, `GRIDUP_IEC104_PORT` — varsayılanlar `deploy/compose.yaml` ile uyumludur.

## Doğrulama durumu

Bu betikler bu geliştirme ortamında **gerçek Docker yığınına karşı çalıştırılıp doğrulanmadı**
(ortamda Docker yoktu). Sözdizimi `bash -n` ile kontrol edildi. Ekip, yığın ayaktayken en az bir
kez her betiği çalıştırıp gerçek zamanlamaları (rapor §8.2'deki saniyeler) teyit etmelidir
(`STATUS.md` §7).
