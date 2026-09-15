# demo/senaryo/ — Belirlenimli demo betikleri (T5.1)

**Sahip:** Kişi C. Rapor §8.2'deki S0–S8 akışının komut satırı karşılığı.

| Betik | Senaryo | Süre (varsayılan) | Durum |
|---|---|---|---|
| `s0.sh` | Normal gün | 60 sn | ✅ Çalışır |
| `s1.sh` | Gevşek bağlantı | 90 sn | ✅ Çalışır |
| `s2.sh` | Aşırı yük | 45 sn | ✅ Çalışır |
| `s3.sh` | Yoğuşma | 60 sn | ✅ Çalışır |
| `s4.sh` | Ark olayı | 60 sn | ✅ Çalışır |
| `s5.sh` | Koruma sağlığı | 30 sn | ✅ Çalışır |
| `s6.sh` | Haberleşme kopması | 45 sn | ✅ Çalışır (uyarısıyla, aşağıda) |
| `s7.sh` | Ölçek (1.000 pano) | 60 sn | ✅ Çalışır (`loadtest/fleet.py`) |
| `s8.sh` | Entegrasyon (SCADA) | — | ✅ Çalışır (bilgilendirme + doğrulama komutu) |

## Oynatılan veri gerçekten nedir?

`s0`–`s6`, `sim/panosim.py --scenario` ile **etiketli arıza senaryolarını canlı oynatır**.
Oynatılan fizik, `data/fixtures/` altındaki CSV'leri ve `docs/12` doğrulama tablosunu üreten
fiziğin **birebir aynısıdır**: ikisi de `panoalgo.scenarios.iter_samples()` yürütücüsünü
kullanır (`sim/tests/test_panosim_scenario.py` bunu ölçer). Yani "demoda başka, raporda başka"
olması mümkün değildir.

Yürütücü fiziği 15 dakikalık adımlarla koşturur ve bunların yalnızca bir kısmını yayınlar —
gerçek kenarın "1 s işle, 10 s'de bir özet gönder" davranışının aynısı. Seyreltme oranı
`--duration`'a göre seçilir; betik başlarken kaç mesaj yayınlayacağını ekrana yazar.

**Zaman damgası:** yayınlanan `ts` **duvar saatidir** (K3 kararı, `docs/14` §7). Fizik
hızlandırılmış kalır — 90 saniyede 720 simüle saat akar — ama zaman damgaları geleceğe
kaçmaz, dolayısıyla arayüzün trend grafikleri veriyi görür.

## Kullanım

```bash
# Yığın ayaktayken:
docker compose -f deploy/compose.yaml up -d --build

# Herhangi bir senaryo:
./demo/senaryo/s1.sh                     # varsayılanlar: SIM-00001, 90 sn
./demo/senaryo/s1.sh ADM-00099 120       # belirli pano ve süre
./demo/senaryo/s5.sh SIM-00005 30 X3:2   # S5 ayrıca dedektör adı alır

# Ölçek ve entegrasyon:
./demo/senaryo/s7.sh 1000 60
./demo/senaryo/s8.sh
```

### Gereksinimler ve otomatik geri dönüş

Betikler senaryoyu **önce host Python'ıyla** çalıştırmayı dener, olmazsa **yığının kendi
imajında** (`docker compose run --rm panosim`) çalıştırır. İkisi de yoksa ne olduğunu ve
nasıl düzelteceğinizi açıkça yazar (sessizce geçmez).

Host Python için gereken tek şey:

```bash
pip install -r sim/requirements.txt
```

`panoalgo`'yu ayrıca **kurmanız gerekmez** — `_ortak.sh` `libs/panoalgo`'yu `PYTHONPATH`'e ekler.

Windows'ta `python3` çoğu zaman Microsoft Store kısayoludur: vardır, çalışır, hiçbir şey
yapmaz. Betikler bu yüzden "komut var mı" değil "gerçekten Python mu" diye bakar ve
`python3 → python → py -3` sırasını dener. Elle göstermek için:
`GRIDUP_PYTHON=/c/Python312/python.exe ./demo/senaryo/s1.sh`

Ortam değişkenleri: `GRIDUP_API`, `GRIDUP_FRONTEND`, `GRIDUP_MQTT`, `GRIDUP_MODBUS_HOST`,
`GRIDUP_MODBUS_PORT`, `GRIDUP_IEC104_PORT`, `GRIDUP_PYTHON` — varsayılanlar
`deploy/compose.yaml` ile uyumludur.

## İki dürüstlük notu

**S0 "sıfır alarm" demek değildir.** S0 yanlış alarm **tabanıdır**: `docs/12` §3'e göre
100 pano/gün başına 71,4 alarm (sözleşme sınırı 150), ağırlıklı olarak çiy noktası uyarıları.
Canlı demoda da çiy alarmı görebilirsiniz; bu bir hata değil, ölçülmüş ve sınır içinde
kalan gürültü tabanıdır.

**S6'da alarmı merkez üretir.** `ALM-COMMS-LOST` kenarda basılmaz; backend'in heartbeat
denetimi üretir (`heartbeat_timeout_min`, sözleşme). 45 saniyelik oynatmadaki boşluk o eşiği
aşmaz. Alarmı canlı görmek için `s6.sh`'nin yazdırdığı `docker compose stop panosim` /
`start panosim` adımlarını kullanın. Boşluk süresince **sahte değer üretilmez** — hiçbir
mesaj yayınlanmaz.
