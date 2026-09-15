# 04 — IEC 60870-5-104 Nokta Planı

> **Sahip:** Kişi B · **Kapsam:** MoSCoW **Could** (PLAN.md TB3 Adım 8), TB3 Adım 1–7 bittikten sonra yapıldı.
> §2, §3, §5, §6 ve §7 tabloları sözleşmeden ve IEC 104 kodundan **üretilir** (`python scripts/gen_iec104_doc.py`); elle düzenlenmez
> (PLAN.md kural 10). **Kod:** `backend/app/scada/iec104.py` (çerçeve), `iec104_points.py` (nokta planı), `iec104_server.py` (istasyon).

## 1. Neden IEC 104, neden aynı veri?

Dağıtım SCADA'larında Modbus TCP'den çok **IEC 60870-5-104** kullanılır (rapor §6.3, §6.4c). Merkez bu yüzden aynı veriyi iki protokolle
sunar ve ikisi **aynı ağ geçidini** paylaşır:

| | Modbus TCP (docs/03) | IEC 60870-5-104 (bu doküman) |
|---|---|---|
| Pano | Birim (unit id) 1–247 | Ortak adres (CA) = aynı birim numarası |
| Nokta | PDU adresi | IOA = 1000 + PDU adresi (ölçülen değer) |
| Değer | Ölçekli tam sayı (ham) | Fiziksel kayan nokta (ham × ölçek) |
| "Yok" | 0x8000 / 0xFFFF | **IV** (geçersiz) kalite bayrağı |
| Alarm bitleri | Register 800/801 bit alanı | Bit başına tek nokta (IOA 2000 + bit) |
| Değişiklik | SCADA okuyunca (yoklama) | **Kendiliğinden** gönderim, zaman etiketli (UTC) |
| Yazma | Yalnızca şifreli komut bloğu | **Yok**: istasyon salt okunur |

Değerler Modbus ağ geçidiyle aynı kodlayıcıdan (`encoder.py`) gelir: iki protokol aynı panoda aynı anda farklı değer gösteremez.

## 2. İstasyon parametreleri (üretilmiş)

<!-- URETILMIS:istasyon -->
| Parametre | Deger |
|---|---|
| Rol | Kontrollu istasyon (slave), TCP 2404 |
| Ortak adres (CA) | Modbus birim numarasi (`MODBUS_UNITS` veya otomatik) |
| Yayin adresi | `0xFFFF` = tum istasyonlar; her istasyon KENDI ortak adresiyle cevaplar (IEC 60870-5-101/104 7.2.4); hic istasyon yoksa hemen ret (COT 46) |
| IOA | 3 bayt |
| k / w | 12 / 8 |
| t1 / t2 / t3 | 15 s / 10 s / 20 s |
| Kendiliginden gonderim taramasi | 1 s |
| Nesne / ASDU | zamansiz en cok 30, zaman etiketli en cok 16 |
<!-- /URETILMIS:istasyon -->

## 3. Desteklenen ASDU tipleri ve iletim nedenleri (üretilmiş)

<!-- URETILMIS:asdu -->
| Tip | Ad | Yon | Anlami | COT |
|---|---|---|---|---|
| 13 | `M_ME_NC_1` | izleme | Olculen deger, kisa kayan nokta + QDS | 20 (sorgulama) |
| 36 | `M_ME_TF_1` | izleme | Olculen deger + CP56Time2a (UTC) | 3 (kendiliginden) |
| 1 | `M_SP_NA_1` | izleme | Tek nokta + SIQ | 20 |
| 30 | `M_SP_TB_1` | izleme | Tek nokta + CP56Time2a (UTC) | 3 |
| 100 | `C_IC_NA_1` | komut | Istasyon sorgulamasi (QOI 20): ACTCON -> veriler -> ACTTERM | 6 -> 7, 20, 10 |
| 103 | `C_CS_NA_1` | komut | Saat senkronu: istasyon saatiyle ACTCON (saat disaridan degistirilmez) | 6 -> 7 |
| 45, 46, ... | `C_SC_NA_1`, `C_DC_NA_1` ve diger tum tipler | komut | **Reddedilir** (istasyon salt okunur, GK6) | -> 44 + P/N |
| - | Bilinmeyen ortak adres | - | Reddedilir | -> 46 + P/N |
| - | Desteklenmeyen iletim nedeni | - | Reddedilir | -> 45 + P/N |
<!-- /URETILMIS:asdu -->

## 4. Adres planı kuralları

- **Ölçülen değerler:** IOA = 1000 + Modbus PDU adresi. Örnek: `conn_temp.GIRIS_L2` (PDU 101) → **IOA 1101**; `k_index` yüzde cinsindendir
  (K/K₀ = 1,45 → 145,0).
- **Alarm bitleri:** IOA = 2000 + `alarm-codes.yaml` biti. Değer, merkez alarm yöneticisinin **canlı** durumudur (active/acked ve koşul
  sürüyor; rafa alınmış alarm duyurulmaz). Mandallı kopya IEC 104'te yoktur: olay zaman etiketli kendiliğinden gönderimle zaten kaydedilir.
- **Özet bitler:** IOA = 3000 + coil adresi (kritik alarm, uyarı, haberleşme, bakım, koruma sağlığı, veri kalitesi).
- **Komut bloğu** (Modbus 900–909) IEC 104'te **sunulmaz**.
- **Geçersiz kalite (IV):** kenarın göndermediği alan veya verisi olmayan pano. Alarm durumu henüz yüklenmemiş bir panonun tüm noktaları IV
  gelir; SCADA "alarm yok" sanmaz.
- **Kendiliğinden gönderim:** ölçekli değer 10 ham adım (0,1 ölçekte 1,0) değişince veya kalite değişince; tek nokta her değişimde.
  STARTDT anında o anki değerler taban alınır.
- **Zaman etiketi = merkezin değişikliği gördüğü an** (UTC, 1 s tarama), kenarın ölçüm anı değil: etiket, ölçüm periyodu kadar
  (demoda 10 s) geç kalabilir. Bilinçli sınır: ağ geçidi görüntüsü nokta başına zaman taşımaz. Olayın kesin zamanı olay kaydında
  (`/api/v1/events/{id}/blackbox`) ve Modbus olay bloğunda (830–833) durur.
- **Yayın adresi (`0xFFFF`):** her istasyon kendi ortak adresiyle ayrı ACTCON → veriler → ACTTERM döner; saat senkronu da istasyon başına
  onaylanır.

## 5. Ölçülen değerler (üretilmiş)

<!-- URETILMIS:olculen -->
| IOA | Ad | Modbus PDU | Birim | Olcek | Olu bant | IV (gecersiz) kosulu | Merkez kaynagi |
|---|---|---|---|---|---|---|---|
| 1000 | `device_info.map_version` | 0 | - | 1 | 1 | ham 0xFFFF | modbus-map.yaml `version` |
| 1001 | `device_info.fw_version` | 1 | - | 1 | 1 | ham 0xFFFF | `fw` 'M.m.p' -> 0xMmpp |
| 1002 | `device_info.serial_hi` | 2 | - | 1 | 1 | ham 0xFFFF | - (kenar merkeze gondermiyor; hep 'yok') |
| 1003 | `device_info.serial_lo` | 3 | - | 1 | 1 | ham 0xFFFF | - (kenar merkeze gondermiyor; hep 'yok') |
| 1004 | `device_info.pano_type` | 4 | - | 1 | 1 | ham 0xFFFF | `panels.pano_type` (1600kVA-dahili = 1, bilinmeyen = 0) |
| 1005 | `device_info.point_count` | 5 | - | 1 | 1 | ham 0xFFFF | `t_conn` nokta sayisi |
| 1020 | `health.uptime_h` | 20 | - | 1 | 1 | ham 0xFFFF | `health.uptime_s` / 3600 |
| 1021 | `health.last_sync_m` | 21 | - | 1 | 1 | ham 0xFFFF | merkezin panodan son veri aldigi andan beri gecen dakika |
| 1022 | `health.supply_state` | 22 | - | 1 | 1 | ham 0xFFFF | canli ALM-LASTGASP -> 2; aksi halde 'yok' |
| 1023 | `health.backup_pct` | 23 | - | 1 | 1 | ham 0xFFFF | `health.vbak_pct` |
| 1024 | `health.rssi_dbm_neg` | 24 | - | 1 | 1 | ham 0xFFFF | -`health.rssi_dbm` |
| 1025 | `health.nodes_ok` | 25 | - | 1 | 1 | ham 0xFFFF | `health.nodes_ok` |
| 1026 | `health.nodes_total` | 26 | - | 1 | 1 | ham 0xFFFF | `health.nodes_total` |
| 1027 | `health.heartbeat` | 27 | - | 1 | 1 | ham 0xFFFF | `seq` (16 bit sarar; donarsa kenar sessiz) |
| 1028 | `health.buffered_msgs` | 28 | - | 1 | 1 | ham 0xFFFF | `health.buffered` |
| 1029 | `health.baseline_day` | 29 | - | 1 | 1 | ham 0xFFFF | `health.baseline_day` |
| 1100 | `conn_temp.GIRIS_L1` | 100 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[GIRIS_L1].t_c` |
| 1101 | `conn_temp.GIRIS_L2` | 101 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[GIRIS_L2].t_c` |
| 1102 | `conn_temp.GIRIS_L3` | 102 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[GIRIS_L3].t_c` |
| 1103 | `conn_temp.GIRIS_N` | 103 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[GIRIS_N].t_c` |
| 1104 | `conn_temp.DSYA1_L1` | 104 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA1_L1].t_c` |
| 1105 | `conn_temp.DSYA1_L2` | 105 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA1_L2].t_c` |
| 1106 | `conn_temp.DSYA1_L3` | 106 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA1_L3].t_c` |
| 1107 | `conn_temp.DSYA2_L1` | 107 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA2_L1].t_c` |
| 1108 | `conn_temp.DSYA2_L2` | 108 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA2_L2].t_c` |
| 1109 | `conn_temp.DSYA2_L3` | 109 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA2_L3].t_c` |
| 1110 | `conn_temp.DSYA3_L1` | 110 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA3_L1].t_c` |
| 1111 | `conn_temp.DSYA3_L2` | 111 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA3_L2].t_c` |
| 1112 | `conn_temp.DSYA3_L3` | 112 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA3_L3].t_c` |
| 1113 | `conn_temp.DSYA4_L1` | 113 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA4_L1].t_c` |
| 1114 | `conn_temp.DSYA4_L2` | 114 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA4_L2].t_c` |
| 1115 | `conn_temp.DSYA4_L3` | 115 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA4_L3].t_c` |
| 1116 | `conn_temp.DSYA5_L1` | 116 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA5_L1].t_c` |
| 1117 | `conn_temp.DSYA5_L2` | 117 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA5_L2].t_c` |
| 1118 | `conn_temp.DSYA5_L3` | 118 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA5_L3].t_c` |
| 1119 | `conn_temp.DSYA6_L1` | 119 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA6_L1].t_c` |
| 1120 | `conn_temp.DSYA6_L2` | 120 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA6_L2].t_c` |
| 1121 | `conn_temp.DSYA6_L3` | 121 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA6_L3].t_c` |
| 1122 | `conn_temp.DSYA7_L1` | 122 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA7_L1].t_c` |
| 1123 | `conn_temp.DSYA7_L2` | 123 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA7_L2].t_c` |
| 1124 | `conn_temp.DSYA7_L3` | 124 | degC | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA7_L3].t_c` |
| 1150 | `conn_dt.GIRIS_L1` | 150 | K | 0.1 | 1 | ham 0x8000 | `t_conn[GIRIS_L1].dt_c` |
| 1151 | `conn_dt.GIRIS_L2` | 151 | K | 0.1 | 1 | ham 0x8000 | `t_conn[GIRIS_L2].dt_c` |
| 1152 | `conn_dt.GIRIS_L3` | 152 | K | 0.1 | 1 | ham 0x8000 | `t_conn[GIRIS_L3].dt_c` |
| 1153 | `conn_dt.GIRIS_N` | 153 | K | 0.1 | 1 | ham 0x8000 | `t_conn[GIRIS_N].dt_c` |
| 1154 | `conn_dt.DSYA1_L1` | 154 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA1_L1].dt_c` |
| 1155 | `conn_dt.DSYA1_L2` | 155 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA1_L2].dt_c` |
| 1156 | `conn_dt.DSYA1_L3` | 156 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA1_L3].dt_c` |
| 1157 | `conn_dt.DSYA2_L1` | 157 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA2_L1].dt_c` |
| 1158 | `conn_dt.DSYA2_L2` | 158 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA2_L2].dt_c` |
| 1159 | `conn_dt.DSYA2_L3` | 159 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA2_L3].dt_c` |
| 1160 | `conn_dt.DSYA3_L1` | 160 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA3_L1].dt_c` |
| 1161 | `conn_dt.DSYA3_L2` | 161 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA3_L2].dt_c` |
| 1162 | `conn_dt.DSYA3_L3` | 162 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA3_L3].dt_c` |
| 1163 | `conn_dt.DSYA4_L1` | 163 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA4_L1].dt_c` |
| 1164 | `conn_dt.DSYA4_L2` | 164 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA4_L2].dt_c` |
| 1165 | `conn_dt.DSYA4_L3` | 165 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA4_L3].dt_c` |
| 1166 | `conn_dt.DSYA5_L1` | 166 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA5_L1].dt_c` |
| 1167 | `conn_dt.DSYA5_L2` | 167 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA5_L2].dt_c` |
| 1168 | `conn_dt.DSYA5_L3` | 168 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA5_L3].dt_c` |
| 1169 | `conn_dt.DSYA6_L1` | 169 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA6_L1].dt_c` |
| 1170 | `conn_dt.DSYA6_L2` | 170 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA6_L2].dt_c` |
| 1171 | `conn_dt.DSYA6_L3` | 171 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA6_L3].dt_c` |
| 1172 | `conn_dt.DSYA7_L1` | 172 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA7_L1].dt_c` |
| 1173 | `conn_dt.DSYA7_L2` | 173 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA7_L2].dt_c` |
| 1174 | `conn_dt.DSYA7_L3` | 174 | K | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA7_L3].dt_c` |
| 1200 | `k_index.GIRIS_L1` | 200 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[GIRIS_L1].k_ratio` x 100 |
| 1201 | `k_index.GIRIS_L2` | 201 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[GIRIS_L2].k_ratio` x 100 |
| 1202 | `k_index.GIRIS_L3` | 202 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[GIRIS_L3].k_ratio` x 100 |
| 1203 | `k_index.GIRIS_N` | 203 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[GIRIS_N].k_ratio` x 100 |
| 1204 | `k_index.DSYA1_L1` | 204 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA1_L1].k_ratio` x 100 |
| 1205 | `k_index.DSYA1_L2` | 205 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA1_L2].k_ratio` x 100 |
| 1206 | `k_index.DSYA1_L3` | 206 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA1_L3].k_ratio` x 100 |
| 1207 | `k_index.DSYA2_L1` | 207 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA2_L1].k_ratio` x 100 |
| 1208 | `k_index.DSYA2_L2` | 208 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA2_L2].k_ratio` x 100 |
| 1209 | `k_index.DSYA2_L3` | 209 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA2_L3].k_ratio` x 100 |
| 1210 | `k_index.DSYA3_L1` | 210 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA3_L1].k_ratio` x 100 |
| 1211 | `k_index.DSYA3_L2` | 211 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA3_L2].k_ratio` x 100 |
| 1212 | `k_index.DSYA3_L3` | 212 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA3_L3].k_ratio` x 100 |
| 1213 | `k_index.DSYA4_L1` | 213 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA4_L1].k_ratio` x 100 |
| 1214 | `k_index.DSYA4_L2` | 214 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA4_L2].k_ratio` x 100 |
| 1215 | `k_index.DSYA4_L3` | 215 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA4_L3].k_ratio` x 100 |
| 1216 | `k_index.DSYA5_L1` | 216 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA5_L1].k_ratio` x 100 |
| 1217 | `k_index.DSYA5_L2` | 217 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA5_L2].k_ratio` x 100 |
| 1218 | `k_index.DSYA5_L3` | 218 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA5_L3].k_ratio` x 100 |
| 1219 | `k_index.DSYA6_L1` | 219 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA6_L1].k_ratio` x 100 |
| 1220 | `k_index.DSYA6_L2` | 220 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA6_L2].k_ratio` x 100 |
| 1221 | `k_index.DSYA6_L3` | 221 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA6_L3].k_ratio` x 100 |
| 1222 | `k_index.DSYA7_L1` | 222 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA7_L1].k_ratio` x 100 |
| 1223 | `k_index.DSYA7_L2` | 223 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA7_L2].k_ratio` x 100 |
| 1224 | `k_index.DSYA7_L3` | 224 | percent_of_baseline | 0.1 | 1 | ham 0x8000 | `t_conn[DSYA7_L3].k_ratio` x 100 |
| 1300 | `environment.t_low_c` | 300 | degC | 0.1 | 1 | ham 0x8000 | `env.t_low_c` |
| 1301 | `environment.rh_low_pct` | 301 | percent | 0.1 | 1 | ham 0x8000 | `env.rh_low_pct` |
| 1302 | `environment.td_low_c` | 302 | degC | 0.1 | 1 | ham 0x8000 | `env.td_low_c` |
| 1303 | `environment.td_margin_k` | 303 | K | 0.1 | 1 | ham 0x8000 | `env.td_margin_k` |
| 1304 | `environment.t_up_c` | 304 | degC | 0.1 | 1 | ham 0x8000 | `env.t_up_c` |
| 1305 | `environment.rh_up_pct` | 305 | percent | 0.1 | 1 | ham 0x8000 | `env.rh_up_pct` |
| 1306 | `environment.dt_air_k` | 306 | K | 0.1 | 1 | ham 0x8000 | `env.dt_air_k` |
| 1307 | `environment.voc_idx` | 307 | index | 0.1 | 1 | ham 0xFFFF | `env.voc_idx` |
| 1400 | `electrical_mirror.i_l1_a` | 400 | - | 0.1 | 1 | ham 0xFFFF | `elec.i_ph[0]` |
| 1401 | `electrical_mirror.i_l2_a` | 401 | - | 0.1 | 1 | ham 0xFFFF | `elec.i_ph[1]` |
| 1402 | `electrical_mirror.i_l3_a` | 402 | - | 0.1 | 1 | ham 0xFFFF | `elec.i_ph[2]` |
| 1403 | `electrical_mirror.i_n_a` | 403 | - | 0.1 | 1 | ham 0xFFFF | `elec.i_n` |
| 1404 | `electrical_mirror.u_l1_v` | 404 | - | 0.1 | 1 | ham 0xFFFF | `elec.u_ph[0]` |
| 1405 | `electrical_mirror.u_l2_v` | 405 | - | 0.1 | 1 | ham 0xFFFF | `elec.u_ph[1]` |
| 1406 | `electrical_mirror.u_l3_v` | 406 | - | 0.1 | 1 | ham 0xFFFF | `elec.u_ph[2]` |
| 1407 | `electrical_mirror.thd_i_l1_pct` | 407 | - | 0.1 | 1 | ham 0xFFFF | `elec.thd_i[0]` |
| 1408 | `electrical_mirror.thd_i_l2_pct` | 408 | - | 0.1 | 1 | ham 0xFFFF | `elec.thd_i[1]` |
| 1409 | `electrical_mirror.thd_i_l3_pct` | 409 | - | 0.1 | 1 | ham 0xFFFF | `elec.thd_i[2]` |
| 1410 | `electrical_mirror.cosphi` | 410 | - | 0.001 | 0.01 | ham 0x8000 | `elec.cosphi` |
| 1411 | `electrical_mirror.unbal_pct` | 411 | - | 0.1 | 1 | ham 0xFFFF | `elec.unbal_pct` |
| 1412 | `electrical_mirror.mpr_comm_ok` | 412 | - | 1 | 1 | - | `elec` geldiyse 1 |
| 1500 | `arc_mirror.system_state` | 500 | - | 1 | 1 | ham 0xFFFF | `tvoc.state` |
| 1501 | `arc_mirror.trip_count` | 501 | - | 1 | 1 | ham 0xFFFF | `tvoc.trips` |
| 1502 | `arc_mirror.last_det_low` | 502 | - | 1 | 1 | ham 0xFFFF | `tvoc.det_bits_low` |
| 1503 | `arc_mirror.last_det_high` | 503 | - | 1 | 1 | ham 0xFFFF | `tvoc.det_bits_high` |
| 1504 | `arc_mirror.last_trip_relay` | 504 | - | 1 | 1 | ham 0xFFFF | - (kenar merkeze gondermiyor; hep 'yok') |
| 1505 | `arc_mirror.last_trip_date` | 505 | - | 1 | 1 | ham 0xFFFF | - (kenar merkeze gondermiyor; hep 'yok') |
| 1506 | `arc_mirror.last_trip_hhmm` | 506 | - | 1 | 1 | ham 0xFFFF | - (kenar merkeze gondermiyor; hep 'yok') |
| 1507 | `arc_mirror.last_trip_sec` | 507 | - | 1 | 1 | ham 0xFFFF | - (kenar merkeze gondermiyor; hep 'yok') |
| 1508 | `arc_mirror.sensor_status_x2` | 508 | - | 1 | 1 | ham 0xFFFF | `tvoc.sensor_x2` |
| 1509 | `arc_mirror.sensor_status_x3` | 509 | - | 1 | 1 | ham 0xFFFF | `tvoc.sensor_x3` |
| 1510 | `arc_mirror.amb_light_x2` | 510 | - | 1 | 1 | ham 0xFFFF | `tvoc.amb_light_x2` |
| 1511 | `arc_mirror.amb_light_x3` | 511 | - | 1 | 1 | ham 0xFFFF | `tvoc.amb_light_x3` |
| 1512 | `arc_mirror.active_dtc_1` | 512 | - | 1 | 1 | ham 0xFFFF | - (kenar merkeze gondermiyor; hep 'yok') |
| 1513 | `arc_mirror.prot_health_ok` | 513 | - | 1 | 1 | - | `tvoc.prot_health_ok` (TVOC-2 yoksa 0) |
| 1514 | `arc_mirror.tvoc_comm_ok` | 514 | - | 1 | 1 | - | `tvoc.comm_ok` (TVOC-2 yoksa 0) |
| 1600 | `pd.pulses_per_s` | 600 | - | 1 | 1 | ham 0xFFFF | `pd.pps` |
| 1601 | `pd.amp_dbmv` | 601 | - | 1 | 1 | - | `pd.amp_dbmv` |
| 1602 | `pd.trend_slope` | 602 | - | 0.01 | 0.1 | - | `pd.trend` |
| 1603 | `pd.phase_cluster` | 603 | - | 0.01 | 0.1 | ham 0xFFFF | `pd.phase_cluster` |
| 1700 | `risk.risk_score` | 700 | - | 1 | 1 | ham 0xFFFF | `risk.score` |
| 1701 | `risk.fault_mode` | 701 | - | 1 | 1 | ham 0xFFFF | `risk.mode` -> hypotheses[].id |
| 1702 | `risk.ttl_hours` | 702 | - | 1 | 1 | ham 0xFFFF | `risk.ttl_h` |
| 1703 | `risk.worst_point` | 703 | - | 1 | 1 | ham 0xFFFF | en kotu nokta: durum > K/K0 > dT (yalnizca q = 0) |
| 1830 | `event.event_count` | 830 | - | 1 | 1 | ham 0xFFFF | ag gecidinin gordugu alarm acilislari (16 bit sarar) |
| 1831 | `event.last_code` | 831 | - | 1 | 1 | ham 0xFFFF | son acilan alarmin bit numarasi |
| 1832 | `event.ts_hi` | 832 | - | 1 | 1 | - | son acilisin olay zamani, Unix s yuksek word |
| 1833 | `event.ts_lo` | 833 | - | 1 | 1 | - | son acilisin olay zamani, Unix s dusuk word |
<!-- /URETILMIS:olculen -->

## 6. Tek noktalar (üretilmiş)

<!-- URETILMIS:tek-nokta -->
| IOA | Ad | Tur | Oncelik | Aciklama |
|---|---|---|---|---|
| 2000 | `ALM-THR-TERM-WARN` | alarm biti 0 | P3 | Terminal sicaklik artisi 50 K ustu |
| 2001 | `ALM-THR-TERM-ALM` | alarm biti 1 | P2 | Terminal sicaklik artisi 70 K ustu |
| 2002 | `ALM-THR-BUS-ALM` | alarm biti 2 | P1 | Bara sicaklik artisi 105 K ustu |
| 2003 | `ALM-THR-PHASE-DIF` | alarm biti 3 | P2 | Benzer yukte fazlar arasi fark 15 K ustu |
| 2004 | `ALM-K-WARN` | alarm biti 4 | P3 | Isil direnc indeksi K/K0 > 1.3 — baglanti direnci artisi suphesi |
| 2005 | `ALM-K-ALM` | alarm biti 5 | P2 | Isil direnc indeksi K/K0 > 1.6 — gevsek/oksitlenmis baglanti |
| 2006 | `ALM-TTL-14D` | alarm biti 6 | P3 | 70 K sinirina tahmini 14 gunden az kaldi |
| 2007 | `ALM-DEW-WARN` | alarm biti 7 | P3 | Ciy noktasi marji 3 K altinda |
| 2008 | `ALM-DEW-ALM` | alarm biti 8 | P2 | Ciy noktasi marji 1 K altinda — yogusma riski |
| 2009 | `ALM-I-OVER` | alarm biti 9 | P2 | Faz akimi anma degerinin ustunde |
| 2010 | `ALM-NEUTRAL-THD` | alarm biti 10 | P3 | Notr akimi ve akim THD birlikte artti — harmonik kaynakli notr isinmasi |
| 2011 | `ALM-ARC-TRIP` | alarm biti 11 | P1 | TVOC-2 ark tripi |
| 2012 | `ALM-PROT-HEALTH` | alarm biti 12 | P1 | Ark korumasi dedektor arizasi — pano sessizce korumasiz |
| 2013 | `ALM-PD-TREND` | alarm biti 13 | P3 | PD darbe sayisi/genligi trendi artiyor (OG) |
| 2014 | `ALM-DQ-FROZEN` | alarm biti 14 | SYS | Sensor degeri donmus (N ornek ayni) |
| 2015 | `ALM-DQ-JUMP` | alarm biti 15 | SYS | Fiziksel olmayan degisim hizi |
| 2016 | `ALM-DQ-BELOW-AMBIENT` | alarm biti 16 | SYS | Baglanti sicakligi ortamin altinda — sensor yerinden dusmus olabilir |
| 2017 | `ALM-NODE-LOST` | alarm biti 17 | SYS | Dugum sessiz |
| 2018 | `ALM-COMMS-LOST` | alarm biti 18 | SYS | Merkez baglantisi koptu (heartbeat yok) |
| 2019 | `ALM-DOOR-UNAUTH` | alarm biti 19 | P2 | Planli is emri olmadan kapak acildi |
| 2020 | `ALM-LASTGASP` | alarm biti 20 | P2 | Besleme kesildi (son nefes mesaji) |
| 2021 | `ALM-PANEL-TEMP` | alarm biti 21 | P2 | Pano ic ortam sicakligi 45 degC ustu |
| 3000 | `critical_alarm` | coil 0 | - | canli P1 alarm var |
| 3001 | `warning_active` | coil 1 | - | canli P2 veya P3 alarm var |
| 3002 | `comms_ok` | coil 2 | - | son veri heartbeat_timeout_min icinde |
| 3003 | `maint_mode` | coil 3 | - | `health.maint_mode` |
| 3004 | `prot_health_ok` | coil 4 | - | `tvoc.prot_health_ok` (TVOC-2 yoksa 0) |
| 3005 | `data_quality_ok` | coil 5 | - | tum noktalarda q = 0 ve canli ALM-DQ-* yok |
<!-- /URETILMIS:tek-nokta -->

## 7. Birlikte çalışabilirlik (üretilmiş)

IEC 60870-5-104 uygulayan her ürün, standardın ek formundaki **bölüm başlıklarıyla** bir birlikte çalışabilirlik listesi yayımlar;
SCADA entegrasyon mühendisi bu formu okur. Aşağıdaki blok o başlıkları kullanır, satırların tamamını `backend/app/scada/` kodundan
üretir (`python scripts/gen_iec104_doc.py`) ve elle düzenlenmez.

<!-- URETILMIS:birlikte-calisabilirlik -->
> Isaretleme: **X** = uygulandi, **-** = uygulanmadi/desteklenmiyor. Satirlarin tamami `backend/app/scada/` kodundan okunur; bu blok elle duzenlenmez.

### 7.1 Genel bilgi (sistem veya cihaz)

| Satir | Isaret | Kaynak |
|---|---|---|
| Kontrollu istasyon (alt istasyon) tanimi | X | `iec104_server.Iec104Server`, salt okunur |
| Kontrol eden istasyon (ana istasyon) tanimi | - | modulde istemci/ana istasyon sinifi yok; merkez baglanti kurmaz |
| Uygulama katmani | X | IEC 60870-5-101 ASDU'lari, IEC 60870-5-104 ag erisimiyle (`iec104.py`) |
| Yazma / kontrol yolu | - | her kontrol ASDU'su COT 44 + P/N ile reddedilir (GK6) |

### 7.2 Ag yapilandirmasi

| Ozellik | Deger | Kaynak |
|---|---|---|
| Ag erisimi | TCP/IP uzerinde coklu istemci | `asyncio.start_server` |
| Es zamanli baglanti siniri | 8 | `Iec104Server(max_connections=...)` |
| Istasyon basina ortak adres | her pano bir CA (= Modbus birim numarasi) | `iec104_points`, `gateway` |
| Yedekli baglanti grubu | - | tek dinleyici soket; yedeklilik uygulanmadi |
| Seri hat yapilandirmasi (noktadan noktaya, coklu nokta) | - | IEC 60870-5-104 seri hat kullanmaz |

### 7.3 Fiziksel katman

| Ozellik | Deger | Kaynak |
|---|---|---|
| Tasima | TCP/IP | `Iec104Server.start` |
| Dinlenen port | 2404 (`IEC104_PORT`) | `Iec104Server(port=...)` |
| Dinlenen arayuz | `0.0.0.0` (`IEC104_HOST`) | `Iec104Server(host=...)` |
| Izinli istemci aglari | `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `::1/128` (`IEC104_ALLOWED_CLIENTS` ile daraltilir) | `DEFAULT_ALLOWED_NETWORKS` |
| Iletim hizi, seri cerceve (FT 1.2), bagli katman adresi | - | ag erisiminde yok |

### 7.4 Baglanti katmani (APCI)

| Ozellik | Deger | Kaynak |
|---|---|---|
| Baslangic bayti | 0x68 | `iec104.START` |
| Kontrol alani | 4 bayt; I (veri), S (onay), U (STARTDT/STOPDT/TESTFR) | `decode_apdu` |
| Azami APDU (uzunluk alani: kontrol alani + ASDU) | 253 | `iec104.MAX_LENGTH` |
| Azami APDU (hat uzerinde, baslangic + uzunluk dahil) | 255 | `0x68` + uzunluk bayti + APDU |
| Azami ASDU | 249 | `iec104.MAX_ASDU` |
| Sira numarasi modulu | 32768 | `iec104.SEQ_MODULO` (15 bit) |
| Bir ASDU'ya sigan azami nesne | M_SP_NA_1: 60, M_ME_NC_1: 30, M_SP_TB_1: 22, M_ME_TF_1: 16 | azami ASDU / (IOA + eleman); istasyonun grup siniri 30 / 16 (§2) |
| Dengeli / dengesiz iletim | 104'te yalnizca dengeli; yoklama yok | - |

### 7.5 Uygulama katmani: alan uzunluklari

| Alan | Uzunluk (oktet) | Not |
|---|---|---|
| Tip tanimlayici | 1 | `encode_asdu` ciktisinin ilk bayti |
| Degisken yapi niteleyici (VSQ) | 1 | SQ = 0 uretilir (her nesne kendi adresiyle); SQ = 1 cozulur |
| Iletim nedeni (COT) | 2 | neden + kaynak adres; kaynak adres gelen cercevedeki degeriyle geri doner |
| Ortak adres (ASDU adresi) | 2 | yayin adresi 0xFFFF |
| Bilgi nesnesi adresi (IOA) | 3 | 1000 / 2000 / 3000 tabanli plan (§4) |
| Zaman etiketi | 7 | CP56Time2a, UTC, yaz saati biti 0 |

### 7.6 Standartlastirilmis ASDU secimi

| Tip | Ad | Yon | Isaret | Not |
|---|---|---|---|---|
| 1 | `M_SP_NA_1` | izleme | X | Tek nokta + SIQ; sorgulama cevabi |
| 13 | `M_ME_NC_1` | izleme | X | Olculen deger, kisa kayan nokta + QDS; sorgulama cevabi |
| 30 | `M_SP_TB_1` | izleme | X | Tek nokta + CP56Time2a (UTC); kendiliginden |
| 36 | `M_ME_TF_1` | izleme | X | Olculen deger + CP56Time2a (UTC); kendiliginden |
| 70 | `M_EI_NA_1` | izleme | - | Baslatma sonu: kodekte tanimli, istasyon GONDERMEZ (oturum STARTDT ile baslar) |
| - | Cift nokta, adim konumu, bit dizisi, sayac, koruma olayi | izleme | - | kodekte tanimli degil; sunulmaz |
| 45 | `C_SC_NA_1` | kontrol | - | Tek komut: cozulur, calistirilmaz (istasyon salt okunur, GK6) |
| 46 | `C_DC_NA_1` | kontrol | - | Cift komut: cozulur, calistirilmaz (istasyon salt okunur, GK6) |
| 100 | `C_IC_NA_1` | kontrol | X | Istasyon sorgulamasi, yalnizca QOI 20 (grup sorgulamasi yok) |
| 103 | `C_CS_NA_1` | kontrol | X | Saat senkronu: istasyon saatiyle ACTCON, merkez saati degismez |
| - | Diger tum kontrol tipleri | kontrol | - | kodek tanimadigi icin COT 44 + P/N |

### 7.7 Tip - iletim nedeni matrisi

| Tip | 3<br>kendiliginden | 6<br>etkinlestirme | 7<br>etkinlestirme onayi | 10<br>etkinlestirme sonu | 20<br>sorgulama cevabi | 44<br>bilinmeyen tip | 45<br>bilinmeyen neden | 46<br>bilinmeyen ortak adres |
|---|---|---|---|---|---|---|---|---|
| `M_SP_NA_1` | - | - | - | - | X | - | - | - |
| `M_ME_NC_1` | - | - | - | - | X | - | - | - |
| `M_SP_TB_1` | X | - | - | - | - | - | - | - |
| `M_ME_TF_1` | X | - | - | - | - | - | - | - |
| `C_IC_NA_1` | - | X | X | X | - | - | X | X |
| `C_CS_NA_1` | - | X | X | - | - | - | X | X |
| Diger tum tipler | - | - | - | - | - | X | - | - |

Reddetme nedenleri (44, 45, 46) her zaman P/N biti kurulu dondurulur. Istasyon sorgulamasi QOI 20 disinda bir nitelikle gelirse ACTCON P/N ile dondurulur; grup sorgulamasi yoktur. Kodekte tanimli olup hicbir SCADA modulunde gecmeyen sabitler: `C_SC_NA_1`, `C_DC_NA_1`, `M_EI_NA_1`, `COT_INITIALIZED`, `COT_UNKNOWN_IOA`.

### 7.8 Temel uygulama fonksiyonlari

| Fonksiyon | Isaret | Kaynak | Not |
|---|---|---|---|
| Istasyon baslatma (baslatma sonu bildirimi) | - | `M_EI_NA_1` = 70 | tip tanimli ama hicbir yerde uretilmiyor; baslatma yerine STARTDT/STOPDT kullanilir |
| Istasyon sorgulamasi | X | `C_IC_NA_1` = 100 | ACTCON -> tum noktalar (COT 20) -> ACTTERM; yayin adresinde istasyon basina ayri |
| Saat senkronizasyonu | X | `C_CS_NA_1` = 103 | yalnizca onay: NTP disindan saat oynatilmaz |
| Komut iletimi | - | `C_SC_NA_1` = 45 | tum kontrol ASDU'lari reddedilir; koruma cihazina yol yoktur (GK6) |
| Sayac (integrated totals) sorgulamasi | - | `C_CI_NA_1` kodekte tanimli degil | sayac nesnesi sunulmuyor, sorgulanacak sayac yok |
| Parametre yukleme | - | `P_ME_NA_1` kodekte tanimli degil | esik/parametre uzaktan yazilmaz; esikler contracts/ dizininden gelir |
| Test yordami (test komutu) | - | `C_TS_NA_1` kodekte tanimli degil | canlilik denetimi APCI duzeyinde TESTFR ile yapilir |
| Dosya transferi | - | `F_FR_NA_1` kodekte tanimli degil | kayit/dosya aktarimi yok; olay kaydi REST ucundan alinir |
| Nokta bazli okuma (okuma yordami) | - | `C_RD_NA_1` kodekte tanimli degil | nokta bazli okuma yok; bu yuzden bilinmeyen IOA reddi (COT 47) hic kullanilmaz |
| Kendiliginden gonderim | X | `_Connection._spontaneous` | olu bant asilinca M_ME_TF_1, tek nokta degisince M_SP_TB_1 |
| Baglanti canliligi denetimi (TESTFR) | X | `_Connection._timers` | t3 sonunda TESTFR gonderilir, t1 icinde cevap gelmezse baglanti kapanir |

### 7.9 Zaman asimlari, pencere parametreleri ve port

| Parametre | Deger | Not |
|---|---|---|
| t0 (baglanti kurma) | - | `Timing` alanlari: t1, t2, t3, k, w, spontaneous, tick; t0 yok - baglantiyi ana istasyon acar, istasyon hicbir zaman baglanti kurmaz |
| t1 (gonderilen I / TESTFR icin onay suresi) | 15 s | asilirsa baglanti kapatilir |
| t2 (alinan cerceveleri S ile onaylama) | 10 s | t1'den kucuk olmali |
| t3 (bosta TESTFR gonderme) | 20 s | sessiz baglanti canlilik denetimine girer |
| k (onaysiz gonderilebilen I cercevesi) | 12 | pencere dolunca gonderim bekletilir, baglanti kapatilmaz |
| w (onaylanmadan alinabilen I cercevesi) | 8 | w'inci cercevede S gonderilir |
| Port | 2404 | TCP, `IEC104_PORT` |
| Kendiliginden gonderim taramasi | 1 s | olu bant denetimi araligi |
| Zamanlayici adimi | 0.05 s | t1/t2/t3 denetim cozunurlugu |
<!-- /URETILMIS:birlikte-calisabilirlik -->

## 8. Güvenlik

- **Salt okunur:** kontrol komutları (`C_SC_NA_1`, `C_DC_NA_1` ve diğerleri) P/N bitiyle COT 44 döner; koruma cihazına (TVOC-2) hiçbir yol yoktur (GK6).
- **İzinli ağlar:** `IEC104_ALLOWED_CLIENTS` (varsayılan özel ağlar; sahada SCADA ön-ucunun adresi). Bağlantı sınırı 8.
- **Protokol ihlali bağlantıyı kapatır:** STARTDT öncesi I çerçevesi, sıra hatası, gönderilmemiş çerçeveyi onaylama, bozuk çerçeve.
- **Onay beklenmezse** (t1) veya TESTFR cevapsız kalırsa bağlantı kapanır; yarı açık bağlantı kaynak tutmaz.
- Saat senkronu merkez saatini **değiştirmez**: saat NTP'nin işidir, SCADA'dan gelen komutla sistem saati oynatılmaz.

## 9. Doğrulama

Bağımsız bir IEC 104 istemcisi kurulu olmadığı için kilit çerçeveler **standarttan elle çıkarılmış baytlarla** sınanır; örnek: istasyon
sorgulaması `68 0E 00 00 00 00 64 01 06 00 01 00 00 00 00 14` → ACTCON `68 0E 00 00 02 00 64 01 07 00 01 00 00 00 00 14`.

| Test | Kapsam | Mutasyon |
|---|---|---|
| `test_iec104_codec.py` | APCI I/S/U, ASDU, kısa kayan nokta, CP56Time2a | 12/12 |
| `test_iec104_points.py` | IOA planı, işaretli/ölçekli değer, IV kuralı, alarm bitleri, ölü bant | 9/9 |
| `test_iec104_server.py` (30 test) | Sorgulama, yayın adresi (istasyon başına cevap), reddedilen komut/adres/neden, saat senkronu, k/w penceresi, t1/t2/t3, kendiliğinden gönderim, STOPDT, izinli ağ | 37/37 |
| `test_scada_app.py` | Uygulama içinde: **IEC 104 değeri = API değeri**, Modbus kapalıyken IEC 104 çalışır, ayarlar | — |
| `test_gen_iec104_doc.py` | Bu dokümanın tabloları koddan güncel mi (`--check`); §7 alan uzunlukları kodlayıcıdan ölçülüyor mu, desteklenmeyen fonksiyonlar açıkça işaretli mi | — |

**Canlı yığında ölçüm (13 Eyl 2026, 3 simüle pano, `localhost:2404`).** Backend kodeğini kullanmayan, baytları elle kuran ayrı bir
istemciyle:

| Kontrol | Sonuç |
|---|---|
| Tek istasyon sorgulaması (CA 1) | 167 nokta (139 ölçülen + 28 tek nokta), 8 I çerçevesi, 2 ms |
| IEC 104 değeri = REST API değeri | 87 kontrol, **0 fark** (sıcaklık, ΔT, K/K₀, ortam, elektrik, sağlık, TVOC-2) |
| IEC 104 değeri = Modbus FC03 ham × ölçek | 139 adres, **0 fark** |
| Yayın sorgulaması (`0xFFFF`) | 3 istasyon, 501 nokta, 24 I çerçevesi; ACTCON/ACTTERM CA 1, 2, 3 ile ayrı ayrı |
| `C_SC_NA_1` kontrol komutu | COT 44 + P/N (reddedildi, `rejected_commands` arttı) |
| TESTFR | TESTFR_CON |
| Kendiliğinden gönderim (25 s) | 48 nesne, `M_ME_TF_1`; alınma − zaman etiketi 0,00 s |
| Onay göndermeyen istemci | 15 s sonra "t1 içinde onay gelmedi" ile bağlantı kapatıldı (beklenen) |

Bu canlı test ilk koşuda gerçek bir uyumsuzluk yakaladı: yayın sorgulamasına tek bir `0xFFFF` ACTCON/ACTTERM dönülüyordu; istasyon başına
GI izleyen bir ana istasyon sonlanmayı hiç görmezdi. Standarda (7.2.4) göre düzeltildi, önce testi kırmızıya çevrildi.
