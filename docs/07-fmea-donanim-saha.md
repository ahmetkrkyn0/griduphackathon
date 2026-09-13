# 07 — FMEA: Donanım ve Saha

> **Sahip:** Kişi C · Rapor §7.3'ün donanım/saha satırları (1, 2, 3, 9, 10). Yazılım/sistem
> satırları için bkz. `docs/07b-fmea-yazilim-sistem.md` (Kişi B). Ş = şiddet, O = olasılık,
> D = tespit edilemezlik (1–10); RÖS = Ş×O×D.

| # | Hata türü | Etki | Ş | O | D | RÖS | Önlem | Önlem sonrası RÖS |
|---|---|---|---|---|---|---|---|---|
| 1 | Bağlantı sıcaklık düğümü yerinden düştü | Nokta izlenemez; düşerse fazlar arası kısa devre riski | 9 | 3 | 5 | 135 | İletken olmayan gövde, çift bağ (V-0 kablo bağı + mekanik kilit), "sıcaklık ortama indi + ani düşüş" algoritması ile tespit (`ALM-DQ-BELOW-AMBIENT`) | 9×2×2 = 36 |
| 2 | Düşük yükte enerji toplama yetersiz | Veri boşluğu | 4 | 6 | 3 | 72 | Süperkapasitör + düşük yükte seyrek gönderim; "yetersiz enerji" durumu düğüm sağlığında raporlanır (`health.vbak_pct`) | 4×3×2 = 24 |
| 3 | Kontrolcü beslemesi kesildi | İzleme durur | 7 | 4 | 3 | 84 | Süperkapasitör (`blok-diyagrami.md` §4) ile son nefes mesajı; merkezde heartbeat kaybı alarmı (`ALM-COMMS-LOST`) | 7×4×1 = 28 |
| 9 | Sensör kalibrasyon kayması | Yanlış ölçüm | 5 | 4 | 6 | 120 | Fazlar arası ve komşu sensör çapraz kontrolü (`FazKarsilastirma`, frontend); ortam sensörleriyle gece "eşitlenme" kontrolü | 5×3×3 = 45 |
| 10 | Kurulumda AT sekonderinin açık devre kalması | Aşırı gerilim, AT hasarı, tehlike | 10 | 2 | 4 | 80 | Yalnızca ayrık çekirdekli (devreyi açmayan) sensör kullanımı; `docs/08` kurulum prosedüründe açık uyarı ve kontrol listesi maddesi | 10×1×2 = 20 |

## Donanım/saha risklerine özel notlar

- **Satır 1 ve 10**, saha kurulum ekibinin en sık yapabileceği iki hata; bu yüzden ikisi de
  `docs/08-kurulum-proseduru.md`'de ayrı, vurgulu maddeler olarak tekrarlanır (tek yerde yazıp
  unutulmasın diye).
- **Satır 9**, kalibrasyon kaymasının kendisinin bir yazılım kontrolüyle (çapraz doğrulama)
  hafifletilmesi — donanım riski, yazılım katmanında yakalanıyor; bu nedenle `docs/07b` ile
  birlikte okunmalı.
- Bu tablo elle güncellenmiştir (üretilmiş değildir); yeni bir donanım revizyonu (`hardware/`)
  eklendiğinde bu dosyaya yeni bir satır eklenmelidir.
