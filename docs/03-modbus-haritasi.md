# 03 — Pano Beyni Modbus Haritası ve SCADA Ağ Geçidi

> **Sahip:** Kişi B · **Tek kaynak:** `contracts/modbus-map.yaml` (v1, donmuş).
> §3–§7, §8'deki komut tablosu, §9 ve §12 o dosyadan ve ağ geçidi kodundan **üretilir**
> (`python scripts/gen_modbus_doc.py`); elle düzenlenmez (PLAN.md kural 10). Excel için aynı register tablosu:
> `docs/03-modbus-haritasi.csv` (`;` ayraçlı, UTF-8).
> **Kod:** `backend/app/scada/` — `map_loader.py` (harita), `encoder.py` (değer kodlama), `modbus_tcp.py` (Modbus TCP sunucusu),
> `gateway.py` (birim eşlemesi, yazma politikası), `service.py` (yaşam döngüsü).

## 1. Amaç: SCADA tek bir cihaz okusun

Trafo merkezindeki RTU veya dağıtım SCADA'sı bugün MPR-53CS analizörünü ve TVOC-2 ark korumasını **ayrı ayrı** okur (ya da hiç
okumaz). Pano Beyni bu iki cihazın değerlerini kendi sensörleri, risk skoru ve alarm bitleriyle **tek bir haritada** birleştirir:
RTU'ya yeni bir cihaz tanıtmak yerine tek bir Modbus cihazı eklenir (rapor §6.4b).

Aynı harita iki yerde, aynı adreslerle sunulur:

| Nerede | Protokol | Kim sunar | Ne zaman kullanılır |
|---|---|---|---|
| Panoda (kenar) | Modbus RTU slave, RS485 | Pano Beyni firmware'i (`firmware/core/modbus_map.c`, Kişi A) | RTU panonun yanındaysa |
| Merkezde | **Modbus TCP**, port 502 | Ağ geçidi (`backend/app/scada/`, bu doküman) | SCADA ön-uç sunucusu merkezdeyse; hücresel hatla gelen tüm panolar |

SCADA hangi yoldan bağlanırsa bağlansın `conn_temp.GIRIS_L2` hep **PDU 101**'dedir. Merkezde her pano bir Modbus **birimidir**
(unit id 1–247); bir birimin içindeki harita, panodaki haritanın birebir aynısıdır.

## 2. Tek master kısıtı: sahada üç bağlantı senaryosu

Modbus RTU hattında yalnızca bir master olabilir. Mevcut hatta nasıl girildiği, kurulum öncesi keşifte belirlenir (rapor §6.4a, §7.1):

| Senaryo | Sahadaki durum | Çözüm |
|---|---|---|
| A — Yeni kurulum | MPR-53CS / TVOC-2'yi sorgulayan başka master yok | Pano Beyni **master** olur; RTU'ya kendi slave portundan bu haritayı sunar |
| B — RTU zaten master | Mevcut sorgu bozulmamalı | Pano Beyni hatta yalnızca **dinleyici** olur veya RTU'nun ikinci portuna slave eklenir |
| C — İkinci port yok | Dinleme istenmiyor | Hat Pano Beyni üzerinden geçirilir (şeffaf ağ geçidi: RTU → slave port → master port → cihazlar) |

Merkezdeki Modbus TCP ağ geçidi bu kısıttan bağımsızdır: veriyi hücresel hatla gelen telemetriden sunar, sahadaki RS485 hattına dokunmaz.

## 3. Özet (üretilmiş)

<!-- URETILMIS:ozet -->
| Alan | Deger |
|---|---|
| Harita surumu | 1 |
| Bayt sirasi | big |
| 32 bit deger word sirasi | high_first |
| FC03 / FC04 aynasi | evet |
| Blok / tanimli register / coil | 13 / 150 / 6 |
| Izleme noktasi (conn_temp, conn_dt, k_index ayni sira) | 25 |
| Birim (unit id) | 1-247, her birim bir pano |
<!-- /URETILMIS:ozet -->

## 4. Bloklar (üretilmiş)

Adresler **PDU adresidir (0 tabanlı)**. "4xxxx" gösterimi Modicon numarasıdır: holding register = 40001 + PDU,
input register = 30001 + PDU. İstemciniz 1 tabanlı adres istiyorsa PDU'ya 1 ekleyin.

<!-- URETILMIS:bloklar -->
| Blok | PDU adresi | Holding (FC03) | Adet | Erisim | Kaynak cihaz | Not |
|---|---|---|---|---|---|---|
| `device_info` | 0-19 | 40001-40020 | 20 | read | - | - |
| `health` | 20-39 | 40021-40040 | 20 | read | - | - |
| `conn_temp` | 100-149 | 40101-40150 | 50 | read | - | nokta sirasi asagidaki points listesidir; conn_dt ve k_index ayni sirayi kullanir |
| `conn_dt` | 150-199 | 40151-40200 | 50 | read | - | ortam uzeri sicaklik artisi — L0 limitleri bunun uzerinden (IEC 61439-1) |
| `k_index` | 200-299 | 40201-40300 | 100 | read | - | K/K0 * 100; ornek 160 => 1600 register degeri => K/K0 = 1.6 |
| `environment` | 300-319 | 40301-40320 | 20 | read | - | - |
| `electrical_mirror` | 400-449 | 40401-40450 | 50 | read | MPR-53CS | mevcut enerji analizorunden okunup aynalanir; I_primer = ham * 0.001 * CT (CT=500) |
| `arc_mirror` | 500-519 | 40501-40520 | 20 | read_only | ABB TVOC-2 | src_pdu = TVOC-2 Modbus kilavuzundaki PDU adresi (register no = PDU + 1) |
| `pd` | 600-619 | 40601-40620 | 20 | read | - | OG eklentisi; AG panoda 65535/0 |
| `risk` | 700-719 | 40701-40720 | 20 | read | - | - |
| `alarms` | 800-829 | 40801-40830 | 30 | read | - | bit haritasi alarm-codes.yaml bitmap bolumunde |
| `event` | 830-849 | 40831-40850 | 20 | read | - | - |
| `command` | 900-909 | 40901-40910 | 10 | write | - | yazma yalnizca bu blokta; TVOC-2 aynasina yazma ag gecidinde FILTRELENIR (GK6) |
<!-- /URETILMIS:bloklar -->

## 5. Değer kodlama kuralları (üretilmiş)

<!-- URETILMIS:kodlama -->
| Kural | Deger |
|---|---|
| Olcek | ham = fiziksel / `scale`, yarim yukari yuvarlanir (4,35 x 10 -> 44) |
| Negatif int16 | ikiye tumleyen uint16 (-2,5 K x 10 = -25 -> 65511) |
| Aralik disi olcum | DOYAR: int16 +-32767, uint16 0-65534 (sarmaz) |
| Sayac ve bit alani | 16 bit sarar (heartbeat, trip sayaci, olay sayaci) |
| 'Yok' int16 | 0x8000 (32768) |
| 'Yok' uint16 | 0xFFFF (65535); sozlesme notu farkliysa not kazanir (voc_idx, pd blogu) |
| Tanimsiz (yedek) register | 0 |
| 32 bit deger | iki register, `word_order` = high_first (event.ts_hi / ts_lo) |
| Canli alarm biti | durum active / acked ve kosul suruyor; rafa alinmis alarm duyurulmaz |
| Mandalli alarm biti | canli + onaysiz + saklanan mandal; `reset_latch` komutuyla silinir |
| Haberlesme | son veri `heartbeat_timeout_min` icindeyse `comms_ok` = 1; aksi halde son degerler sunulur |
<!-- /URETILMIS:kodlama -->

"Yok" değeri bir **dürüstlük** kararıdır: kenarın merkeze göndermediği bir alan (ör. TVOC-2 son trip tarihi) SCADA'ya 0 olarak
gitseydi "1 Ocak 1970'te trip olmuş" diye okunurdu. Aynı nedenle alarm durumu henüz yüklenmemiş bir panonun alarm bitleri
0 okunmaz, istek 0x0B ile reddedilir (§9).

## 6. Register tablosu (üretilmiş)

"Merkez kaynağı" sütunu, merkezdeki ağ geçidinin o register'ı nereden doldurduğunu gösterir; kaynak tablosu
`backend/app/scada/encoder.py` içindedir ve sözleşmeye kaynağı tanımsız bir register eklenirse ağ geçidi hiç başlamaz.

<!-- URETILMIS:registerler -->
| PDU | 4xxxx | 3xxxx | Ad | Tip | Olcek | Birim | Erisim | TVOC-2 PDU | Merkez kaynagi | Not |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 40001 | 30001 | `device_info.map_version` | uint16 | - | - | read | - | modbus-map.yaml `version` | bu dosyanin version alani |
| 1 | 40002 | 30002 | `device_info.fw_version` | uint16 | - | - | read | - | `fw` 'M.m.p' -> 0xMmpp | ornek: 0x0301 = v0.3.1 |
| 2 | 40003 | 30003 | `device_info.serial_hi` | uint16 | - | - | read | - | - (kenar merkeze gondermiyor; hep 'yok') | - |
| 3 | 40004 | 30004 | `device_info.serial_lo` | uint16 | - | - | read | - | - (kenar merkeze gondermiyor; hep 'yok') | - |
| 4 | 40005 | 30005 | `device_info.pano_type` | uint16 | - | - | read | - | `panels.pano_type` (1600kVA-dahili = 1, bilinmeyen = 0) | 1 = 1600 kVA dahili (EK-II/14) |
| 5 | 40006 | 30006 | `device_info.point_count` | uint16 | - | - | read | - | `t_conn` nokta sayisi | aktif baglanti noktasi sayisi |
| 20 | 40021 | 30021 | `health.uptime_h` | uint16 | - | - | read | - | `health.uptime_s` / 3600 | - |
| 21 | 40022 | 30022 | `health.last_sync_m` | uint16 | - | - | read | - | merkezin panodan son veri aldigi andan beri gecen dakika | son zaman senkronundan beri dakika |
| 22 | 40023 | 30023 | `health.supply_state` | uint16 | - | - | read | - | canli ALM-LASTGASP -> 2; aksi halde 'yok' | 0=sebeke, 1=yedek, 2=son nefes |
| 23 | 40024 | 30024 | `health.backup_pct` | uint16 | - | - | read | - | `health.vbak_pct` | - |
| 24 | 40025 | 30025 | `health.rssi_dbm_neg` | uint16 | - | - | read | - | -`health.rssi_dbm` | pozitif olarak: 87 => -87 dBm |
| 25 | 40026 | 30026 | `health.nodes_ok` | uint16 | - | - | read | - | `health.nodes_ok` | - |
| 26 | 40027 | 30027 | `health.nodes_total` | uint16 | - | - | read | - | `health.nodes_total` | - |
| 27 | 40028 | 30028 | `health.heartbeat` | uint16 | - | - | read | - | `seq` (16 bit sarar; donarsa kenar sessiz) | her cevrimde artar; donarsa kenar oldu |
| 28 | 40029 | 30029 | `health.buffered_msgs` | uint16 | - | - | read | - | `health.buffered` | - |
| 29 | 40030 | 30030 | `health.baseline_day` | uint16 | - | - | read | - | `health.baseline_day` | 7 = taban ogrenme tamam |
| 100 | 40101 | 30101 | `conn_temp.GIRIS_L1` | int16 | 0.1 | degC | read | - | `t_conn[GIRIS_L1].t_c` | - |
| 101 | 40102 | 30102 | `conn_temp.GIRIS_L2` | int16 | 0.1 | degC | read | - | `t_conn[GIRIS_L2].t_c` | - |
| 102 | 40103 | 30103 | `conn_temp.GIRIS_L3` | int16 | 0.1 | degC | read | - | `t_conn[GIRIS_L3].t_c` | - |
| 103 | 40104 | 30104 | `conn_temp.GIRIS_N` | int16 | 0.1 | degC | read | - | `t_conn[GIRIS_N].t_c` | - |
| 104 | 40105 | 30105 | `conn_temp.DSYA1_L1` | int16 | 0.1 | degC | read | - | `t_conn[DSYA1_L1].t_c` | - |
| 105 | 40106 | 30106 | `conn_temp.DSYA1_L2` | int16 | 0.1 | degC | read | - | `t_conn[DSYA1_L2].t_c` | - |
| 106 | 40107 | 30107 | `conn_temp.DSYA1_L3` | int16 | 0.1 | degC | read | - | `t_conn[DSYA1_L3].t_c` | - |
| 107 | 40108 | 30108 | `conn_temp.DSYA2_L1` | int16 | 0.1 | degC | read | - | `t_conn[DSYA2_L1].t_c` | - |
| 108 | 40109 | 30109 | `conn_temp.DSYA2_L2` | int16 | 0.1 | degC | read | - | `t_conn[DSYA2_L2].t_c` | - |
| 109 | 40110 | 30110 | `conn_temp.DSYA2_L3` | int16 | 0.1 | degC | read | - | `t_conn[DSYA2_L3].t_c` | - |
| 110 | 40111 | 30111 | `conn_temp.DSYA3_L1` | int16 | 0.1 | degC | read | - | `t_conn[DSYA3_L1].t_c` | - |
| 111 | 40112 | 30112 | `conn_temp.DSYA3_L2` | int16 | 0.1 | degC | read | - | `t_conn[DSYA3_L2].t_c` | - |
| 112 | 40113 | 30113 | `conn_temp.DSYA3_L3` | int16 | 0.1 | degC | read | - | `t_conn[DSYA3_L3].t_c` | - |
| 113 | 40114 | 30114 | `conn_temp.DSYA4_L1` | int16 | 0.1 | degC | read | - | `t_conn[DSYA4_L1].t_c` | - |
| 114 | 40115 | 30115 | `conn_temp.DSYA4_L2` | int16 | 0.1 | degC | read | - | `t_conn[DSYA4_L2].t_c` | - |
| 115 | 40116 | 30116 | `conn_temp.DSYA4_L3` | int16 | 0.1 | degC | read | - | `t_conn[DSYA4_L3].t_c` | - |
| 116 | 40117 | 30117 | `conn_temp.DSYA5_L1` | int16 | 0.1 | degC | read | - | `t_conn[DSYA5_L1].t_c` | - |
| 117 | 40118 | 30118 | `conn_temp.DSYA5_L2` | int16 | 0.1 | degC | read | - | `t_conn[DSYA5_L2].t_c` | - |
| 118 | 40119 | 30119 | `conn_temp.DSYA5_L3` | int16 | 0.1 | degC | read | - | `t_conn[DSYA5_L3].t_c` | - |
| 119 | 40120 | 30120 | `conn_temp.DSYA6_L1` | int16 | 0.1 | degC | read | - | `t_conn[DSYA6_L1].t_c` | - |
| 120 | 40121 | 30121 | `conn_temp.DSYA6_L2` | int16 | 0.1 | degC | read | - | `t_conn[DSYA6_L2].t_c` | - |
| 121 | 40122 | 30122 | `conn_temp.DSYA6_L3` | int16 | 0.1 | degC | read | - | `t_conn[DSYA6_L3].t_c` | - |
| 122 | 40123 | 30123 | `conn_temp.DSYA7_L1` | int16 | 0.1 | degC | read | - | `t_conn[DSYA7_L1].t_c` | - |
| 123 | 40124 | 30124 | `conn_temp.DSYA7_L2` | int16 | 0.1 | degC | read | - | `t_conn[DSYA7_L2].t_c` | - |
| 124 | 40125 | 30125 | `conn_temp.DSYA7_L3` | int16 | 0.1 | degC | read | - | `t_conn[DSYA7_L3].t_c` | - |
| 150 | 40151 | 30151 | `conn_dt.GIRIS_L1` | int16 | 0.1 | K | read | - | `t_conn[GIRIS_L1].dt_c` | - |
| 151 | 40152 | 30152 | `conn_dt.GIRIS_L2` | int16 | 0.1 | K | read | - | `t_conn[GIRIS_L2].dt_c` | - |
| 152 | 40153 | 30153 | `conn_dt.GIRIS_L3` | int16 | 0.1 | K | read | - | `t_conn[GIRIS_L3].dt_c` | - |
| 153 | 40154 | 30154 | `conn_dt.GIRIS_N` | int16 | 0.1 | K | read | - | `t_conn[GIRIS_N].dt_c` | - |
| 154 | 40155 | 30155 | `conn_dt.DSYA1_L1` | int16 | 0.1 | K | read | - | `t_conn[DSYA1_L1].dt_c` | - |
| 155 | 40156 | 30156 | `conn_dt.DSYA1_L2` | int16 | 0.1 | K | read | - | `t_conn[DSYA1_L2].dt_c` | - |
| 156 | 40157 | 30157 | `conn_dt.DSYA1_L3` | int16 | 0.1 | K | read | - | `t_conn[DSYA1_L3].dt_c` | - |
| 157 | 40158 | 30158 | `conn_dt.DSYA2_L1` | int16 | 0.1 | K | read | - | `t_conn[DSYA2_L1].dt_c` | - |
| 158 | 40159 | 30159 | `conn_dt.DSYA2_L2` | int16 | 0.1 | K | read | - | `t_conn[DSYA2_L2].dt_c` | - |
| 159 | 40160 | 30160 | `conn_dt.DSYA2_L3` | int16 | 0.1 | K | read | - | `t_conn[DSYA2_L3].dt_c` | - |
| 160 | 40161 | 30161 | `conn_dt.DSYA3_L1` | int16 | 0.1 | K | read | - | `t_conn[DSYA3_L1].dt_c` | - |
| 161 | 40162 | 30162 | `conn_dt.DSYA3_L2` | int16 | 0.1 | K | read | - | `t_conn[DSYA3_L2].dt_c` | - |
| 162 | 40163 | 30163 | `conn_dt.DSYA3_L3` | int16 | 0.1 | K | read | - | `t_conn[DSYA3_L3].dt_c` | - |
| 163 | 40164 | 30164 | `conn_dt.DSYA4_L1` | int16 | 0.1 | K | read | - | `t_conn[DSYA4_L1].dt_c` | - |
| 164 | 40165 | 30165 | `conn_dt.DSYA4_L2` | int16 | 0.1 | K | read | - | `t_conn[DSYA4_L2].dt_c` | - |
| 165 | 40166 | 30166 | `conn_dt.DSYA4_L3` | int16 | 0.1 | K | read | - | `t_conn[DSYA4_L3].dt_c` | - |
| 166 | 40167 | 30167 | `conn_dt.DSYA5_L1` | int16 | 0.1 | K | read | - | `t_conn[DSYA5_L1].dt_c` | - |
| 167 | 40168 | 30168 | `conn_dt.DSYA5_L2` | int16 | 0.1 | K | read | - | `t_conn[DSYA5_L2].dt_c` | - |
| 168 | 40169 | 30169 | `conn_dt.DSYA5_L3` | int16 | 0.1 | K | read | - | `t_conn[DSYA5_L3].dt_c` | - |
| 169 | 40170 | 30170 | `conn_dt.DSYA6_L1` | int16 | 0.1 | K | read | - | `t_conn[DSYA6_L1].dt_c` | - |
| 170 | 40171 | 30171 | `conn_dt.DSYA6_L2` | int16 | 0.1 | K | read | - | `t_conn[DSYA6_L2].dt_c` | - |
| 171 | 40172 | 30172 | `conn_dt.DSYA6_L3` | int16 | 0.1 | K | read | - | `t_conn[DSYA6_L3].dt_c` | - |
| 172 | 40173 | 30173 | `conn_dt.DSYA7_L1` | int16 | 0.1 | K | read | - | `t_conn[DSYA7_L1].dt_c` | - |
| 173 | 40174 | 30174 | `conn_dt.DSYA7_L2` | int16 | 0.1 | K | read | - | `t_conn[DSYA7_L2].dt_c` | - |
| 174 | 40175 | 30175 | `conn_dt.DSYA7_L3` | int16 | 0.1 | K | read | - | `t_conn[DSYA7_L3].dt_c` | - |
| 200 | 40201 | 30201 | `k_index.GIRIS_L1` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[GIRIS_L1].k_ratio` x 100 | - |
| 201 | 40202 | 30202 | `k_index.GIRIS_L2` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[GIRIS_L2].k_ratio` x 100 | - |
| 202 | 40203 | 30203 | `k_index.GIRIS_L3` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[GIRIS_L3].k_ratio` x 100 | - |
| 203 | 40204 | 30204 | `k_index.GIRIS_N` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[GIRIS_N].k_ratio` x 100 | - |
| 204 | 40205 | 30205 | `k_index.DSYA1_L1` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA1_L1].k_ratio` x 100 | - |
| 205 | 40206 | 30206 | `k_index.DSYA1_L2` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA1_L2].k_ratio` x 100 | - |
| 206 | 40207 | 30207 | `k_index.DSYA1_L3` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA1_L3].k_ratio` x 100 | - |
| 207 | 40208 | 30208 | `k_index.DSYA2_L1` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA2_L1].k_ratio` x 100 | - |
| 208 | 40209 | 30209 | `k_index.DSYA2_L2` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA2_L2].k_ratio` x 100 | - |
| 209 | 40210 | 30210 | `k_index.DSYA2_L3` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA2_L3].k_ratio` x 100 | - |
| 210 | 40211 | 30211 | `k_index.DSYA3_L1` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA3_L1].k_ratio` x 100 | - |
| 211 | 40212 | 30212 | `k_index.DSYA3_L2` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA3_L2].k_ratio` x 100 | - |
| 212 | 40213 | 30213 | `k_index.DSYA3_L3` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA3_L3].k_ratio` x 100 | - |
| 213 | 40214 | 30214 | `k_index.DSYA4_L1` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA4_L1].k_ratio` x 100 | - |
| 214 | 40215 | 30215 | `k_index.DSYA4_L2` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA4_L2].k_ratio` x 100 | - |
| 215 | 40216 | 30216 | `k_index.DSYA4_L3` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA4_L3].k_ratio` x 100 | - |
| 216 | 40217 | 30217 | `k_index.DSYA5_L1` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA5_L1].k_ratio` x 100 | - |
| 217 | 40218 | 30218 | `k_index.DSYA5_L2` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA5_L2].k_ratio` x 100 | - |
| 218 | 40219 | 30219 | `k_index.DSYA5_L3` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA5_L3].k_ratio` x 100 | - |
| 219 | 40220 | 30220 | `k_index.DSYA6_L1` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA6_L1].k_ratio` x 100 | - |
| 220 | 40221 | 30221 | `k_index.DSYA6_L2` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA6_L2].k_ratio` x 100 | - |
| 221 | 40222 | 30222 | `k_index.DSYA6_L3` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA6_L3].k_ratio` x 100 | - |
| 222 | 40223 | 30223 | `k_index.DSYA7_L1` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA7_L1].k_ratio` x 100 | - |
| 223 | 40224 | 30224 | `k_index.DSYA7_L2` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA7_L2].k_ratio` x 100 | - |
| 224 | 40225 | 30225 | `k_index.DSYA7_L3` | int16 | 0.1 | percent_of_baseline | read | - | `t_conn[DSYA7_L3].k_ratio` x 100 | - |
| 300 | 40301 | 30301 | `environment.t_low_c` | int16 | 0.1 | degC | read | - | `env.t_low_c` | - |
| 301 | 40302 | 30302 | `environment.rh_low_pct` | int16 | 0.1 | percent | read | - | `env.rh_low_pct` | - |
| 302 | 40303 | 30303 | `environment.td_low_c` | int16 | 0.1 | degC | read | - | `env.td_low_c` | ciy noktasi (Magnus) |
| 303 | 40304 | 30304 | `environment.td_margin_k` | int16 | 0.1 | K | read | - | `env.td_margin_k` | negatif = yogusma |
| 304 | 40305 | 30305 | `environment.t_up_c` | int16 | 0.1 | degC | read | - | `env.t_up_c` | - |
| 305 | 40306 | 30306 | `environment.rh_up_pct` | int16 | 0.1 | percent | read | - | `env.rh_up_pct` | - |
| 306 | 40307 | 30307 | `environment.dt_air_k` | int16 | 0.1 | K | read | - | `env.dt_air_k` | ust - alt: pano enerji dengesi |
| 307 | 40308 | 30308 | `environment.voc_idx` | int16 | 0.1 | index | read | - | `env.voc_idx` | 65535 = sensor yok |
| 400 | 40401 | 30401 | `electrical_mirror.i_l1_a` | uint16 | 0.1 | - | read | - | `elec.i_ph[0]` | - |
| 401 | 40402 | 30402 | `electrical_mirror.i_l2_a` | uint16 | 0.1 | - | read | - | `elec.i_ph[1]` | - |
| 402 | 40403 | 30403 | `electrical_mirror.i_l3_a` | uint16 | 0.1 | - | read | - | `elec.i_ph[2]` | - |
| 403 | 40404 | 30404 | `electrical_mirror.i_n_a` | uint16 | 0.1 | - | read | - | `elec.i_n` | - |
| 404 | 40405 | 30405 | `electrical_mirror.u_l1_v` | uint16 | 0.1 | - | read | - | `elec.u_ph[0]` | - |
| 405 | 40406 | 30406 | `electrical_mirror.u_l2_v` | uint16 | 0.1 | - | read | - | `elec.u_ph[1]` | - |
| 406 | 40407 | 30407 | `electrical_mirror.u_l3_v` | uint16 | 0.1 | - | read | - | `elec.u_ph[2]` | - |
| 407 | 40408 | 30408 | `electrical_mirror.thd_i_l1_pct` | uint16 | 0.1 | - | read | - | `elec.thd_i[0]` | - |
| 408 | 40409 | 30409 | `electrical_mirror.thd_i_l2_pct` | uint16 | 0.1 | - | read | - | `elec.thd_i[1]` | - |
| 409 | 40410 | 30410 | `electrical_mirror.thd_i_l3_pct` | uint16 | 0.1 | - | read | - | `elec.thd_i[2]` | - |
| 410 | 40411 | 30411 | `electrical_mirror.cosphi` | int16 | 0.001 | - | read | - | `elec.cosphi` | - |
| 411 | 40412 | 30412 | `electrical_mirror.unbal_pct` | uint16 | 0.1 | - | read | - | `elec.unbal_pct` | - |
| 412 | 40413 | 30413 | `electrical_mirror.mpr_comm_ok` | uint16 | - | - | read | - | `elec` geldiyse 1 | 0 = analizor cevap vermiyor |
| 500 | 40501 | 30501 | `arc_mirror.system_state` | uint16 | - | - | read_only | 1300 | `tvoc.state` | - |
| 501 | 40502 | 30502 | `arc_mirror.trip_count` | uint16 | - | - | read_only | 149 | `tvoc.trips` | - |
| 502 | 40503 | 30503 | `arc_mirror.last_det_low` | uint16 | - | - | read_only | 100 | `tvoc.det_bits_low` | - |
| 503 | 40504 | 30504 | `arc_mirror.last_det_high` | uint16 | - | - | read_only | 101 | `tvoc.det_bits_high` | - |
| 504 | 40505 | 30505 | `arc_mirror.last_trip_relay` | uint16 | - | - | read_only | 102 | - (kenar merkeze gondermiyor; hep 'yok') | - |
| 505 | 40506 | 30506 | `arc_mirror.last_trip_date` | uint16 | - | - | read_only | 103 | - (kenar merkeze gondermiyor; hep 'yok') | 1970-01-01 + N gun |
| 506 | 40507 | 30507 | `arc_mirror.last_trip_hhmm` | uint16 | - | - | read_only | 104 | - (kenar merkeze gondermiyor; hep 'yok') | MSB saat, LSB dakika |
| 507 | 40508 | 30508 | `arc_mirror.last_trip_sec` | uint16 | - | - | read_only | 105 | - (kenar merkeze gondermiyor; hep 'yok') | - |
| 508 | 40509 | 30509 | `arc_mirror.sensor_status_x2` | uint16 | - | - | read_only | 222 | `tvoc.sensor_x2` | bit 1 = OK |
| 509 | 40510 | 30510 | `arc_mirror.sensor_status_x3` | uint16 | - | - | read_only | 223 | `tvoc.sensor_x3` | - |
| 510 | 40511 | 30511 | `arc_mirror.amb_light_x2` | uint16 | - | - | read_only | 224 | `tvoc.amb_light_x2` | - |
| 511 | 40512 | 30512 | `arc_mirror.amb_light_x3` | uint16 | - | - | read_only | 225 | `tvoc.amb_light_x3` | - |
| 512 | 40513 | 30513 | `arc_mirror.active_dtc_1` | uint16 | - | - | read_only | 1301 | - (kenar merkeze gondermiyor; hep 'yok') | - |
| 513 | 40514 | 30514 | `arc_mirror.prot_health_ok` | uint16 | - | - | read_only | - | `tvoc.prot_health_ok` (TVOC-2 yoksa 0) | bizim ozet bitimiz; 0 = pano korumasiz |
| 514 | 40515 | 30515 | `arc_mirror.tvoc_comm_ok` | uint16 | - | - | read_only | - | `tvoc.comm_ok` (TVOC-2 yoksa 0) | 0 = cevap yok (or. fabrika ID 248) |
| 600 | 40601 | 30601 | `pd.pulses_per_s` | uint16 | - | - | read | - | `pd.pps` | - |
| 601 | 40602 | 30602 | `pd.amp_dbmv` | int16 | - | - | read | - | `pd.amp_dbmv` | - |
| 602 | 40603 | 30603 | `pd.trend_slope` | int16 | 0.01 | - | read | - | `pd.trend` | - |
| 603 | 40604 | 30604 | `pd.phase_cluster` | uint16 | 0.01 | - | read | - | `pd.phase_cluster` | - |
| 700 | 40701 | 30701 | `risk.risk_score` | uint16 | - | - | read | - | `risk.score` | 0-100 |
| 701 | 40702 | 30702 | `risk.fault_mode` | uint16 | - | - | read | - | `risk.mode` -> hypotheses[].id | alarm-codes.yaml hypotheses[].id |
| 702 | 40703 | 30703 | `risk.ttl_hours` | uint16 | - | - | read | - | `risk.ttl_h` | 65535 = bilinmiyor |
| 703 | 40704 | 30704 | `risk.worst_point` | uint16 | - | - | read | - | en kotu nokta: durum > K/K0 > dT (yalnizca q = 0) | conn_temp points listesindeki indeks |
| 800 | 40801 | 30801 | `alarms.alarm_bits_0_15` | uint16 | - | - | read | - | canli alarmlar (active/acked, kosul suruyor), bit 0-15 | canli; bit 0-15 |
| 801 | 40802 | 30802 | `alarms.alarm_bits_16_31` | uint16 | - | - | read | - | canli alarmlar, bit 16-31 | canli; bit 16-31 |
| 810 | 40811 | 30811 | `alarms.latched_bits_0_15` | uint16 | - | - | read | - | canli \| onaysiz \| mandal (reset_latch'e kadar), bit 0-15 | mandalli kopya |
| 811 | 40812 | 30812 | `alarms.latched_bits_16_31` | uint16 | - | - | read | - | mandalli kopya, bit 16-31 | - |
| 820 | 40821 | 30821 | `alarms.active_alarm_count` | uint16 | - | - | read | - | canli alarm sayisi | - |
| 821 | 40822 | 30822 | `alarms.highest_prio` | uint16 | - | - | read | - | canli alarmlarin en acili (P1>P2>P3>SYS>INFO) | 1=P1, 2=P2, 3=P3, 4=INFO, 5=SYS, 0=yok |
| 830 | 40831 | 30831 | `event.event_count` | uint16 | - | - | read | - | ag gecidinin gordugu alarm acilislari (16 bit sarar) | - |
| 831 | 40832 | 30832 | `event.last_code` | uint16 | - | - | read | - | son acilan alarmin bit numarasi | alarm-codes.yaml bit numarasi |
| 832 | 40833 | 30833 | `event.ts_hi` | uint16 | - | - | read | - | son acilisin olay zamani, Unix s yuksek word | Unix zaman, yuksek word |
| 833 | 40834 | 30834 | `event.ts_lo` | uint16 | - | - | read | - | son acilisin olay zamani, Unix s dusuk word | - |
| 900 | 40901 | 30901 | `command.password` | uint16 | - | - | write | - | okumada her zaman 0 | dogru degilse diger yazmalar yok sayilir |
| 901 | 40902 | 30902 | `command.ack_alarm` | uint16 | - | - | write | - | komut; okumada 0 | - |
| 902 | 40903 | 30903 | `command.reset_latch` | uint16 | - | - | write | - | komut; okumada 0 | - |
| 903 | 40904 | 30904 | `command.maint_mode` | uint16 | - | - | write | - | komut; okumada `health.maint_mode` | 1 = bakim modu; P1 asla bastirilmaz |
| 904 | 40905 | 30905 | `command.test_alarm` | uint16 | - | - | write | - | komut; okumada 0 | sentetik test alarmi tetikler |
<!-- /URETILMIS:registerler -->

## 7. Coil ve discrete input (üretilmiş)

RTU'nun tek bakışta okuduğu özet bitler. FC01 (coil) ve FC02 (discrete input) aynı değerleri döndürür; coil'e yazma desteklenmez.

<!-- URETILMIS:coiller -->
| Adres | Coil (FC01) | Discrete input (FC02) | Ad | Merkez kaynagi | Not |
|---|---|---|---|---|---|
| 0 | 00001 | 10001 | `critical_alarm` | canli P1 alarm var | P1 aktif |
| 1 | 00002 | 10002 | `warning_active` | canli P2 veya P3 alarm var | P2 veya P3 aktif |
| 2 | 00003 | 10003 | `comms_ok` | son veri heartbeat_timeout_min icinde | - |
| 3 | 00004 | 10004 | `maint_mode` | `health.maint_mode` | - |
| 4 | 00005 | 10005 | `prot_health_ok` | `tvoc.prot_health_ok` (TVOC-2 yoksa 0) | ark korumasi sagligi |
| 5 | 00006 | 10006 | `data_quality_ok` | tum noktalarda q = 0 ve canli ALM-DQ-* yok | - |
<!-- /URETILMIS:coiller -->

## 8. Yazma güvenliği ve komut bloğu

Modbus'ın kendisinde kimlik doğrulama yoktur (rapor §7.4). Ağ geçidi bu yüzden **varsayılan olarak salt okunurdur** ve yazmayı
katman katman sınırlar:

1. **Ağ:** yalnızca izinli ağlardan bağlantı kabul edilir (`MODBUS_ALLOWED_CLIENTS`; varsayılan 127/8, 10/8, 172.16/12,
   192.168/16). Sahada SCADA ön-uç sunucusunun adresine daraltılır. Eş zamanlı bağlantı sınırı ve boşta kalan bağlantının
   kapatılması kaynak tüketimini sınırlar.
2. **Yazma kapalı:** `MODBUS_WRITE_PASSWORD` boşsa her yazma 0x01 ile reddedilir.
3. **Yalnızca komut bloğu:** yazma yalnızca `command` bloğunda kabul edilir. **TVOC-2 aynası (500–519) dahil** başka her adrese
   yazma, şifre doğru olsa bile 0x02 ile reddedilir — koruma devresine yazma yok (PLAN.md GK6, FMEA satır 11).
4. **Şifre bağlantıya bağlıdır:** 900'e doğru şifre yazılınca yalnızca **o TCP bağlantısı** sınırlı süre açılır; başka bir
   bağlantı ayrıca şifre yazmak zorundadır. 16 bitlik şifre kaba kuvvete tek başına dayanmadığı için aynı IP'den art arda
   yanlış şifre, o IP'nin yazmasını süreli kilitler (okuma sürer).
5. **Önce doğrula, sonra çalıştır:** bir FC16 isteğindeki tek geçersiz değer tüm isteği reddeder; yarım komut çalışmaz.
6. **Denetim izi:** her onay, alarm yöneticisinin kaydına `SCADA Modbus <istemci IP> (birim N)` olarak; her kenar komutu ve
   reddedilen yazma, backend kaydına istemci IP'siyle düşer.

<!-- URETILMIS:komutlar -->
| PDU | Ad | Yazilabilir deger | Etki |
|---|---|---|---|
| 900 | `password` | 1-65535 | Dogruysa bu TCP baglantisi 60 s acilir (ayni FC16 istegindeki komutlar da calisir). Yanlissa 0x03; ayni IP'den 3 yanlis -> 300 s yazma kilidi. Okumada hep 0. |
| 901 | `ack_alarm` | 0 / 1-32 / 65535 | yok / bit numarasi + 1 olan koddaki alarmlar / panonun tum onaylanabilir alarmlari. Merkez alarm yoneticisinde onaylanir; denetim izine `SCADA Modbus <ip> (birim N)` yazilir. |
| 902 | `reset_latch` | 0 / 1 | yok / mandalli bitleri sil (kosulu suren ve onaysiz alarmlarin biti yine gorunur) |
| 903 | `maint_mode` | 0 / 1 / 2 | yok / bakim modu ac / kapat -> MQTT `cmd` ile KENARA. Okumada kenarin bildirdigi `health.maint_mode`. P1 bakim modunda da bastirilmaz. |
| 904 | `test_alarm` | 0 / 1 | yok / sentetik test alarmi -> MQTT `cmd` ile kenara |
| 905-909 | (yedek) | 0 | baska deger 0x03 |
<!-- /URETILMIS:komutlar -->

Bakım modu **kenarın** durumudur: ağ geçidi komutu MQTT `gridup/pano/{pano_id}/cmd` topic'iyle panoya iletir, yeni durum
panonun bir sonraki telemetrisinde (`health.maint_mode`) geri okunur. MQTT bağlantısı kopuksa komut kuyruğa alınmaz, SCADA'ya
0x0B döner: saatler sonra teslim edilen eski bir "bakım modu aç" komutu sahada sürpriz yaratırdı.

## 9. İstisna kodları (üretilmiş)

İstek doğrulama sırası Modbus Application Protocol v1.1b3 durum diyagramlarını izler: fonksiyon desteklenir mi (0x01) → adet
ve uzunluk (0x03) → adres (0x02) → birim ve veri (0x0A / 0x0B).

<!-- URETILMIS:istisnalar -->
| Kod | Modbus adi | Ag gecidinde ne zaman |
|---|---|---|
| 0x01 | ILLEGAL_FUNCTION | Desteklenmeyen fonksiyon (FC05/15 coil yazma, FC43 vb.); yazma kapali (sifre tanimsiz); baglanti kilidi acilmamis veya suresi dolmus; istemci yanlis sifre kilidinde |
| 0x02 | ILLEGAL_DATA_ADDRESS | Aralik harita bloklarinin disinda veya iki bloga tasiyor; tanimsiz coil; komut blogu disina yazma (TVOC-2 aynasi dahil, GK6) |
| 0x03 | ILLEGAL_DATA_VALUE | Adet siniri (okuma 1-125 register / 1-2000 bit, yazma 1-123), bozuk PDU; yanlis sifre; gecersiz komut degeri |
| 0x04 | SLAVE_DEVICE_FAILURE | Ag gecidinde beklenmeyen hata (kayda duser, baglanti acik kalir) |
| 0x0A | GATEWAY_PATH_UNAVAILABLE | Birim (unit id) bir panoya eslenmemis |
| 0x0B | GATEWAY_TARGET_FAILED | Panonun merkezde verisi yok; alarm durumu henuz yuklenmedi (alarm bitleri 0 okunup 'alarm yok' sanilmasin); komut kenara iletilemedi (MQTT kopuk) |
<!-- /URETILMIS:istisnalar -->

## 10. Birim eşlemesi ve yapılandırma

| Ortam değişkeni (`deploy/.env`) | Varsayılan | Anlamı |
|---|---|---|
| `MODBUS_TCP_PORT` | 502 | Makinede yayınlanan port (konteyner içinde hep 502) |
| `MODBUS_WRITE_PASSWORD` | boş | Boş = salt okunur. 1–65535 |
| `MODBUS_UNITS` | boş | `1=ADM-00001,2=ADM-00002`. Boş = otomatik: pano kimliği sırasıyla ilk 247 pano |
| `MODBUS_ALLOWED_CLIENTS` | özel ağlar | Virgülle CIDR listesi |
| `MODBUS_ENABLED` | 1 | 0 = ağ geçidi kapalı |

**Otomatik eşleme yalnızca demo içindir.** SCADA veritabanı noktaları birim numarasına bağlar; araya yeni bir pano girdiğinde
otomatik numaralar kayar. Sahada `MODBUS_UNITS` zorunludur. Geçersiz eşleme (0 veya 247'den büyük birim, bozuk pano kimliği, aynı
panonun iki kez eşlenmesi) backend'i başlatmaz — yanlış panoyu okutmaktansa hiç yayın yapmamak tercih edilir.

Modbus portu açılamazsa (başka bir süreç kullanıyor) backend **durmaz**: alarm ve bildirim zinciri SCADA aynasından önemlidir.
Durum `GET /health` yanıtındaki `scada` alanında görünür (`listening`, `error`, eşlenen birim, izinli/reddedilen bağlantı sayaçları).

## 11. Jüri demosu: QModMaster ile okuma

1. `docker compose -f deploy/compose.yaml up -d` — ağ geçidi `localhost:502`'de dinler.
2. QModMaster → Modbus TCP, IP `127.0.0.1`, port `502`, Slave Addr **1** (ilk pano).
3. Fonksiyon **03 Read Holding Registers**, başlangıç **100**, adet **25** → bağlantı sıcaklıkları, °C × 10
   (250 = 25,0 °C). Aynı değerler arayüzde pano detayında görünür.
4. Başlangıç **800**, adet 2 → canlı alarm bitleri; **700**, adet 3 → risk skoru, arıza modu, sınıra kalan saat.
5. Fonksiyon **06 Write Single Register**, adres **501** (TVOC-2 trip sayacı) → istisna yanıtı. Varsayılan salt okunur
   yığında 0x01 (yazma kapalı); `MODBUS_WRITE_PASSWORD` tanımlı ve şifre girilmiş olsa bile **0x02**: koruma cihazına yazılamaz.
6. Slave Addr **9** → 0x0A: eşlenmemiş birim.

## 12. RS485 hat bütçesi (üretilmiş)

Pano Beyni'nin kendi RS485 hattındaki sorgu süresi (rapor §6.4d). MPR-53CS (2 blok) ve TVOC-2 (3 blok) okumaları cihaz yanıt
süreleriyle birlikte 1 saniyelik yerel çevrime sığar; merkeze 10 s özet yeterlidir, alarmlar anında gider.

<!-- URETILMIS:hat-butcesi -->
Hat: 19200 baud, 8E1 = 11 bit/karakter; hedef tur suresi 1000 ms.

| FC03 okuma | Karakter (istek + yanit) | Hat suresi |
|---|---|---|
| 10 register | 33 | ~23 ms |
| 50 register | 113 | ~69 ms |
| 100 register | 213 | ~126 ms |
| 125 register | 263 | ~155 ms |
<!-- /URETILMIS:hat-butcesi -->

## 13. Neden kendi Modbus TCP sunucumuz?

Projede pymodbus 3.7.4 var ve plan başta onun sunucusunu öngörüyordu. 13 Eylül'deki denemede bu sürümün sunucusu her istemci
bağlantısı kapandığında `0.0.0.0` üzerinde **rastgele bir portta yeni bir dinleme soketi açtı** (3 bağlantı → 3 sızan port).
Her tarama turunda yeniden bağlanan bir SCADA ön-ucu, sunucuda sayısız açık port bırakırdı: hem kaynak sızıntısı hem saldırı yüzeyi.
Ayrıca o sürüm, yazma isteğini değerine göre (şifre) reddetmeye ve bağlantıyı kabul anında IP'ye göre kesmeye izin vermiyordu.

Modbus TCP çerçevesi küçük olduğu için sunucu asyncio ile yazıldı (`modbus_tcp.py`, FC01/02/03/04/06/16). pymodbus **istemcisi**
testlerde bağımsız bir uygulama olarak kullanılır: sunucumuzla konuşabilmesi, başka istemcilerle (QModMaster, SCADA sürücüleri)
birlikte çalışabilirliğin kanıtıdır. Spesifikasyon kenar durumları (bölünmüş TCP paketi, arka arkaya iki istek, yanlış protokol
kimliği, adet sınırları) ayrıca elle kurulmuş ham çerçevelerle sınanır.

## 14. Doğrulama — donanım olmadan neyi kanıtladık

| Kanıt | Nasıl | Sonuç |
|---|---|---|
| Harita tutarlılığı | `test_map_loader.py`: gerçek sözleşmede adresler, çakışma, tip, nokta sırası | 41 test |
| Değer kodlama | `test_scada_encoder.py`: `tel_valid.json`'dan elle hesaplanmış ham değerler | 84 test; 28/28 mutasyon yakalandı |
| Protokol | `test_modbus_tcp.py`: pymodbus istemcisi + ham çerçeveler | 35 test; 19/19 mutasyon yakalandı |
| Ağ geçidi politikası | `test_scada_gateway.py`: gerçek TCP, gerçek alarm servisi, şifre/kilit/GK6/komutlar | 60 test (10.000 panoluk filo dahil); 35/35 mutasyon yakalandı |
| Uygulama bağlantısı | `test_scada_app.py`: **Modbus değeri = API değeri**, port doluyken backend ayakta | 9 test |
| Doküman güncelliği | `test_gen_modbus_doc.py`: bu doküman ve CSV sözleşmeden yeniden üretilebiliyor | 6 test |
| Canlı yığın (13 Eyl) | `docker compose` yığını, PC'den Modbus TCP okuması | 3 panoda `conn_temp` = API × 10; eşlenmemiş birim 0x0A; şifresiz yazma 0x01; harita boşluğu 0x02 |
| Canlı yazma (13 Eyl) | Geçici şifreyle | TVOC-2 aynasına doğru şifreyle yazma **0x02**; yanlış şifre 0x03; şifresiz komut 0x01; bakım modu ve test alarmı komutları MQTT `cmd` topic'inde sözleşmedeki biçimde yakalandı |

**Simüle edilen:** SCADA istemcisi (pymodbus / QModMaster), panolar (veri üreteci). **Gerçek olan:** Modbus TCP sunucusu, register
kodlaması, yazma politikası ve MQTT komut yolu — sahada aynı kod çalışır; değişen yalnızca `MODBUS_UNITS` ve izinli ağdır.
