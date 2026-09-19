# 12. Dogrulama Sonuclari

> Bu dosya ELLE YAZILMAZ. `python scripts/validate.py --out docs/12-dogrulama-sonuclari.md`
> komutu `data/fixtures/` altindaki seed'li senaryolari yeniden olcer ve bu tabloyu
> uretir (PLAN.md T4.2). Asagidaki her sayi tekrar uretilebilir.

Uretim zamani: 2026-09-19T20:50:57+03:00

## 1. Senaryo bazinda tespit basarisi

Tablo IKI BLOKTUR. `eslesen` satirlarda uretec ile dedektor AYNI isil
denklemi kullanir; `uyumsuz` satirlarda uretece dedektorun varsaymadigi bir
fizik eklenmistir (bkz. Bolum 1.1). Ikisi ayni sayi degildir ve birlikte
okunmalidir: eslesen blok yontemin TAVANINI, uyumsuz blok SINIRINI olcer.

| Senaryo | Model | Sure (s) | Ornek | Beklenen | Yakalanan | Recall | Yasakli alarm | Kacan |
|---|---|---:|---:|---:|---:|---:|---|---|
| `S0_normal` | eslesen | 168 | 672 | 0 | 0 | - | yok | yok |
| `S1_loose_conn` | eslesen | 720 | 2880 | 4 | 4 | 1.00 | yok | yok |
| `S2_overload` | eslesen | 168 | 672 | 1 | 1 | 1.00 | yok | yok |
| `S3_condense` | eslesen | 168 | 672 | 2 | 2 | 1.00 | yok | yok |
| `S4_arc` | eslesen | 72 | 288 | 1 | 1 | 1.00 | yok | yok |
| `S5_prot_health` | eslesen | 72 | 288 | 1 | 1 | 1.00 | yok | yok |
| `S6_comms_loss` | eslesen | 168 | 648 | 0 | 0 | - | yok | yok (merkezde: ALM-COMMS-LOST) |
| `S7_harmonic` | eslesen | 168 | 672 | 1 | 1 | 1.00 | yok | yok |
| `S8_sensor_fault` | eslesen | 168 | 672 | 1 | 1 | 1.00 | yok | yok |
| `S9_pd_trend` | eslesen | 168 | 672 | 1 | 1 | 1.00 | yok | yok |
| `S10_coupling` | uyumsuz | 720 | 2880 | 4 | 4 | 1.00 | yok | yok |
| `S11_load_tau` | uyumsuz | 720 | 2880 | 4 | 4 | 1.00 | yok | yok |
| `S12_two_pole` | uyumsuz | 720 | 2880 | 4 | 4 | 1.00 | ALM-DQ-DRIFT | yok |
| `S13_sensor_nonlin` | uyumsuz | 720 | 2880 | 4 | 2 | 0.50 | yok | ALM-THR-TERM-ALM, ALM-THR-TERM-WARN |

### 1.1 Model uyumsuzlugu — yontemin siniri

Dedektor (`libs/panoalgo/panoalgo/detect.py`) isil davranisi su ayrik
denklemle kestirir: `dT[k+1] = a*dT[k] + beta*I2[k]`, `K = beta/(1-a)`.
Uretec S0-S9'da AYNI denklemi kullanir. Bu, tespit basarisinin bir kismini
yapisal olarak garanti eder: kestirici kendi ileri modelini ters ceviriyordur.
Asagidaki senaryolar uretece dedektorun VARSAYMADIGI bir fizik ekler ve ayni
tespit boru hattini yeniden olcer. Dedektor DEGISTIRILMEDI — amac onu
guclendirmek degil, sinirini olcmektir.

| Senaryo | Eklenen fizik | Dedektorun varsayimi |
|---|---|---|
| `S10_coupling` | terminal grubu ici isil kuplaj | tek nokta |
| `S11_load_tau` | yuke bagli zaman sabiti | tau sabit |
| `S12_two_pole` | ikinci (yavas) isil kutup | birinci mertebe |
| `S13_sensor_nonlin` | olcum zinciri dogrusalsizligi | dogrusal olcum |

**Olculen.** Eslesen modelde beklenen alarmlarin 12/12'i yakalandi (recall 1.00); dedektorun varsaymadigi fizik eklendiginde 14/16 (recall 0.88).

Uyumsuz blokta kacan kodlar ve hangi senaryoda kactiklari:

- `ALM-THR-TERM-ALM` — `S13_sensor_nonlin`
- `ALM-THR-TERM-WARN` — `S13_sensor_nonlin`

Uyumsuz blokta YASAKLI alarm cikan senaryolar (yanlis teshis):

- `S12_two_pole` — ALM-DQ-DRIFT

**Nasil okunmali.** Eslesen bloktaki sayi yontemin TAVANIDIR ve tek basina
yayimlanirsa yaniltir. Uyumsuz bloktaki sayi ayni algoritmanin, ayni
esiklerle, dedektorun bilmedigi bir fizik altindaki davranisidir. Ikisinin
farki bu calismada olculebilir hale getirilen seydir.

## 2. Sabit 70 K esigi ile karsilastirma

Sabit esik = `thresholds.term_rise_alarm_k` = 70 K (`ALM-THR-TERM-ALM`). Fizik katmani (L1) bu esikten kac saat once uyardi?

| Senaryo | Model | Ilk L1 tespiti | Tetikleyen kod | 70 K ihlali | One alma (saat) | One alma (gun) |
|---|---|---|---|---|---:|---:|
| `S1_loose_conn` | eslesen | 2026-07-13T22:15:00+00:00 | `ALM-TTL-14D` | 2026-07-22T15:15:00+00:00 | 209.0 | 8.7 |
| `S2_overload` | eslesen | 2026-04-08T08:00:00+00:00 | `ALM-DEW-ALM`, `ALM-DEW-WARN` | 2026-04-08T09:15:00+00:00 | 1.2 | 0.1 |
| `S10_coupling` | uyumsuz | 2026-07-13T22:15:00+00:00 | `ALM-TTL-14D` | 2026-07-23T11:00:00+00:00 | 228.8 | 9.5 |
| `S11_load_tau` | uyumsuz | 2026-07-13T22:15:00+00:00 | `ALM-TTL-14D` | 2026-07-22T15:15:00+00:00 | 209.0 | 8.7 |
| `S12_two_pole` | uyumsuz | 2026-07-13T04:00:00+00:00 | `ALM-TTL-14D` | 2026-07-23T15:15:00+00:00 | 251.2 | 10.5 |

**Durustluk kaydi — sayiyi tetikleyen kod.** `ALM-TTL-14D` de bir L1
kodudur (`contracts/alarm-codes.yaml`), dolayisiyla "ilk L1 tespiti" onu da
sayar. Yukaridaki senaryolarda one alma suresini tetikleyen kod TESPIT degil
PROGNOZ: `S1_loose_conn`, `S10_coupling`, `S11_load_tau`, `S12_two_pole`. Ayni prognozun geri
testi Bolum 4'te yayimlaniyor ve **kotu** (koni icinde kalma orani dusuk,
ufuk yok). Yani bu satirlardaki sure, guvenilirligi ayni dosyada olculup
zayif bulunmus bir tahminden geliyor. K indeksi esiginin (`ALM-K-WARN`)
kendi uyari ani ayri bir sayidir ve daha gectir; ikisi karistirilmamalidir.

Bu tabloda YER ALMAYAN uyumsuz senaryolar sabit esigi HIC tetiklemedi (`S13_sensor_nonlin`): sabit esik o
senaryolarda ariziyi tamamen kacirdi, dolayisiyla 'one alma' tanimsizdir.
Bu bir olcum eksigi degil, olcumun kendisidir.

## 3. Yanlis alarm yuku

Etiket penceresi disinda cikan her alarm yanlis alarmdir. Kesintisiz bir aralik
TEK alarm sayilir (operator yuku ornek sayisiyla degil olay sayisiyla olculur).

Sozlesme hedefi: gunde 150 kabul edilebilir, 300 ust sinir (100 pano olceginde).

| Senaryo | Model | Yanlis alarm / 100 pano / gun | Cikan kodlar |
|---|---|---:|---|
| `S0_normal` | eslesen | 71.4 | ALM-DEW-ALM, ALM-DEW-WARN |
| `S1_loose_conn` | eslesen | 23.3 | ALM-PANEL-TEMP |
| `S2_overload` | eslesen | 28.6 | ALM-DEW-ALM, ALM-DEW-WARN |
| `S3_condense` | eslesen | 28.6 | ALM-DEW-ALM, ALM-DEW-WARN |
| `S4_arc` | eslesen | 66.7 | ALM-DEW-ALM, ALM-DEW-WARN |
| `S5_prot_health` | eslesen | 66.7 | ALM-DEW-ALM, ALM-DEW-WARN |
| `S6_comms_loss` | eslesen | 28.6 | ALM-DEW-ALM, ALM-DEW-WARN |
| `S7_harmonic` | eslesen | 28.6 | ALM-DEW-ALM, ALM-DEW-WARN |
| `S8_sensor_fault` | eslesen | 28.6 | ALM-DEW-ALM, ALM-DEW-WARN |
| `S9_pd_trend` | eslesen | 28.6 | ALM-DEW-ALM, ALM-DEW-WARN |
| `S10_coupling` | uyumsuz | 23.3 | ALM-PANEL-TEMP |
| `S11_load_tau` | uyumsuz | 23.3 | ALM-PANEL-TEMP |
| `S12_two_pole` | uyumsuz | 36.7 | ALM-PANEL-TEMP, ALM-TTL-14D |
| `S13_sensor_nonlin` | uyumsuz | 43.3 | ALM-PANEL-TEMP, ALM-TTL-14D |

## 4. Prognoz geri testi

Gercek kalan omur ETIKETTEN turetilir: `RUL* = l0_breach_at - t`. Tahmin,
verideki `min_ttl_h` sutunudur (kenarin o an yayinladigi `ttl_h`). Koni
genisligi alfa = 0.20 (Saxena ve ark. 2010): tahmin
`[(1-alfa)RUL*, (1+alfa)RUL*]` araligindaysa koni icinde sayilir.

| Senaryo | Tahmin | Ilk tahmin (RUL*) | Koni icinde | Ufuk (PH) | CRA | Medyan tahmin/gercek | Hata agirlik merkezi |
|---|---:|---:|---:|---:|---:|---:|---:|
| `S1_loose_conn` | 790 | 211.8 h | 5.2% | yok | -5.12 | 1.69 | 0.41 |
| `S2_overload` | 0 | - | - | - | - | - | - |
| `S10_coupling` | 925 | 231.5 h | 3.5% | yok | -5.29 | 1.69 | 0.43 |
| `S11_load_tau` | 754 | 213.5 h | 5.4% | yok | -5.34 | 1.72 | 0.41 |
| `S12_two_pole` | 1146 | 347.5 h | 5.3% | yok | -5.35 | 1.43 | 0.27 |

**Ufuk (PH)** = tahminin o andan ihlale kadar BIR DAHA konidan cikmadigi ilk an.
**CRA** = ortalama goreli dogruluk, `1 - |RUL* - tahmin| / RUL*`; 1,00 kusursuz,
0 hata gercek omur kadar buyuk, negatif daha da buyuk. **Hata agirlik merkezi**
0'a yakinsa hata pencerenin BASINDA toplanmis, 1'e yakinsa SONUNDA — tek basina
okunmaz, cunku hata her yerde buyukse merkez de ortalarda cikar; koni icinde
kalma orani ile birlikte okunur.

### 4.1 alfa-lambda noktalari

lambda, ilk tahmin ile ihlal ani arasindaki yolun kesridir; lambda = 0,50
"omrun yarisinda tahmin tutuyor muydu" demektir.

| Senaryo | lambda | RUL* (h) | Tahmin (h) | Koni icinde | RA |
|---|---:|---:|---:|---|---:|
| `S1_loose_conn` | 0.25 | 158.8 | 7.0 | hayir | 0.04 |
| `S1_loose_conn` | 0.50 | 106.0 | 3.0 | hayir | 0.03 |
| `S1_loose_conn` | 0.75 | 53.0 | 95.0 | hayir | 0.21 |
| `S10_coupling` | 0.25 | 173.8 | 2.0 | hayir | 0.01 |
| `S10_coupling` | 0.50 | 115.8 | 92.0 | hayir | 0.79 |
| `S10_coupling` | 0.75 | 58.0 | 6.0 | hayir | 0.10 |
| `S11_load_tau` | 0.25 | 160.2 | 10.0 | hayir | 0.06 |
| `S11_load_tau` | 0.50 | 105.0 | 3.0 | hayir | 0.03 |
| `S11_load_tau` | 0.75 | 53.5 | 73.0 | hayir | 0.64 |
| `S12_two_pole` | 0.25 | 260.8 | 689.0 | hayir | -0.64 |
| `S12_two_pole` | 0.50 | 173.8 | 313.0 | hayir | 0.20 |
| `S12_two_pole` | 0.75 | 88.0 | 9.0 | hayir | 0.10 |

### 4.2 Tahmin ne zaman guvenilir hale geldi

Saglikli bir prognozda ariza yaklastikca (kucuk RUL*) koni icinde kalma
orani 1'e dogru gitmelidir.

| Senaryo | Kalan omur araligi | Tahmin | Koni icinde | Medyan tahmin/gercek |
|---|---|---:|---:|---:|
| `S1_loose_conn` | 0-12 h | 48 | 0.0% | 54.22 |
| `S1_loose_conn` | 12-48 h | 116 | 0.0% | 6.53 |
| `S1_loose_conn` | 48-168 h | 455 | 8.6% | 1.20 |
| `S1_loose_conn` | 168-336 h | 171 | 1.2% | 1.67 |
| `S1_loose_conn` | 336 h ustu | 0 | - | - |
| `S10_coupling` | 0-12 h | 48 | 0.0% | 0.56 |
| `S10_coupling` | 12-48 h | 144 | 1.4% | 7.19 |
| `S10_coupling` | 48-168 h | 480 | 5.6% | 1.00 |
| `S10_coupling` | 168-336 h | 253 | 1.2% | 1.69 |
| `S10_coupling` | 336 h ustu | 0 | - | - |
| `S11_load_tau` | 0-12 h | 48 | 0.0% | 50.15 |
| `S11_load_tau` | 12-48 h | 101 | 0.0% | 7.51 |
| `S11_load_tau` | 48-168 h | 423 | 9.5% | 1.36 |
| `S11_load_tau` | 168-336 h | 182 | 0.5% | 1.67 |
| `S11_load_tau` | 336 h ustu | 0 | - | - |
| `S12_two_pole` | 0-12 h | 48 | 0.0% | 26.44 |
| `S12_two_pole` | 12-48 h | 144 | 0.0% | 5.57 |
| `S12_two_pole` | 48-168 h | 471 | 10.8% | 0.94 |
| `S12_two_pole` | 168-336 h | 456 | 2.2% | 1.61 |
| `S12_two_pole` | 336 h ustu | 27 | 0.0% | 1.27 |

### 4.3 Durustluk kayitlari

- **Sonuc 4 olcumden geliyor ama n HALA 1'DIR.** Guven araligi YOKTUR. Bunlarin 1 tanesi eslesen, 3 tanesi uyumsuz modeldendir; hepsi AYNI tohumun AYNI bozulma yorungesidir, yalnizca farkli model dunyalarinda okunmustur. Yani dort sayi birbirinin BAGIMSIZ tekrari degildir ve ortalamalari bir populasyon istatistigi vermez. Bagimsiz tekrar icin coklu tohum gerekir (Yapilacaklar 2.2); bu is onu KAPSAMAZ.
- **`S1_loose_conn`: ihlalden SONRA 587 tahmin daha uretildi.** Sinir zaten asilmisken sistem hala sonlu bir kalan omur soyluyor; bu tahminler geri testin disinda tutuldu (gercek kalan omur negatif, oran tanimsiz).
- **`S2_overload`: sinir asildi ama hic tahmin uretilmedi.** Kalici uyarim ve surekli pozitif egim kosullari saglanmadigi icin `ttl_h` null kaldi; prognoz olcumu bu senaryoda YAPILAMAZ.
- **`S10_coupling`: ihlalden SONRA 526 tahmin daha uretildi.** Sinir zaten asilmisken sistem hala sonlu bir kalan omur soyluyor; bu tahminler geri testin disinda tutuldu (gercek kalan omur negatif, oran tanimsiz).
- **`S11_load_tau`: ihlalden SONRA 578 tahmin daha uretildi.** Sinir zaten asilmisken sistem hala sonlu bir kalan omur soyluyor; bu tahminler geri testin disinda tutuldu (gercek kalan omur negatif, oran tanimsiz).
- **`S12_two_pole`: ihlalden SONRA 680 tahmin daha uretildi.** Sinir zaten asilmisken sistem hala sonlu bir kalan omur soyluyor; bu tahminler geri testin disinda tutuldu (gercek kalan omur negatif, oran tanimsiz).
- **`S8_sensor_fault`: sinir HIC asilmadigi halde 183 tahmin uretildi — bu bir PROGNOZ YANLIS-ALARMIDIR.** Bunlarin 86 tanesi `ALM-TTL-14D` alarmina dondu ve §3'teki yanlis alarm sayaci bunlari GORMEZ: etiket penceresinin icinde cikiyorlar. Nedeni [05-anomali-tespiti.md](05-anomali-tespiti.md) "bilinen sinirlar" bolumundedir.
- **`S13_sensor_nonlin`: sinir HIC asilmadigi halde 1679 tahmin uretildi — bu bir PROGNOZ YANLIS-ALARMIDIR.** Bunlarin 1018 tanesi `ALM-TTL-14D` alarmina dondu ve §3'teki yanlis alarm sayaci bunlari GORMEZ: etiket penceresinin icinde cikiyorlar. Nedeni [05-anomali-tespiti.md](05-anomali-tespiti.md) "bilinen sinirlar" bolumundedir.

## 5. Nasil yeniden uretilir

```bash
python -m panoalgo.scenarios --all --seed 1304 --out data/fixtures
python scripts/validate.py --out docs/12-dogrulama-sonuclari.md
```
