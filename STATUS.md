# Kişi C — Durum Takibi (Arayüz, Donanım Tasarımı, Teslim)

> Bu dosya yalnızca C'nin (Berke) kendi ilerleme takibi içindir; PLAN.md'nin yerine geçmez.
> PLAN.md'de yalnızca kutucuk işaretleme ve "Günlük Kayıt" satırı ekleme yapılır (kural: ortak dosya).
> Her önemli adımdan sonra bu dosya güncellenir. Dal: `berke/frontend` (origin'e push edildi).

**Son güncelleme:** 14 Eylül 2026, devam ediyor (oturum: otonom `/goal` çalışması).
**Son commit:** Faz 4/5 (README, ekran görüntüleri, demo betikleri, sunum taslağı) — bkz. §1.

## 0.1 ⚠️ Ekip riski (öneri seçilerek not düşüldü, aksiyon ekipte)

**A kulvarı (`libs/panoalgo/`, `firmware/`, `sim/panosim.py`, `mpr53cs_sim.py`, `tvoc2_sim.py`,
`docs/05`, `docs/12`) bu tarih itibarıyla depoda hâlâ yok** — `sim/` yalnızca bir yer tutucu
(`hello_publisher.py`) içeriyor, `docs/` klasöründe 17 dosyadan yalnızca A'ya ait 2'si eksik.
B ve C tamamlandı ve örnek veriyle uçtan uca çalışıyor; ama **gerçek Docker yığınında "uçtan uca"
demo ve `demo/senaryo/s0-s6` A'nın işi olmadan gösterilemez.** Özellik dondurmaya (17 Eylül 23:59)
3 gün var. Bu, C'nin çözebileceği bir şey değil (dosya sahipliği kuralı); PLAN.md Günlük Kayıt'a
ve bu bölüme not düşüldü ki ekip bugün görüp aksiyon alsın.

## 0. Bu oturumun hedefi

Kullanıcı talebi (özet): C'nin kalan tüm frontend/donanım/teslim görevlerini bitir. Başka daldan
bir şey gerekirse mevcut daldan yeni bir dal aç, birleştirmeyi orada yap. Karar gereken yerlerde
önerilen seçeneği uygula. Her şeyi not düş, bu dosyayı sürekli güncelle.

## 1. Genel ilerleme

| Faz | Durum |
|---|---|
| TC1 (Filo listesi, pano detay, WS akışı) | ✅ Tamamlandı (önceki oturum) |
| Entegrasyon (`origin/ahmet/backend` merge) | ✅ Tamamlandı |
| TC2 (Alarm konsolu, dijital ikiz trendi, donanım şeması başlangıcı) | ✅ Tamamlandı, commit `f98058b` |
| TC3 (Trend/korelasyon, kara kutu, cihaz sağlığı, bölge haritası, donanım dok.) | ✅ Tamamlandı, commit `f98058b` |
| Faz 4/5/6 (README, ekran görüntüleri, demo betikleri, sunum) | ⏳ Devam ediyor |

## 2. Yapılan entegrasyon

- **`int/pull-ahmet-backend` dalı** `berke/frontend`'den açıldı, `origin/ahmet/backend` içine
  merge edildi (çakışmasız, 58 dosya), sonra `berke/frontend`'e geri merge edildi. Artık
  `berke/frontend` şunları da içeriyor:
  - `backend/app/api/insights.py` → `GET /panels/{id}/series`, `GET /events/{id}/blackbox`,
    `GET /fleet/kpi` (TC3'ün kullandığı uçlar).
  - `backend/app/scada/*`, `docs/02/03/04/07b/09/15/17`, `loadtest/`, `scripts/gen_*` — B'nin işi.
- **Doğrulama notu:** Bu makinede global `starlette` sürümü (`1.0.0`) `fastapi==0.115.*` ile
  uyumsuz olduğu için backend testleri toplanamıyor. **Merge öncesi `main`'de de var** — benim
  değişikliğimden kaynaklanmıyor. B'ye bildirilmeli.

## 3. TC2 — tamamlandı

Alarm konsolu (`/alarmlar`), dijital ikizde nokta tıklanınca gerçek zaman serisi trendi, yeni API
uçları (`alarms`, `shelve`, `series`, `blackbox`), `assets/ek2-14-pano.svg`,
`hardware/pano-beyni/` (blok diyagramı + I/O tablosu + BOM + README), `docs/16-ux-tasarim.md`.
Ayrıntı: PLAN.md TC2 bölümü + Günlük Kayıt (14 Eylül).

## 4. TC3 — tamamlandı

`TrendKorelasyon.tsx` (I²–ΔT dağılımı — **fizik düzeltmesi yapıldı**, bkz. §6), `OlayAnalizi.tsx`
(kara kutu + yeni ark tripi senaryosu), `CihazSagligi.tsx`, `BolgeHaritasi.tsx`,
`hardware/yerlesim/ek2-14-yerlesim.svg`, `hardware/mekanik/din-kutu.scad`, `docs/01/07/08/10/11/13`.
**9 ekranın 7'si çalışıyor** (kabul kriteri karşılandı). Ayrıntı: PLAN.md TC3 + Günlük Kayıt.

## 5. Faz 4/5/6 — C'nin görevleri

| Görev | Durum |
|---|---|
| T4.5 README (repo kökü) 7-çıktı tablosu | ✅ Tamamlandı |
| T4.6 Ekran görüntüleri (`assets/ekran/`, 7 ekran) | ✅ Tamamlandı, `docs/16` §5'e gömülü |
| T4.7 Sır taraması (C'nin payı) | ✅ Temiz — son commit'ten önce tekrar koşulmalı |
| T5.1 Belirlenimli demo betikleri (`demo/senaryo/`) | ✅ Yazıldı (`s0`–`s6` A'yı bekliyor, `s7`/`s8` çalışır) |
| T5.2 Sunum taslağı (`demo/sunum/`) | ✅ Tamamlandı |
| Faz 6 teslim kontrol listesi | ⏳ Ekip teslim gününde (20 Eylül) yapacak |

## 6. Kararlar (öneri seçilerek verildi — kullanıcı talimatı gereği, uygulandıkları haliyle)

1. **KiCad şeması → blok diyagramı + I/O tablosu + BOM.** İlk planda "stok KiCad sembolleriyle
   geçerli bir `.kicad_sch`" düşünülmüştü; **uygulama sırasında bundan vazgeçildi**: KiCad'in
   sürüme özgü dosya formatı (uuid, `lib_symbols`, sayfa şeması) bu ortamda (KiCad kurulu değil,
   internet yok) doğrulanamazdı — küçük bir sözdizimi hatası dosyayı açılmaz/bozuk hale
   getirebilirdi, bu da "sahte şema" izlenimi doğurup dürüstlük kuralını asıl ihlal eden şey
   olurdu. Bunun yerine `hardware/pano-beyni/blok-diyagrami.md` (Mermaid, gerçek parça
   numaralarıyla) + `io-tablosu.md` + `bom.csv` — rapor §10'un kendi tanımladığı asgari seviye.
   Gerekçe `hardware/pano-beyni/README.md`'de açık yazılı.
2. **Bölge haritası → il/ilçe değil dağıtım şirketi (ADM/GDZ) bazlı.** Sözleşmede (`PanelSummary`)
   gerçek bir il/ilçe alanı yok, yalnızca genelde boş `lat`/`lon`. Coğrafi olarak uydurma bir
   kırılım göstermek yerine, pano kimliğinden gerçekten çıkarılabilen tek yapısal ayrımı
   (ADM-xxxxx / GDZ-xxxxx öneki) kullandım. `docs/16` §3'te açıkça belirtildi.
3. **Cihaz sağlığı ekranı ölçek sınırı.** API'de toplu "düğüm sağlığı" ucu yok. Görünen panoları
   sınırlı eşzamanlılıkla (6) tek tek çekiyor; ekranın altında bu açıkça yazıyor. Kalıcı çözüm
   için `contracts/changes/2026-09-14-fleet-health-bulk.md` önerisi açıldı (3 onay bekliyor).
4. **OpenSCAD/STL üretilmedi.** Bu ortamda `openscad` kurulu değil, internet de yok; yalnızca
   `.scad` kaynağı teslim edildi (`hardware/mekanik/din-kutu.scad`), STL üretimi ekip içinde
   OpenSCAD kurulu bir makinede yapılmalı. README'de not düşüldü.
5. **Sentetik veri fizik düzeltmesi (TC3 sırasında bulundu).** İlk `mockSeries.ts` sürümünde
   bağlantı ΔT'si ve panel akımı birbirinden bağımsız, ayrı gürültü fonksiyonlarıyla üretiliyordu.
   Bu, I²–ΔT saçılım grafiğinde "sağlıklı vs gevşek bağlantı farklı eğim" iddiasını **görsel
   olarak yalanlıyordu** (ilk ve son 7 günün eğimi ~aynı çıktı: 530 vs 677 yerine ~30 vs ~30).
   Kök neden: ΔT, gerçek fizik modelinden (ΔT = K·I²) değil, bağımsız bir zaman rampasından
   geliyordu. Düzeltme: `connPointValue` artık `elecValue`'nun kullandığı **aynı** akım
   fonksiyonunu (`phaseCurrentA`) kullanıp ΔT'yi bu akımdan `K₀·K_ratio·I²` olarak türetiyor.
   Tarayıcıda doğrulandı: düzeltme sonrası eğim farkı 530,91 vs 677,20 (×10⁻⁶) — rapor §6.5
   L1-1'in iddia ettiği görsel artık gerçekten ortaya çıkıyor.
6. **Demo betikleri (henüz yapılmadı, T5.1):** Gerçek Docker yığını bu ortamda çalışmadığı için
   `demo/senaryo/*.sh` betikleri yazılacak ve yalnızca statik olarak gözden geçirilecek, gerçek
   yığına karşı çalıştırılıp doğrulanmayacak. Ekip bir kez gerçek yığında çalıştırıp süreleri
   teyit etmeli.

## 7. Riskler / ekibe not

- Backend ortam sorunu (§2) B'ye iletilmeli.
- `contracts/changes/2026-09-14-fleet-health-bulk.md` üç onay bekliyor.
- Demo betikleri (T5.1 tamamlanınca) gerçek yığında bir kez çalıştırılıp zamanlamaları teyit
  edilmeli.
- `hardware/mekanik/din-kutu.scad` bir OpenSCAD kurulu makinede STL'e çevrilmeli.

---
*Bu bölümün altına yeni girişler en üste eklenir (en yeni en üstte).*
