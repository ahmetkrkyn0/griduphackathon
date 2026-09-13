# Kişi C — Durum Takibi (Arayüz, Donanım Tasarımı, Teslim)

> Bu dosya yalnızca C'nin (Berke) kendi ilerleme takibi içindir; PLAN.md'nin yerine geçmez.
> PLAN.md'de yalnızca kutucuk işaretleme ve "Günlük Kayıt" satırı ekleme yapılır (kural: ortak dosya).
> Her önemli adımdan sonra bu dosya güncellenir. Dal: `berke/frontend`.

**Son güncelleme:** 14 Eylül 2026, devam ediyor (oturum: otonom `/goal` çalışması).

## 0. Bu oturumun hedefi

Kullanıcı talebi (özet): C'nin kalan tüm frontend/donanım/teslim görevlerini bitir. Başka daldan
bir şey gerekirse mevcut daldan yeni bir dal aç, birleştirmeyi orada yap. Karar gereken yerlerde
önerilen seçeneği uygula. Her şeyi not düş, bu dosyayı sürekli güncelle.

## 1. Yapılan entegrasyon

- **`int/pull-ahmet-backend` dalı** `berke/frontend`'den açıldı, `origin/ahmet/backend` içine
  merge edildi (çakışmasız, 58 dosya), backend testleriyle doğrulanmaya çalışıldı, sonra
  `berke/frontend`'e geri merge edildi. Artık `berke/frontend` şunları da içeriyor:
  - `backend/app/api/insights.py` → `GET /panels/{id}/series`, `GET /events/{id}/blackbox`,
    `GET /fleet/kpi` (TC3'ün ihtiyaç duyduğu uçlar; sözleşmede zaten tanımlıydı, kod şimdi var).
  - `backend/app/scada/*` (Modbus TCP + IEC 104 ağ geçidi) — B'nin işi, dokunmadım.
  - `docs/02, 03, 04, 07b, 09, 15, 17` — B'nin dokümanları, dokunmadım.
  - `loadtest/`, `scripts/gen_*` — B'nin işi.
- **Doğrulama notu:** Bu makinede `pip` genelinde `starlette` sürümü (`1.0.0`) `fastapi==0.115.*`
  ile uyumsuz olduğu için testler toplanamıyor (`TypeError: Router.__init__() got an unexpected
  keyword argument 'on_startup'`). Bu hata **merge öncesi `main`'de de var** — benim
  değişikliğimden kaynaklanmıyor, `backend/requirements.txt` (B'nin kilit dosyası) doğru pin'i
  içeriyor; sorun yerel ortamın global paket kirliliği. Docker imajı muhtemelen etkilenmez
  (temiz `pip install -r requirements.txt`). B'ye bildirilmeli.

## 2. TC1 (Faz 1) — durum: tamamlandı, önceki oturumda

Filo listesi, pano detay, WebSocket akışı, "RAL 7035" tema yönü. Ayrıntı: `frontend/README.md`.

## 3. TC2 (Faz 2) — Alarm konsolu + dijital ikiz + donanım şeması başlangıcı

| # | Görev | Durum |
|---|---|---|
| 1 | Alarm konsolu sayfası (`/alarmlar`) — öncelik/zaman/konum, Neden/Ne yapmalı/Ne kadar acil, onay/raf/yorum, eskalasyon | planlandı |
| 2 | API: `GET /api/v1/alarms`, `POST /alarms/{id}/shelve`, `GET /panels/{id}/series` istemciye eklenecek | planlandı |
| 3 | Dijital ikiz: nokta tıklanınca gerçek zaman serisi trendi (K/K₀, ΔT) | planlandı |
| 4 | `assets/ek2-14-pano.svg` — kendi çizimimiz, statik | planlandı |
| 5 | `hardware/pano-beyni/` — blok diyagramı, I/O tablosu, KiCad şema v1, BOM taslağı | planlandı |
| 6 | `docs/16-ux-tasarim.md` başlangıç | planlandı |

## 4. TC3 (Faz 3) — Trend/korelasyon, kara kutu, cihaz sağlığı, donanım dokümantasyonu

| # | Görev | Durum |
|---|---|---|
| 1 | `TrendKorelasyon.tsx` — I²–ΔT dağılımı, K trendi, çiy noktası marjı | planlandı |
| 2 | `OlayAnalizi.tsx` — kara kutu (`/events/{id}/blackbox`) | planlandı |
| 3 | `CihazSagligi.tsx` — düğüm/pano sağlığı | planlandı |
| 4 | `BolgeHaritasi.tsx` — çevrimdışı, il bazlı özet harita | planlandı |
| 5 | `hardware/yerlesim/ek2-14-yerlesim.svg`, `hardware/mekanik/din-kutu.scad` | planlandı |
| 6 | `docs/07, 08, 10, 11, 13, 01` | planlandı |

## 5. Faz 4/5/6 — C'nin kalan görevleri

| Görev | Durum |
|---|---|
| T4.5 README 7-çıktı tablosu | planlandı |
| T4.6 Ekran görüntüleri (`assets/ekran/`) | planlandı |
| T5.1 Belirlenimli demo betikleri | planlandı |
| T5.2 Sunum taslağı | planlandı |
| PLAN.md kutucukları + Günlük Kayıt | planlandı |

## 6. Kararlar (öneri seçilerek verildi — kullanıcı talimatı gereği)

1. **KiCad şeması gerçekçilik sınırı:** Vendor IC'lerin (ADM2587E, ATECC608A vb.) gerçek KiCad
   sembolleri elde mevcut değil (internet/kütüphane erişimi yok, üretmek riskli/yanıltıcı
   olurdu). Bunun yerine: (a) stok KiCad kütüphanelerindeki gerçek sembollerle (Device, power,
   Connector_Generic) geçerli, açılabilir bir `.kicad_sch` + (b) Mermaid blok diyagramı (parça
   numaralarıyla, metin) + (c) I/O tablosu + (d) BOM. `hardware/pano-beyni/README.md` hangisinin
   gerçek sembol, hangisinin etiketli blok olduğunu açıkça yazar (dürüstlük kuralı, Bölüm C).
2. **Bölge haritası:** Gerçek harita karosu kullanılmıyor (GK4, internet yok). İl bazlı, soyut
   ama etiketli bir düzen (ADM: Aydın/Denizli/Muğla, GDZ: İzmir/Manisa) — coğrafi doğruluk iddia
   edilmez, `docs/16`'da bu açıkça belirtilir.
3. **Cihaz sağlığı ekranı ölçek sınırı:** API'de toplu "düğüm sağlığı" ucu yok, yalnızca
   pano-bazlı detay var. Interim çözüm: görünen panoların detayını çeker (sayfalanmış, "tümünü
   yükle" butonu). Kalıcı çözüm için `contracts/changes/2026-09-14-fleet-health-bulk.md` öneri
   dosyası açılacak (3 onay bekleyecek, bu bir öneri; uygulanması B'nin onayına bağlı).
4. **OpenSCAD/STL:** Bu ortamda `openscad` çalıştırılabilir değil; yalnızca `.scad` kaynağı
   teslim edilir, STL üretimi ekip içinde OpenSCAD kurulu bir makinede yapılmalı (README'de not
   düşülecek).
5. **Demo betikleri:** Gerçek Docker yığını bu ortamda çalışmadığı için `demo/senaryo/*.sh`
   betikleri yazılacak ve statik olarak gözden geçirilecek ama gerçek yığına karşı çalıştırılıp
   doğrulanmayacak. Bu STATUS.md'de açıkça belirtilir.

## 7. Riskler / ekibe not

- Backend ortam sorunu (madde 1) B'ye iletilmeli.
- `contracts/changes/2026-09-14-fleet-health-bulk.md` üç onay bekleyecek.
- Demo betikleri gerçek yığında bir kez çalıştırılıp zamanlamaları teyit edilmeli.

---
*Bu bölümün altına yeni girişler en üste eklenir (en yeni en üstte).*
