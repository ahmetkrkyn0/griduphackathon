# 20 — P0: Güncel Kanıt ve Sınır Raporu

> Kaynak görev: [INOVASYON-UYGULAMA-PLANI.md](../INOVASYON-UYGULAMA-PLANI.md) §3 (P0 — Güncel durumu sabitle ve
> iddiaları ölçümle eşle). Bu dosya P0'ın istediği üç çıktıyı tek yerde toplar: (1) iddia → test/ölçüm → sınır
> tablosu, (2) güncel başarım özeti, (3) bilinen açıkların kısa listesi. **18 Eylül 2026** tarihinde üretildi.
>
> **Kapsam notu:** Bu P0 denetimidir — kod/README değişikliği yapılmadı. Aşağıda listelenen açıklar P1+ işi.

## 1. Anlık durum (donmuş referans noktası)

| Alan | Değer |
|---|---|
| Commit | `66f7a7d9` (`git log -1`), dal `berke/upgrade` |
| Çalışma ağacı | Temiz (`git status --porcelain` boş) |
| Senaryo seed'i | `1304` (`docs/12-dogrulama-sonuclari.md` §5, `libs/panoalgo/panoalgo/scenarios.py` ile eşleşiyor) |
| Veri sürümü | `data/fixtures/` — 10 senaryo + `rls_vectors.csv`, `git status` temiz (son değişiklik commit `0cd7d79`, 2026-09-14) |
| Rollback noktası | Git tag YOK (`git tag -l` boş). Fiilen tek "bilinen iyi" nokta şu an ki temiz HEAD'dir. **Açık: demo öncesi bir `demo-YYYYMMDD` tag'i atılmalı.** |
| Mevcut demo yapılandırması | `deploy/compose.yaml` + `compose.sim.yaml` + `compose.frontend.yaml`, imajlar sha256 digest ile sabit (bkz. §4) |

## 2. Doğrulama tekrar-üretimi (P0 madde 2)

```
python scripts/validate.py --out <scratch>/12-dogrulama-yeniden.md
diff docs/12-dogrulama-sonuclari.md <scratch>/12-dogrulama-yeniden.md
```

**Sonuç: SIFIR SAPMA.** Üretim zaman damgası dışında committed `docs/12-dogrulama-sonuclari.md` ile yeniden
üretilen çıktı **bit bit aynı**. Yani 15 Eylül'de ölçülüp yazılan her sayı (recall, yanlış alarm yükü, prognoz
geri testi) bugünkü kod ve veriyle birebir tekrar üretilebiliyor — kod ile belge arasında drift yok.

## 3. İddia → Test/Ölçüm → Sınır

| # | İddia | Test / Ölçüm (kaynak) | Sınır / Uyarı |
|---|---|---|---|
| 1 | Tespit başarısı: S1–S9 senaryolarında recall 1.00 | `docs/12-dogrulama-sonuclari.md` §1, `python scripts/validate.py` (bugün tekrar üretildi, sapma yok) | **n = 1**: her senaryo tek seed'li tek yörünge; popülasyon istatistiği değil (`docs/12` §4.3) |
| 2 | S1 (gevşek bağlantı) erken uyarısı, sabit 70 K eşiğinden **8,7 gün önce** tespit ediyor | `docs/12` §2 — L1 fiziksel katman, anlık `k_ratio` oranı | Bu, TTL/kalan-ömür TAHMİNİ değildir — yalnız eşik-öncesi tespittir (bkz. madde 3) |
| 3 | Aynı S1 senaryosunda kalan-ömür (TTL) tahmini güvenilir | `docs/12` §4/§4.1 — CRA **−5,12**, koni-içi oran **%5,2**, ömrün %25/%50/%75'inde bile "koni içinde: hayır" | **Kök neden:** TTL doğrusal ekstrapolasyon + aşırı yumuşatılmış eğim (`libs/panoalgo/panoalgo/detect.py:271-285` `K_SLOPE_ALPHA=0.05`, EWMA ~20 örnek hafıza) fiziksel süreç hızlandıkça geriden geliyor; güven aralığı taşınmıyor (`edge.py:195-211`). Zaten `docs/05-anomali-tespiti.md` §10 "Bilinen sınırlar"da belgeli. **Erken uyarı ile TTL doğruluğu birbirine karıştırılmamalı — ürün/demo dilinde ayrı sunulmalı.** |
| 4 | S8 (sensör arızası) sınır aşılmadan alarm üretmiyor | `docs/12` §1 (recall 1.00, tek beklenen alarm = arıza tespiti, sınır ihlali değil) | **183 sonlu TTL tahmini üretildi**, sınır HİÇ aşılmadı (`docs/12` §4.3, "PROGNOZ YANLIŞ-ALARMI"); 86'sı `ALM-TTL-14D` alarmına döndü ve §3'teki yanlış-alarm sayacı bunu GÖRMÜYOR (etiket penceresi içinde çıkıyor). **Kök neden:** kalite katmanı (`quality.py`) yavaş/monoton sürüklenmeyi yakalamıyor + TTL hattı (`edge.py:109-110`, `detect.py:292-305`) kalite bitlerinden habersiz — RLS regresyonu yavaş sensör sürüklenmesi ile gerçek ısınmayı ayıramıyor. Zaten `docs/05` §10 ve `GELISTIRME-BACKLOGU.md:87-92` (F-04), `:293`'te belgeli; **README/PLAN.md'de yok**. |
| 5 | README: "sensör düğümleri ve PD kartı dahil toplam pano başı retrofit maliyeti **<120 USD**" | Kaynak gösterilen `docs/10-bom-maliyet-roi.md` — "120" rakamı belgede **hiç geçmiyor**. Belge yalnızca kontrolcü kartı maliyetini verir (~37 USD adet 1.000'de) ve açıkça **"+ sensör/kurulum"** ekler (satır 52) — toplanmamış | **Kaynakla eşleşmiyor.** Ya rakam başka bir yerde (elle) hesaplanmış ve dokümana yazılmamış, ya da güncelliğini yitirmiş. P0 kapsamında düzeltilmedi — README'yi gözden geçirmek P1+ işi. |
| 6 | README: "1 engellenen yangında **14–22 ayda** kendini amorti eder" | `docs/10` §3 — ROI parametrik formülü var ama "14–22 ay" rakamı belgede yok; belge kendi kendine **"Sayılar iddia değil, örnektir"** diyor (satır 56) | **Kaynakla eşleşmiyor**, aynı not #5 |
| 7 | README: "Alarmlar ... GSM modeme (SMS) ve **Telegram Bot API**'ye ... sıfır gecikmeyle ... teslim edilir" | SMS: `docs/17-donanimsiz-dogrulama.md:36` — sürücü gerçek (AT/PDU), modem **simülasyon**, p95 gecikme ölçülü (`docs/09`). Telegram: `docs/17`'nin kanıt tablosunda **hiç yok** (Telegram 17 Eylül'de eklendi, `docs/17` 16 Eylül'de dondu); `backend/tests/test_telegram.py` tamamen `httpx.MockTransport` ile sahte | **Telegram için gerçek telefona teslim kanıtı yok**, gecikme ölçümü yok. "Sıfır gecikme" ifadesi kanıtsız. |
| 8 | README: "656 test" (backend+db+SCADA+bildirim+Telegram) | `docs/17:149` — panoalgo 401, backend 661 (DB'li), frontend 85; hiçbir kombinasyon 656 etmiyor | Sayı muhtemelen bayat/elle girilmiş. `docs/17`'nin kendisi de README'nin eski sayı taşıyabileceğini söylüyor. |
| 9 | Saha doğrulaması | `docs/17-donanimsiz-dogrulama.md` — başlığın kendisi "**Donanım Olmadan** Neyi, Nasıl Kanıtladık?"; "Donanım satın alınmadı" (satır 16) açıkça yazıyor | README doğrudan "sahada test edildi" demiyor (iyi) — ama proje genelinde saha/donanım kanıtı **yok**, hepsi simülasyon/tasarım seviyesinde. Bu, projenin kendi dürüstlük kuralına (`docs/17:11`) uygun bir itiraf; risk README'nin bunu her yerde yeterince açık söylememesi. |

## 4. Bilinen açıklar (kısa liste)

1. **Rollback tag'i yok** — demo öncesi bilinen-iyi commit'e tag atılmamış (§1).
2. **S1 TTL tahmini sistematik olarak güvenilmez** (CRA −5,12) — README/sunumda "erken uyarı" ile "kalan ömür tahmini" ayrı sunulmalı; şu an ayrım belgelerde var ama üründe/UI dilinde karışabilir (P1 kapsamı, `frontend/src/components/AlarmNedeni.tsx`).
3. **S8 sahte-TTL alarmı** (183 tahmin, sınır hiç aşılmadan) — kod düzeyinde düzeltme yapılmadı, yalnız belgelendi (`docs/05` §10). Kalite bitlerinin TTL hattına bağlanması gerekiyor (`edge.py`/`detect.py`).
4. **Maliyet rakamları (README:32) kaynak dokümanla eşleşmiyor** — "<120 USD" ve "14–22 ay" ifadeleri `docs/10`'da yok; `docs/10` kendini "örnek, iddia değil" olarak işaretliyor.
5. **Telegram bildirim kanalı kanıtsız** — `docs/17` donma tarihinden (16 Eylül) sonra eklendi, testleri tamamen mock, gerçek teslim/gecikme ölçümü yok; README "sıfır gecikme" diyor.
6. **README test sayısı (656) hiçbir alt toplamla uyuşmuyor** — muhtemelen bayat.
7. **`docs/17-donanimsiz-dogrulama.md` kendisi 16 Eylül'de dondu**, ama proje o tarihten sonra değişti (Telegram, test sayıları) — bu doğrulama dosyasının da bir güncelleme geçişine ihtiyacı var.

## 5. Nasıl yeniden üretilir

```bash
python scripts/validate.py --out <scratch-path>/12-dogrulama-yeniden.md
diff docs/12-dogrulama-sonuclari.md <scratch-path>/12-dogrulama-yeniden.md   # sıfır sapma bekleniyor
git log -1 --format="%H %ci %s"
git tag -l
```

Bu rapor P1'in önkoşuludur (bkz. plan §3 "Bitti ölçütü"). P1 çalışmasına, madde 2 ve 3'teki kök nedenler
zaten koda referans verilmiş halde başlanabilir.
