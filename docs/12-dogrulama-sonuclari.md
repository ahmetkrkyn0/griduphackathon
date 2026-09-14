# 12. Dogrulama Sonuclari

> Bu dosya ELLE YAZILMAZ. `python scripts/validate.py --out docs/12-dogrulama-sonuclari.md`
> komutu `data/fixtures/` altindaki seed'li senaryolari yeniden olcer ve bu tabloyu
> uretir (PLAN.md T4.2). Asagidaki her sayi tekrar uretilebilir.

Uretim zamani: 2026-09-14T17:29:53+03:00

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

## 4. Nasil yeniden uretilir

```bash
python -m panoalgo.scenarios --all --seed 1304 --out data/fixtures
python scripts/validate.py --out docs/12-dogrulama-sonuclari.md
```
