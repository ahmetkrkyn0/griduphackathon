# 21 — P1: Tahmin Geçerliliği Tamamlandı Raporu

> Kaynak görev: [INOVASYON-UYGULAMA-PLANI.md](../INOVASYON-UYGULAMA-PLANI.md) §4 (P1 — Tahmin geçerliliği ve
> kanıt kartı), uygulama planı [docs/superpowers/plans/2026-09-18-p1-tahmin-gecerliligi.md](superpowers/plans/2026-09-18-p1-tahmin-gecerliligi.md).
> Bu dosya P1'in 8 görevinin (Task 1-8) neyi değiştirdiğini, plan §4'teki 5 kabul senaryosunun
> hangi testte kanıtlandığını ve P1'in kapatamadığı/kısmen kapattığı bilinen sınırları (S8 ve
> alarm kartı raise-time snapshot'ı) tek yerde toplar. **19 Eylül 2026** tarihinde üretildi, commit
> aralığı `f1f01b5..239cd3e` (dal `berke/upgrade`).
>
> **Kapsam notu:** Bu bir tamamlanma raporudur, plan belgesinin kendisi değildir. Aşağıdaki tüm
> dosya:satır referansları bu raporun yazıldığı anda gerçek kodla karşılaştırılarak doğrulandı.

## 1. Kapsam ve özet

P1, tahmin geçerliliği (`gecerlilik`) kavramını uçtan uca taşıdı: panoalgo'da zaten var olan
alanlardan (`q`, `excited`, `ttl_h`, `state`, `health.baseline_day`) TEK bir türetilmiş değer
hesaplanıyor, bu değer backend'in hem nokta görünümünde (`GET /api/v1/panels/{id}` → `points[]`)
hem de nokta-bağlı alarm nedenlerinde (`active_alarms[].reason.gecerlilik`) aynı fonksiyondan
geliyor, ve frontend bunu hem alarm kartında ("Ne kadar acil?") hem de ölçüm tablosunda
("Geçerlilik" sütunu) gösteriyor. `contracts/openapi.yaml` **DONDU** kaldı — yeni alan sözleşmeye
eklenmedi, açık nesnelere (`ConnPoint`, `AlarmReason`) turetilmiş bir alan olarak eklendi.

Ayrıca P1, S8 (sensör arızası) bilinen sınırıyla ilgili **gerçek ama dar kapsamlı** bir düzeltme
yaptı: artık kalite kuralları tarafından işaretlenmiş bir nokta hiçbir zaman yanıltıcı bir kalan-
ömür sayısı göstermiyor. Bu, S8'in kendi sayısını değiştirmedi (bkz. §4) — ölçülüp dürüstçe
belgelendi, uydurulmadı.

## 2. Görev bazında ne yapıldı

### Task 1 — kalite bayrağı set olan noktada `ttl_h` artık asla canlı değil

`libs/panoalgo/panoalgo/edge.py`: yeni `EdgePipeline._suppress_ttl_when_quality_suspect()` metodu
(satır 220-233), `process()` içinde `_update_quality()`'den hemen sonra, alarm/risk hesabından
önce çağrılır (satır 109-111). Herhangi bir noktanın `q != 0` ise (`ALM-DQ-FROZEN`, `ALM-DQ-JUMP`,
`ALM-DQ-BELOW-AMBIENT`, `ALM-NODE-LOST` kurallarından biri tarafından işaretlenmişse) `ttl_h`
alanını `None`'a çeker.

Test: `libs/panoalgo/tests/test_edge.py::test_ttl_is_suppressed_when_the_point_quality_is_suspect`
(satır 104-120). `time_to_limit()` doğrudan çağrılarak (`test_detect.py`'de zaten kanıtlı bir
girdiyle) gerçek, pozitif bir ön-koşul `ttl_h` üretilir; sonra aynı fonksiyon `q=0` iken dokunmadığı,
`q=1` iken `None`'a çektiği ayrı ayrı doğrulanır. İncelemede monkeypatch ile üretim kodu
nötrleştirilip testin gerçekten kırıldığı, yani ayırt edici olduğu ayrıca kanıtlandı.

Commit'ler: `1d2b9b2` (ilk uygulama), `ac00b60` (kapsam netleştirme), `0528d1b` (testin
senaryo-tabanlı ilk hâli — incelemede önkoşulu güvenilir sağlamadığı, yani ispatsız olduğu
ortaya çıktı — `test_detect.py`'de zaten kanıtlı `time_to_limit()` çağrısına dayanan
deterministik bir teste dönüştürülmesi; bu, S8'in kendisiyle ilgisiz, ayrı bir test-kalitesi
düzeltmesidir).

*Düzeltildi (final whole-branch review sonrası, commit `b80ef2c`):* `edge.py:223`'teki yazım
hatası ("hiclbir"), `:226`'daki tek Türkçe karakter (`içerir`), `:227`'deki geçersiz kelime
("kucuklenmez") ve `:229`'daki bozuk parantez ifadesi ("(s/zamaninda implemented degil)")
temizlendi; dosyanın geri kalanıyla aynı ASCII harf-çevirisine (`siniri`, `surunen` gibi) uyumlu.

### Task 2 — nokta geçerliliğinin backend'de türetilmesi

`backend/app/api/views.py`: yeni `point_validity(point, state, comms_ok, thresholds, baseline_day)`
fonksiyonu (satır 79-109) altı olası değerden birini döner: `veri_yetersiz` (comms koptu ya da
uyarım yok), `sensor_supheli` (q != 0), `sinir_asildi` (alarm/critical), `ogreniyor` (taban
öğrenme sürüyor), `model_kapsami_disi` (ttl_h yok), `tahmin_gecerli`. Öncelik sırası fonksiyonun
docstring'inde açık: comms kaybı > sensör şüphesi > sınır aşımı > öğrenme > uyarım yokluğu > model
kapsamı dışı > geçerli. `point_view()` (satır 165-180) bu değeri `"gecerlilik"` anahtarıyla nokta
görünümüne ekler (satır 179).

Testler: `backend/tests/test_api_panels.py::test_point_validity_prioritises_sensor_suspicion_over_everything_else`
(6 parametreli örnek, satır 236-260) ve `test_panel_detail_points_carry_labels_states_and_measurements`
(satır 169-205, gerçek bir ALM-K-WARN ve gerçek bir ALM-DQ örneğinde tam nokta gövdesini kontrol eder).

Commit: `58f71d1`.

*Bilinen küçük boşluk (belgeleniyor, düzeltilmedi):* parametreli testte `comms_ok` hiç `False`
yapılmıyor; en yüksek öncelikli "comms koptu → veri_yetersiz" dalı yalnızca Task 4'ün
`test_data_loss_shows_last_seen_not_a_live_looking_value` testinde ayrıca kanıtlanıyor (bkz. §3).

### Task 3 — alarm nedeninde aynı geçerlilik

`backend/app/risk.py`: `RiskEngine._condition()` (satır 134-157), `point is not None` olduğunda
(satır 151-154) `point_state()` ve `point_validity()`'yi **aynı fonksiyonlardan** tekrar çağırıp
sonucu `reason["gecerlilik"]`'e yazar. Panel-geneli koşullarda (`point=None`, örn.
`ALM-DEW-WARN`) bu alan hiç eklenmiyor — nokta kavramı olmayan bir alarmda geçerlilik uydurulmuyor.

Testler: `backend/tests/test_risk.py::test_condition_reason_carries_point_gecerlilik_alongside_verify`
(satır 378-385) ve `test_panel_wide_conditions_do_not_carry_gecerlilik` (satır 388-395).

Commit'ler: `7c2582e`, `7334dde` (tek karakterlik ASCII düzeltmesi).

### Task 4 — 5 kabul senaryosunun uçtan uca kodu

Yeni dosya `backend/tests/test_p1_validity_scenarios.py` (108 satır): plan §4'teki "Kabul
senaryoları" tablosunun her satırı için, gerçek bir telemetri yükünü `IngestPipeline`'a yazıp
`GET /api/v1/panels/{id}` üzerinden okuyan bir test. Bkz. §3 — bu dosya aynı zamanda P1'in
"Teslim kapısı" kanıtıdır.

Commit: `5b3d2a4`.

### Task 5 — frontend tipi ve Türkçe sözlük

`frontend/src/api/types.ts`: `Gecerlilik` birleşim tipi (satır 12, 6 değer), `ConnPoint.gecerlilik`
(satır 45) ve `AlarmReason.gecerlilik` (satır 119) alanlarına eklendi — `contracts/openapi.yaml`
dondurulmuş olduğu için `AlarmVerify` ile aynı desende, açık nesnenin içine.

`frontend/src/lib/labels.ts`: `GECERLILIK_TEXT` (satır 23-30, her değerin Türkçe adı),
`GECERLILIK_HINT` (satır 32-38, `tahmin_gecerli` dışındaki her değer için açıklayıcı cümle) ve
`validityHint(gecerlilik, prio)` yardımcı fonksiyonu (satır 42-45): geçerlilik "geçerli" değilse
nedeni açıklayan cümleyi, aksi hâlde önceliğe göre eski davranışı ("Hemen müdahale gerekir." /
"Süre tahmini yok.") döner.

Test: `frontend/src/lib/labels.test.ts:24-27` — 6 değerin tamamının `GECERLILIK_TEXT`'te karşılığı
olduğunu kontrol eder.

Commit: `687aef0`.

*Bilinen küçük boşluk (belgeleniyor, düzeltilmedi):* bu testteki 6 değerlik liste elle yazılmış;
kardeş `ALARM_TEXT`/`HYP_TEXT` testleri gibi `contracts/alarm-codes.yaml`'dan türetilmiyor, çünkü
`Gecerlilik`'in sözleşmede bir YAML kaynağı yok. Zamanla tip ile test birbirinden kayabilir.

### Task 6 — alarm kartında geçerlilik-farkında mesaj

`frontend/src/components/AlarmNedeni.tsx`: `gecerlilik = alarm.reason?.gecerlilik` (satır 54);
"Ne kadar acil?" bölümü (satır 118-136) `ttl` varsa sayıyı gösteriyor, yoksa artık
`validityHint(gecerlilik, alarm.prio)` çağırıyor (satır 127) — eskiden burada yalnızca öncelik
bazlı sabit bir cümle vardı.

Commit: `70d3e3e`. Kontrolcü tarafından tarayıcıda görsel olarak doğrulandı (bkz. plan ilerleme
kaydı): `sensor_supheli` bir alarmda "Bu ölçümde veri kalitesi şüpheli; kalan ömür tahmini
gösterilmiyor." metni gerçekten göründü.

### Task 7 — ölçüm tablosunda Geçerlilik sütunu

`frontend/src/pages/PanoDetay.tsx`: `OlcumTablosu` bileşenine yeni "Geçerlilik" sütun başlığı
(satır 595) ve her satırda `p.gecerlilik` varsa `GECERLILIK_TEXT[p.gecerlilik]`, yoksa "–"
gösteren hücre (satır 624-626).

Commit: `80611ab`. Kontrolcü tarafından tarayıcıda görsel olarak doğrulandı: DSYA-3 L2 satırında
"Sensör şüpheli", diğer (geçerlilik hesaplanmamış) satırlarda "–" gösterdiği doğrulandı.

### Task 8 — SCADA ve Telegram'da tutarlılık kilidi

`backend/tests/test_scada_encoder.py::test_ttl_suppressed_for_quality_encodes_as_na` (satır 232):
Task 1'in ürettiği durumu (worst-point'in `q`'su set, `ttl_h`'i ve panel-geneli `risk.ttl_h`'i
`None`) elle kurup `risk.ttl_hours` register'ının SCADA sözleşmesindeki "yok" sentinel'ine
(`NAU16`, uint16 0xFFFF) kodlandığını kilitler — eski/sahte bir sayı olarak DEĞİL.

`backend/tests/test_telegram.py::test_telegram_omits_rul_line_when_ttl_h_is_none` (satır 90):
`ttl_h=None` olan gerçek bir `Alarm` ile Telegram mesajının "Kalan Ömür (RUL)" satırını hiç
basmadığını kilitler (`templates.py`'deki var olan `if ttl_h is not None` korumasının davranışı).

Commit: `239cd3e`.

*Açık kalan takip — bkz. §6.* Ayrıca küçük bir netlik notu: `test_ttl_suppressed_for_quality_encodes_as_na`
içindeki `tel_payload["t_conn"][1]["q"] = 1` ve `["ttl_h"] = None` satırları, yapılan asıl
iddia (`risk.ttl_hours` register'ı) için nedensel olarak etkisizdir — onu yalnızca üçüncü satır
(`tel_payload["risk"]["ttl_h"] = None`) sürüklüyor. Test doğru sonucu doğru şekilde kilitliyor;
yalnızca yorum, nokta-seviyesi alanların da bu register'a girdi olduğu izlenimini verebilir.

## 3. Kabul senaryoları → test eşleşmesi (Teslim kapısı kanıtı)

Plan §4'ün "Teslim kapısı" şartı: *"bu senaryolar geçmeden yeni demo sürümüne alınmaz."* Beşi de
`backend/tests/test_p1_validity_scenarios.py` içinde, plandaki sıraya birebir uyan tek bir testle
kanıtlanıyor:

| # | Durum (plan §4) | Beklenen davranış (plan §4) | Test | Doğrulanan |
|---|---|---|---|---|
| 1 | Sağlıklı ölçüm, öğrenme tamamlanmamış | Öğrenme bilgisi; doğrulanmamış süre tahmini yok | `test_healthy_measurement_still_learning_shows_no_unverified_duration` (satır 45-53) | `gecerlilik == "ogreniyor"`, `ttl_h is None` |
| 2 | Gevşek bağlantı belirtisi, yeterli veri | Erken uyarı korunur, dayanaklar görünür | `test_loose_connection_signature_keeps_early_warning_with_evidence` (satır 56-64) | `state == "warn"`, `gecerlilik == "tahmin_gecerli"`, `ttl_h == 150.5` (sayı hâlâ görünür) |
| 3 | Sensör sapması | Şüphe nedeni ve geçersiz tahmin durumu; yanıltıcı geri sayım yok | `test_sensor_drift_shows_suspicion_and_no_misleading_countdown` (satır 67-81) | `gecerlilik == "sensor_supheli"`, `ttl_h is None` (canlı görünümler için — nokta şüpheli olmadan ÖNCE açılmış, hâlâ açık bir alarm kartı için geçerli değildir, bkz. §5) |
| 4 | Veri kopması | Son veri zamanı ve izleme kaybı; son değer canlı gibi görünmez | `test_data_loss_shows_last_seen_not_a_live_looking_value` (satır 84-98) | `state == "stale"`, `gecerlilik == "veri_yetersiz"` (comms `store.set_last_rx` ile koparılarak, `ts` alanı değil) |
| 5 | Sınır aşılmış | "Sınır aşıldı"; kritik ölçüm alarmı bağımsız kalır | `test_breached_limit_keeps_critical_alarm_independent_of_validity` (satır 101-108) | `state == "alarm"`, `gecerlilik == "sinir_asildi"` |

Satır 3'ün testi kasıtlı olarak `IngestPipeline`'a doğrudan yazıyor (`EdgePipeline`'ı hiç
çalıştırmıyor); Task 1'in kendi davranışı (q set olunca `ttl_h`'i gerçekten `None`'a çekmesi)
ayrıca ve doğrudan `test_edge.py::test_ttl_is_suppressed_when_the_point_quality_is_suspect`'te
kanıtlanıyor (bkz. §2, Task 1). İki test farklı katmanları doğruluyor, birbirini tekrar etmiyor.

Beşi de bu raporun §7'sindeki `pytest -q` koşusunun içinde, tamamı **PASS**.

## 4. Bilinen sınır: S8 (sürüklenen sensör) — dürüst sonuç

**Sayı değişmedi.** [docs/12-dogrulama-sonuclari.md](12-dogrulama-sonuclari.md) §4.3'teki S8
prognoz yanlış-alarmı hâlâ **183 tahmin, 86'sı `ALM-TTL-14D`**. Bu rapor için docs/12 19 Eylül 2026'da
yeniden üretildi (`python scripts/validate.py --out docs/12-dogrulama-sonuclari.md`); `git diff`
yalnızca "Üretim zamanı" satırını değiştirdi, S8 dâhil **hiçbir sayı bir birim bile kımıldamadı**.

> **20 Eylül notu — sayılar güncellendi.** Bu bölüm yazıldığında dalın üzerindeki `docs/12`
> **99 tahmin / 89** basıyordu ve yukarıdaki cümle o an doğruydu. `main`'den gelen **F-31**
> (düğüm kütüğü, `102850c`, 18 Eylül) birleştirildikten sonra aynı betik **183 / 86** üretiyor;
> sayılar buna göre düzeltildi. Bölümün iddiası değişmedi: Task 1'in kalite koruması bu sayıyı
> hâlâ kımıldatmıyor. Sayılar `data/fixtures/S8_sensor_fault.csv`'den bağımsız olarak da
> doğrulanabilir (sonlu `min_ttl_h` = 183, `ALM-TTL-14D` taşıyan satır = 86).

**Neden (20 Eylül'de yeniden ölçüldü).** S8'in 183 tahmini **tek bir noktadan gelmiyor**:
fikstürün `worst_point` sütununa göre beş noktaya dağılıyor — `DSYA5_L2` 57, `DSYA4_L3` 54,
`DSYA4_L1` 41, `DSYA3_L1` 21, `DSYA7_L1` 10 (`data/fixtures/S8_sensor_fault.csv`).
Task 1'in eklediği koruma (`_suppress_ttl_when_quality_suspect`, §2) yalnızca `q != 0` olan
noktalarda devreye girer — yani zaten var olan bir kalite kuralı bir noktayı işaretlemişse.

Bu bölümün önceki hâli "yavaş, monoton bir sürüklenme dört kuraldan hiçbirine takılmıyor,
`q` 672 örneğin hiçbirinde sıfırdan çıkmıyor" diyordu. **Bu artık doğru değildir:** F-31 ile
sürüklenme için beşinci bir kural eklendi (`ALM-DQ-DRIFT`, bit 22, `contracts/alarm-codes.yaml`
v4) ve aynı fikstürde **239 kez** tetikleniyor; pano genelinde `q_any` 672 satırın **448'inde**
sıfırdan farklı.

**Açık kalan soru — uydurmuyoruz.** Sürüklenme artık işaretlendiği hâlde 86 satırın neden hâlâ
`ALM-TTL-14D` taşıdığı bu teslimde **ölçülmedi**. Akla gelen yol, korumanın `_update_quality`'den
ÖNCE koşması ve bir önceki turun `q`'sunu görmesi — bayrak birikene kadar geçen turlarda TTL
geçiyor olabilir. Bu bir **hipotezdir, ölçülmemiştir**; sonraki iterasyonun maddesidir.

**Bu bir eksik uygulama değil, kapsam dışı bırakılmış bir iştir.** Kapatmak, sürüklenmeyi
yakalayan yeni ve özel bir kalite kuralı gerektirir (uzun vadeli eğilimi bir taban ya da fiziksel
zarfla karşılaştıran, muhtemelen yeni bir `ALM-DQ-*` kodu ve `contracts/` değişikliği) — bu, 17
Eylül sözleşme dondurmasıyla çakışan ve Task 1'in "mevcut kural setinin garantisini genişlet"
kapsamından daha büyük, daha riskli bir değişikliktir. P1'de denenmedi.

Task 1'in eklediği garanti kendi başına gerçek ve kalıcıdır: zaten işaretli bir noktanın bir daha
asla yanıltıcı bir geri sayım göstermemesi, S8'den bağımsız bir kazanımdır. Tam metin ve gerekçe
[docs/05-anomali-tespiti.md](05-anomali-tespiti.md) §10'da güncellendi.

## 5. Bilinen sınır: alarm kartı geçerliliği donmuş (raise-time snapshot)

**Bu P1'in getirdiği bir kusur değil; P1'den önce de var olan bir tasarımın P1'e miras kalan
sonucu.** `backend/app/alarm_manager.py`'deki `Condition` (satır 68-76) ve `Alarm` (satır 79-100)
veri sınıfları `reason`/`advice`/`ttl_h` alanlarını alarm **oluştuğu an** dondurur; bu P1'den önce
de böyleydi (bkz. `backend/app/db.py:158`: "Açıklama (reason/advice/ttl_h) alarm oluştuğu anın
kanıtıdır: güncellenmez." — hemen altındaki `_ALARM_MUTABLE` listesi, satır 159-162, bu üç alanı
güncellenebilir sütunların dışında bilinçli olarak bırakır).

P1, `gecerlilik`'i **aynı donmuş `reason` sözlüğünün içine** ekledi (`backend/app/risk.py:154`,
bkz. §2 Task 3). Sonuç: bir nokta `tahmin_gecerli` iken (gerçek, sayısal bir `ttl_h` ile) bir alarm
açılırsa, o alarmın kartı bu `ttl_h`'i ve `gecerlilik`'i SONSUZA KADAR o andaki hâliyle taşır —
nokta daha sonra kalite şüpheli hâle gelse (`q != 0`) bile. `AlarmNedeni.tsx`'in "Ne kadar acil?"
bölümü (satır 118-136) bunu somutlaştırır: `ttl = ttlText(alarm.ttl_h)` doluysa (satır 121-125) her
zaman o dondurulmuş sayıyı gösterir; `validityHint(gecerlilik, alarm.prio)` (satır 127) YALNIZCA
`ttl` boşken çağrılır — yani alarmın kendi `ttl_h`'i zaten doluysa, o alarmın kartı canlı
`gecerlilik`'i hiç sormaz.

Aynı sayfada bunun somut, çelişkili görünümü: ölçüm tablosu (`PanoDetay.tsx`, §2 Task 7) her
`GET /api/v1/panels/{id}` çağrısında `panel_detail()`'in taze hesapladığı `gecerlilik`'i gösterir —
nokta kalite şüpheli olduğunda doğru şekilde "Sensör şüpheli" / "–" yazar. Ama aynı anda, o nokta
için ÖNCEDEN açılmış bir alarmın kartı hâlâ eski sayısal `ttl_h`'i göstermeye devam eder; iki
bileşen aynı noktayı farklı "an"lardan anlatır.

**Bu yüzden plan §4'ün 3. satırındaki ("yanıltıcı geri sayım yok") kabul kriteri (bkz. §3, satır 3)
tam değil, KOŞULLU doğrudur:** taze hesaplanan görünümler için geçerlidir — ölçüm tablosu (her
zaman) ve yeni açılan bir alarm (kendi koşulu hesaplandığı anda nokta zaten şüpheliyse, `gecerlilik`
baştan `sensor_supheli` gelir). Ama nokta şüpheli hâle gelmeden ÖNCE açılmış ve hâlâ açık duran bir
alarm için geçerli DEĞİLDİR — o kart, dondurulmuş anının `gecerlilik`'ini göstermeye devam eder.

`ttl_h`'in kendisinin donması zaten P1'den önce vardı (`_ALARM_MUTABLE`, yukarıda); P1 yalnızca
`gecerlilik`'i aynı donmuş yapıya ekleyip bu sınırı ONA da miras bıraktı, kapatmadı. Bu incelemede
önerilen ve burada uygulanan yol "düzeltmek" değil "açıkça belgelemek"tir: `AlarmNedeni.tsx`'in
props/mimarisini değiştirmek (örn. kartın kendi `gecerlilik`'ini alarmın `pano_id`+`point`'inden
ayrıca ve CANLI olarak çekmesi) bu düzeltme turunun kapsamından daha büyük, daha riskli bir
değişiklik olurdu. **Kapsam dışı, gerçek bir sınır olarak burada kayıt altına alınıyor;** kapatılması
ayrı bir görev gerektirir.

## 6. Açık kalan takip: IEC104 IV bayrağı `risk.ttl_hours`'a özel bağlı değil

Task 8'in incelemesinde ortaya çıkan, P1'de kapatılmayan tek gerçek boşluk: `risk.ttl_hours`
register'ının `None` olduğunda IEC104 tarafında `QDS_IV` (geçersiz) kalite bayrağı taşıdığını
doğrudan kontrol eden bir test **yok**.

Mekanizma prensipte zaten var ve BAŞKA register'lar için kanıtlı: `backend/app/scada/iec104_points.py`
NA-sentinel'e (`NA_INT16`/`NA_UINT16`) kodlanmış her ölçümü genel olarak `QDS_IV`'e çeviriyor;
`backend/tests/test_iec104_points.py::test_missing_values_are_invalid_quality` (satır 86) bunu
`DSYA1_L1` (IOA 1104) ve `voc_idx` (IOA 1307) üzerinden kanıtlıyor. Mekanizma register-agnostik
olduğu için `risk.ttl_hours`'un IOA'sının da aynı yolu izlemesi beklenir — ama bunu doğrudan
`risk.ttl_hours` için çalıştıran bir test hiçbir zaman yazılmadı; ne eski testlerde ne P1'de.

Bunun tek nedeni: brief'in istediği test `test_scada_encoder.py`'e yazılmıştı, ama o dosyanın hiç
IEC104 deseni yok — genel NA→IV mekanizması `test_iec104_points.py`'de yaşıyor ve o dosya Task
8'in görev kapsamı dışında tutulmuştu. İncelemeci bu ayrımı bağımsızca doğruladı (dosyayı grep'ledi,
mekanizmayı okudu, dışlamayı teyit etti) ve önerdiği düzeltme de Task 8'i genişletmek değil,
`test_iec104_points.py`'ye küçük, ayrı bir takip testi eklemekti. Maliyeti düşük ve dar kapsamlı
olduğu için ayrı bir görev turu açılmadı; burada kayıt altına alınıyor (docs/20'nin P0 açıklarını
sessizce kapatmak yerine belgeleme geleneğiyle tutarlı).

**Önerilen takip:** `test_iec104_points.py`'ye, `risk.ttl_h = None` iken `risk.ttl_hours`'un
IOA'sının döndüğü `PointValue.quality`'nin `QDS_IV` olduğunu doğrudan kontrol eden tek bir test.

## 7. Nasıl yeniden üretilir

```bash
cd libs/panoalgo && python -m pytest -q
cd ../../backend && python -m pytest -q
cd ../frontend && npx tsc --noEmit && npm run test
```

19 Eylül 2026'da bu raporu ilk yazarken alınan sonuç: panoalgo 407, backend 661/28 atlanan,
frontend 107 — üçü de PASS. Final whole-branch review'un düzeltme dalgası (commit `89b55d7`,
`c860fae`) iki yeni test ekledi; güncel sonuç (üçü de PASS):

- **panoalgo:** `408 passed` (bkz. §2 Task 1, sürüklenmeyi değil "zaten işaretli nokta" korumasının
  gerçekten devrede olduğunu kilitleyen yeni test)
- **backend:** `662 passed, 28 skipped` (atlananların tamamı `TEST_DB_DSN tanimli degil` —
  gerçek Postgres gerektiren entegrasyon testleri, CI dışı ortamda beklenen davranış; ayrıca
  `test_stream.py::test_disconnect_racing_with_outer_cancellation_closes_cleanly` bu değişiklerle
  ilgisiz, önceden var olan olasılıksal (~%10) bir testtir — bazı çalıştırmalarda başarısız olabilir)
- **frontend:** `tsc --noEmit` sıfır hata; `vitest run` → `9 test dosyası, 107 test`, tamamı PASS

P1'e özgü testleri tek başına koşturmak için:

```bash
cd libs/panoalgo && python -m pytest tests/test_edge.py -q
cd backend && python -m pytest tests/test_p1_validity_scenarios.py tests/test_api_panels.py tests/test_risk.py tests/test_scada_encoder.py tests/test_telegram.py -q
cd frontend && npx vitest run src/lib/labels.test.ts
```

docs/12'nin yeniden üretimi (S8 dâhil hiçbir sayının kımıldamadığını doğrulamak için):

```bash
python scripts/validate.py --out docs/12-dogrulama-sonuclari.md
git diff --stat docs/12-dogrulama-sonuclari.md   # yalnızca "Uretim zamani" satırı beklenir
```
