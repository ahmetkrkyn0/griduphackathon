# Sozlesme degisiklik onerisi — esigi olmayan uc alarm kodu

- **Tarih:** 14 Eylul 2026
- **Oneren:** Kisi A (Tuna)
- **Durum:** ONERI — uc onay bekliyor (PLAN.md Bolum B, kural 3)
- **Etkilenen dosya:** `contracts/alarm-codes.yaml` (`thresholds` blogu)
- **Surum etkisi:** `version: 1` -> `version: 2` (kabul edilirse)

## Neden

`alarm-codes.yaml` icindeki 22 alarm kodundan uc tanesinin `threshold:` atfi yok.
Kod yazarken bu bir bosluk yaratiyor: kural 10 "esikler sozlesmeden okunur" diyor,
ama okunacak esik tanimli degil. Su an `libs/panoalgo` bu uc kod icin TURETILMIS
varsayilanlar kullaniyor ve bunu kaynak kodunda acikca isaretliyor. Varsayilanlar
kodda kaldigi surece ayni sayi iki yerde (kenar ve merkez) ayri ayri secilebilir —
kural 10'un onlemek istedigi tam olarak bu.

| Kod | Katman | Durum |
|---|---|---|
| `ALM-DQ-BELOW-AMBIENT` | L-1 | esik yok, olu bant gerekiyor |
| `ALM-NEUTRAL-THD` | L1 | esik yok, iki kosullu kural gerekiyor |
| `ALM-PD-TREND` | L1 | esik yok (OG eklentisi, AG panoda `pd: null`) |

## 1. `ALM-DQ-BELOW-AMBIENT` — olu bant

**Sorun.** Kural "baglanti sicakligi ortamin altinda" seklinde. Olu bant olmadan
uygulanirsa SAGLIKLI pano surekli SYS alarmi uretir: hafif yuklu noktalar (ozellikle
`GIRIS_N`) fiziksel olarak ortam sicakliginda oturur, uzerine rapor 15.2'deki
sigma ~0,2 K olcum gurultusu binince `t_c` ortamin bir miktar altini olcer.
Bu gercek sensor davranisidir, ariza degil.

**Olculen kanit.** TA1 ureteci saglikli panoda (`S0`) `GIRIS_N` icin `dt_c` degerini
0,17 K civarinda uretiyor; sigma 0,2 K ile isaret degistirme olasiligi yuksek.

**Oneri.**

```yaml
  # L-1 veri kalitesi
  dq_below_ambient_deadband_k: 1.0   # 3 sigma (olcum gurultusu 0,2 K) uzeri, yuvarlak
```

Kural: `t_c < T_ortam - dq_below_ambient_deadband_k`.

## 2. `ALM-NEUTRAL-THD` — iki kosullu kural

**Sorun.** Metin "Notr akimi ve akim THD birlikte artti" diyor; "birlikte artti"nin
sayisal karsiligi yok. Tek basina yuksek THD (dogrusal olmayan yuk) veya tek basina
yuksek notr akimi (dengesizlik) ariza degildir — rapor 6.5 L1-7 ikisinin BIRLIKTE
artmasini ariza belirtisi sayiyor.

**Oneri.**

```yaml
  # L1 harmonik kaynakli notr isinmasi (iki kosul BIRLIKTE saglanmali)
  neutral_current_ratio_warn: 0.30   # i_n / ortalama faz akimi
  neutral_thd_warn_pct: 15.0         # ortalama akim THD (%)
```

Kural: `i_n / ort(i_ph) > neutral_current_ratio_warn` **VE**
`ort(thd_i) > neutral_thd_warn_pct`.

Sayilarin gerekcesi: rapor 15.2 harmonik senaryosunu "akim THD %25+" olarak tarif
ediyor; uyari esigi bunun altinda, %15'te secildi. Notr orani icin rapor sayi
vermiyor — dengeli ve harmoniksiz bir panoda `i_n / ort(i_ph)` 0,10'un altinda kalir,
0,30 belirgin bir artisi isaret eder. **Bu iki sayi da turetilmistir**, tartisilabilir.

## 3. `ALM-PD-TREND` — kapsam disi birakilmasi onerilir

**Sorun.** PD yalnizca OG hucre/trafo icin anlamli; rapor 3.7'ye gore 400 V AG panoda
Paschen minimumunun (~327 V) altinda kalindigi icin PD BEKLENMEZ ve telemetri
semasinda `pd` blogu AG panoda `null`.

**Oneri.** Esik eklemek yerine alarm satirina kapsam notu dusulmesi:

```yaml
  - code: ALM-PD-TREND
    ...
    scope: "OG eklentisi; AG panoda pd: null oldugu icin degerlendirilmez"
```

MoSCoW'da PD zaten **Could** kumesinde (PLAN.md). Esik, PD donanimi kapsama girerse
(Faz 3 sonrasi) ayri bir degisiklik dosyasiyla tanimlanmali.

## Kabul edilmezse ne olur

`libs/panoalgo` calismaya devam eder; turetilmis varsayilanlar
`panoalgo/quality.py` (`DEFAULT_BELOW_AMBIENT_DEADBAND_K`) ve `panoalgo/fusion.py`
icinde isaretli olarak kalir. Risk sudur: merkez tarafi ayni kurali kendi sayisiyla
uygularsa kenar ile merkez farkli karar verir ve demo sirasinda bir alarm bir yerde
gorunup digerinde gorunmez.

## Onaylar

- [ ] Kisi A (Tuna)
- [ ] Kisi B (Ahmet)
- [ ] Kisi C (Berke)
