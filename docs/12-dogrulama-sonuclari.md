# 12. Dogrulama Sonuclari

> Bu dosya ELLE YAZILMAZ. `python scripts/validate.py --out docs/12-dogrulama-sonuclari.md`
> komutu `data/fixtures/` altindaki seed'li senaryolari yeniden olcer ve bu tabloyu
> uretir (PLAN.md T4.2). Asagidaki her sayi tekrar uretilebilir.

Uretim zamani: 2026-09-19T02:03:28+03:00

## 1. Senaryo bazinda tespit basarisi

| Senaryo | Sure (s) | Ornek | Beklenen | Yakalanan | Recall | Yasakli alarm | Kacan |
|---|---:|---:|---:|---:|---:|---|---|
| `S0_normal` | 168 | 672 | 0 | 0 | - | yok | yok |
| `S1_loose_conn` | 720 | 2880 | 4 | 4 | 1.00 | yok | yok |
| `S2_overload` | 168 | 672 | 1 | 1 | 1.00 | yok | yok |
| `S3_condense` | 168 | 672 | 2 | 2 | 1.00 | yok | yok |
| `S4_arc` | 72 | 288 | 1 | 1 | 1.00 | yok | yok |
| `S5_prot_health` | 72 | 288 | 1 | 1 | 1.00 | yok | yok |
| `S6_comms_loss` | 168 | 648 | 0 | 0 | - | yok | yok (merkezde: ALM-COMMS-LOST) |
| `S7_harmonic` | 168 | 672 | 1 | 1 | 1.00 | yok | yok |
| `S8_sensor_fault` | 168 | 672 | 1 | 1 | 1.00 | yok | yok |
| `S9_pd_trend` | 168 | 672 | 1 | 1 | 1.00 | yok | yok |

## 2. Sabit 70 K esigi ile karsilastirma

Sabit esik = `thresholds.term_rise_alarm_k` = 70 K (`ALM-THR-TERM-ALM`). Fizik katmani (L1) bu esikten kac saat once uyardi?

| Senaryo | Ilk L1 tespiti | 70 K ihlali | One alma (saat) | One alma (gun) |
|---|---|---|---:|---:|
| `S1_loose_conn` | 2026-07-13T22:15:00+00:00 | 2026-07-22T15:15:00+00:00 | 209.0 | 8.7 |
| `S2_overload` | 2026-04-08T08:00:00+00:00 | 2026-04-08T09:15:00+00:00 | 1.2 | 0.1 |

## 3. Yanlis alarm yuku

Etiket penceresi disinda cikan her alarm yanlis alarmdir. Kesintisiz bir aralik
TEK alarm sayilir (operator yuku ornek sayisiyla degil olay sayisiyla olculur).

Sozlesme hedefi: gunde 150 kabul edilebilir, 300 ust sinir (100 pano olceginde).

| Senaryo | Yanlis alarm / 100 pano / gun | Cikan kodlar |
|---|---:|---|
| `S0_normal` | 71.4 | ALM-DEW-ALM, ALM-DEW-WARN |
| `S1_loose_conn` | 23.3 | ALM-PANEL-TEMP |
| `S2_overload` | 28.6 | ALM-DEW-ALM, ALM-DEW-WARN |
| `S3_condense` | 28.6 | ALM-DEW-ALM, ALM-DEW-WARN |
| `S4_arc` | 66.7 | ALM-DEW-ALM, ALM-DEW-WARN |
| `S5_prot_health` | 66.7 | ALM-DEW-ALM, ALM-DEW-WARN |
| `S6_comms_loss` | 28.6 | ALM-DEW-ALM, ALM-DEW-WARN |
| `S7_harmonic` | 28.6 | ALM-DEW-ALM, ALM-DEW-WARN |
| `S8_sensor_fault` | 28.6 | ALM-DEW-ALM, ALM-DEW-WARN |
| `S9_pd_trend` | 28.6 | ALM-DEW-ALM, ALM-DEW-WARN |

## 4. Prognoz geri testi

Gercek kalan omur ETIKETTEN turetilir: `RUL* = l0_breach_at - t`. Tahmin,
verideki `min_ttl_h` sutunudur (kenarin o an yayinladigi `ttl_h`). Koni
genisligi alfa = 0.20 (Saxena ve ark. 2010): tahmin
`[(1-alfa)RUL*, (1+alfa)RUL*]` araligindaysa koni icinde sayilir.

| Senaryo | Tahmin | Ilk tahmin (RUL*) | Koni icinde | Ufuk (PH) | CRA | Medyan tahmin/gercek | Hata agirlik merkezi |
|---|---:|---:|---:|---:|---:|---:|---:|
| `S1_loose_conn` | 790 | 211.8 h | 5.2% | yok | -5.12 | 1.69 | 0.41 |
| `S2_overload` | 0 | - | - | - | - | - | - |

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

### 4.3 Durustluk kayitlari

- **Sonuc 1 yorungeden geliyor (n = 1).** Guven araligi YOKTUR; tek bir seed'li senaryonun tek bir bozulma yorungesi olculmustur. Yukaridaki yuzdeler bu yorungenin ozellikleridir, populasyon istatistigi degildir.
- **`S1_loose_conn`: ihlalden SONRA 587 tahmin daha uretildi.** Sinir zaten asilmisken sistem hala sonlu bir kalan omur soyluyor; bu tahminler geri testin disinda tutuldu (gercek kalan omur negatif, oran tanimsiz).
- **`S2_overload`: sinir asildi ama hic tahmin uretilmedi.** Kalici uyarim ve surekli pozitif egim kosullari saglanmadigi icin `ttl_h` null kaldi; prognoz olcumu bu senaryoda YAPILAMAZ.
- **`S8_sensor_fault`: sinir HIC asilmadigi halde 99 tahmin uretildi — bu bir PROGNOZ YANLIS-ALARMIDIR.** Bunlarin 89 tanesi `ALM-TTL-14D` alarmina dondu ve §3'teki yanlis alarm sayaci bunlari GORMEZ: etiket penceresinin icinde cikiyorlar. Nedeni [05-anomali-tespiti.md](05-anomali-tespiti.md) "bilinen sinirlar" bolumundedir.

## 5. Nasil yeniden uretilir

```bash
python -m panoalgo.scenarios --all --seed 1304 --out data/fixtures
python scripts/validate.py --out docs/12-dogrulama-sonuclari.md
```
