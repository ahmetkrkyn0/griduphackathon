# Sozlesme degisiklik onerisi — esigi olmayan uc alarm kodu + uyarim olcutu

- **Tarih:** 14 Eylul 2026
- **Oneren:** Kisi A (Tuna)
- **Durum:** **KABUL EDILDI ve UYGULANDI — 18 Eylul 2026** (asagida "Karar" bolumu)
- **Etkilenen dosya:** `contracts/alarm-codes.yaml` (`thresholds` blogu)
- **Surum etkisi:** `version: 1` -> `version: 2` — **uygulandi**

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
| `excitation_min_var_i2` | RLS | esik var ama OLCEGE BAGIMLI — notr nokta hicbir zaman gecemiyor |

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

## 4. `excitation_min_var_i2` — mutlak esik olcege bagimli

**Sorun.** Kalici uyarim kosulu su an MUTLAK bir esiktir: `var(I^2) >= 1.0e7`.
Ama `I^2`'nin buyuklugu iletkenin tasidigi akima baglidir. Notr iletken faz akiminin
yaklasik alti'da birini tasir; `I^2` ~36 kat, `var(I^2)` ~1000 kat kucuk olur.
Sonuc: `GIRIS_N` noktasi yuk gun boyunca fazlarla AYNI GORELI oranda degisse bile
hicbir zaman "uyarilmis" sayilmaz, K kestirimi hic guncellenmez ve o nokta izlemesiz
kalir. Harmonik kaynakli notr isinmasi (`ALM-NEUTRAL-THD`, `HYP-HARMONIC`) tam da bu
noktada aranan bir ariza oldugu icin bu bosluk onemlidir.

**Olculen kanit.** TA1 ureteci, karma profil, 25 saat, 30 ornek (30 dk) pencere:

| Nokta | `var(I^2)` medyan | degisim katsayisi (cv) | 1.0e7 esigini geciyor mu |
|---|---|---|---|
| `GIRIS_L1` | 1,67e9 | 0,022 | evet |
| `GIRIS_N` | 1,24e6 | 0,028 | **hayir** |

Iki nokta ayni goreli yuk degisimini gormesine ragmen (cv 0,022 ve 0,028) mutlak
esik yalnizca fazi geciriyor. Yani esik "uyarim var mi" sorusunu degil, "iletken
kalin mi" sorusunu olcuyor.

**Oneri.** Mutlak esigi KALDIRMADAN, olcekten bagimsiz bir ikinci olcut eklensin;
ikisinden biri saglanirsa uyarim var sayilsin.

```yaml
  # RLS / kestirim
  excitation_min_cv_i2: 0.02   # var(I^2) degisim katsayisi; olcege bagimsiz olcut
```

Kural: `var(I^2) >= excitation_min_var_i2` **VEYA**
`std(I^2) / ort(I^2) >= excitation_min_cv_i2`.

0,02 degeri yukaridaki olcumden secildi: hem fazin hem notrun 30 dakikalik normal
yuk dalgalanmasini geciriyor, sabit yuk (cv = 0) kosulunu ise gecirmiyor —
PLAN.md TA2 Adim 1'deki `test_k_index_not_updated_without_excitation` testi gecerli
kalir. **Bu sayi turetilmistir.**

## Kabul edilmezse ne olur

`libs/panoalgo` calismaya devam eder; turetilmis varsayilanlar
`panoalgo/quality.py` (`DEFAULT_BELOW_AMBIENT_DEADBAND_K`), `panoalgo/detect.py`
(`DEFAULT_EXCITATION_MIN_CV`) ve `panoalgo/fusion.py` icinde isaretli olarak kalir. Risk sudur: merkez tarafi ayni kurali kendi sayisiyla
uygularsa kenar ile merkez farkli karar verir ve demo sirasinda bir alarm bir yerde
gorunup digerinde gorunmez.

## 15 Eylul guncellemesi — riskin buyuklugu OLCULDU, karar kolaylasti

Onerinin "Kabul edilmezse ne olur" bolumundeki risk suydu: *"merkez tarafi ayni kurali kendi
sayisiyla uygularsa kenar ile merkez farkli karar verir"*. Birlesmeden sonra bu risk BUYUK
OLCUDE ORTADAN KALKTI ve sebebi olculebilir:

- Merkez dedektor artik `panoalgo.central.CentralDetector` uzerinden **`panoalgo.limits.evaluate`
  cagiriyor** (backend/app/main.py, TB2 Adim 4 — 15 Eylul'de baglandi). Yani kenarin kullandigi
  KODUN AYNISI merkezde de kosuyor; turetilmis varsayilanlar iki yerde ayri ayri secilemez.
- Backend'in `risk.py:_neutral_harmonics` fonksiyonu **karar VERMEZ**, yalnizca "Neden?"
  bolumunun sinyallerini toplar. Esik karsilastirmasi tek yerdedir (`limits.py:228-231`).

**Geriye kalan risk ve karar:** sayilar sozlesmede degil KODDA duruyor. Bu, kural 10'un
("esikler sozlesmeden okunur") ihlalidir ve juri `contracts/`'a bakip bu uc kodun esigini
bulamaz. Teknik risk dusuk, **seffaflik riski surüyor**.

**Oneri (A):** 1, 2 ve 4 numarali maddeler kabul edilsin — uc de `thresholds` blogunda tek
satirdir, geri uyumludur (kod zaten `thresholds.get(...)` ile once sozlesmeye bakiyor, sonra
varsayilana duser; yani kabul edilirse **kod degisikligi gerekmez**). 3 numarali madde (PD kapsam
notu) da yalnizca aciklama ekler. Reddedilirse §"Kabul edilmezse ne olur" gecerlidir ve
`docs/17` §6'ya "esikler kodda" satiri eklenmelidir.

## Onaylar

- [x] Kisi A (Tuna)
- [x] Kisi B (Ahmet)
- [x] Kisi C (Berke)

---

## Karar — 18 Eylul 2026: dort maddenin dordu de uygulandi

Ozellik dondurma (GK2) 17 Eylul 23:59'da doldu; sozlesme artik degistirilebilir.
Oneri `alarm-codes.yaml` **v1 -> v2** ile uygulandi.

### Ne uygulandi

| # | Madde | Sonuc |
|---|---|---|
| 1 | `dq_below_ambient_deadband_k: 1.0` | eklendi; `ALM-DQ-BELOW-AMBIENT` artik bu esige atif yapiyor |
| 2 | `neutral_current_ratio_warn: 0.30` + `neutral_thd_warn_pct: 15.0` | eklendi; `ALM-NEUTRAL-THD` **iki esige birden** atif yapiyor |
| 3 | `ALM-PD-TREND` kapsam notu | **esik eklenmedi** (onerildigi gibi); yerine `scope:` satiri dusuldu |
| 4 | `excitation_min_cv_i2: 0.02` | eklendi |

### Kod degisikligi gerekmedi — dogrulandi

Onerinin "kabul edilirse kod degisikligi gerekmez" iddiasi depoya karsi sinandi: dort
anahtarin dordu de zaten `thresholds.get(ANAHTAR, VARSAYILAN)` ile okunuyordu ve
sozlesmeye yazilan degerler turetilmis varsayilanlarla **birebir ayni**:

| Anahtar | Kodda | Sozlesmeye yazilan |
|---|---|---|
| `dq_below_ambient_deadband_k` | `quality.py` `DEFAULT_BELOW_AMBIENT_DEADBAND_K = 1.0` | 1.0 |
| `neutral_current_ratio_warn` | `limits.py` `DEFAULT_NEUTRAL_RATIO_WARN = 0.30` | 0.30 |
| `neutral_thd_warn_pct` | `limits.py` `DEFAULT_NEUTRAL_THD_WARN_PCT = 15.0` | 15.0 |
| `excitation_min_cv_i2` | `detect.py` `DEFAULT_EXCITATION_MIN_CV = 0.02` | 0.02 |

Yani bu degisiklik **davranisi degistirmez**, sayilarin *nerede yasadigini* degistirir:
kodun icinden sozlesmeye tasir (PLAN.md kural 10). Varsayilanlar kodda kalmaya devam
ediyor — sozlesme okunamadigi durumda (or. eski bir sozlesme surumu) hala geri duserler.

### Sozlesme semasinda tek genisletme

`ALM-NEUTRAL-THD` gercekten **iki kosullu** bir kuraldir; tek bir `threshold:` dizesi
ikisini birden ifade edemiyordu. Bu yuzden alan artik **dize veya liste** kabul ediyor:

- `scripts/check_contracts.py` listenin **her uyesini ayri ayri** denetliyor — aksi
  halde ikinci esik sozlesmede gorunur, hicbir yerde dogrulanmazdi;
- `scripts/gen_alarm_doc.py` ikisini de `docs/06` katalogunda gosteriyor.

### Neyin kapandigini ve neyin kapanmadigini

**Kapandi:** `docs/17` §6 madde 14'teki seffaflik riski — juri artik `contracts/`'a bakip
bu iki kodun esigini bulabiliyor. Kenar ile merkezin ayni kurali farkli sayiyla uygulama
riski de sozlesme tek kaynak oldugu icin kalmadi.

**Kapanmadi:** bu sayilarin ucu (`1.0`, `0.30`, `15.0`) **turetilmistir, olculmemistir** ve
sozlesmedeki yorumlarinda boyle yaziyor. Yalnizca `excitation_min_cv_i2 = 0.02` olculmus
bir taramadan gelir (yukaridaki §4 tablosu). `ALM-PD-TREND` esiksiz kalmaya devam ediyor.
