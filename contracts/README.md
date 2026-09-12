# `contracts/` — Kilitli Bölge

Bu dizin **donmuştur.** Üç kulvarın birbirine dokunmadan paralel çalışabilmesinin tek sebebi burada yazanlara herkesin birebir uymasıdır.

> Bir alan adını değiştirdiğinde üç kulvar birden kırılır ve bunu M1/M2 kapısında, en kötü anda öğrenirsin.

## Dosyalar ve kim okur

| Dosya | Üreten | Tüketen | Ne işe yarar |
|---|---|---|---|
| `mqtt-telemetry.schema.json` | A (`sim/`, `firmware/`) | B (`backend/app/ingest.py`) | Kenardan merkeze giden telemetri yükü + topic planı |
| `modbus-map.yaml` | — (ortak karar) | A (`firmware/core/modbus_map.c`), B (`backend/app/scada/map_loader.py`, `scripts/gen_modbus_doc.py`) | Pano Beyni register haritası; `docs/03` bundan **üretilir** |
| `alarm-codes.yaml` | — (ortak karar) | A (`limits.py`, `fusion.py`, `limits.c`), B (`alarm_manager.py`, `notify/`), C (kod → Türkçe metin) | Alarm kodları, **tüm eşikler**, hipotezler, otomatik aksiyonlar |
| `openapi.yaml` | B (`backend/`) | C (`frontend/src/api/`) | Arayüzün tükettiği tek HTTP/WS sözleşmesi |
| `scenario-labels.schema.json` | A (`scenarios.py`) | A (`scripts/validate.py`), B (`loadtest/fleet.py`) | Etiketli senaryo çıktısı; doğrulama metriklerinin temeli |

## Üç demir kural

1. **Eşik, adres ve kod sabitleri koda gömülmez.** Hepsi bu dizinden okunur (PLAN.md Bölüm B, kural 10). Aynı sabitin üç yerde üç farklı değeri olması demoyu patlatır.
2. **Alan adı uydurulmaz.** Eksik bir alan varsa aşağıdaki değişiklik süreci işletilir. "Şimdilik ben ekleyeyim, sonra söylerim" yok.
3. **Mevcut sözleşme dosyası tek başına düzenlenmez.** Düzenlemek isteyen önce değişiklik dosyası açar.

## Değişiklik süreci (çakışmasız)

1. `contracts/changes/YYYY-MM-DD-<kisa-konu>.md` adında **yeni bir dosya** aç. (Mevcut dosyaya satır eklemek üç kişinin çakışma noktası olurdu; yeni dosya hiçbir zaman çakışmaz.)
2. Dosyaya şunları yaz: **ne değişiyor**, **neden**, **hangi kulvarlar etkileniyor**, **geri uyumlu mu**.
3. Üç kişiden **onay** al (PR'da üç approve).
4. Onay gelince ilgili sözleşme dosyasını düzenle **ve** `version` alanını bir artır.
5. Etkilenen kulvarlar aynı gün uyumlanır — sözleşme ile kod arasında bir geceden uzun fark kalmaz.

### Şablon

```markdown
# <tarih> — <konu>

**Dosya:** contracts/<dosya>
**Öneren:** Kişi <A/B/C>
**Ne değişiyor:** <alan/blok/uç adı> eklenecek / değişecek / kalkacak
**Neden:** <bir-iki cümle, hangi görev bunu gerektiriyor>
**Etkilenen kulvarlar:** A / B / C
**Geri uyumlu mu:** evet (yalnızca ekleme) / hayır (mevcut alan değişiyor)
**Onaylar:** [ ] A  [ ] B  [ ] C
```

## Faz 3'ten sonra

**17 Eylül özellik dondurmasından sonra sözleşme değişmez.** İhtiyaç çıkarsa sözleşme korunur, ilgili kulvar kendi içinde **adaptör** yazar. Son üç günde sözleşme değiştirmek teslimi riske atar.

## Doğrulama

```bash
python scripts/check_contracts.py
```

**Her PR'dan önce ve her sözleşme değişikliğinden sonra koşturun.** Betik şunları denetler:

- beş dosya ayrıştırılabiliyor mu, JSON şemaları draft 2020-12'e göre geçerli mi
- **Modbus adres çakışması** (bu denetim Faz 0'da gerçek bir çakışma yakaladı: `conn_temp` ↔ `conn_dt`)
- blok başına nokta sayısı register sayısını aşıyor mu, `points_ref` çözülüyor mu, `offset < count` mü
- `arc_mirror` gerçekten `read_only` mi ve **`command` dışında yazılabilir blok var mı** (GK6: koruma devresine yazma yok)
- alarm **bit çakışması**, bitlerin `bitmap.live_registers`'a sığması, `P1`'in bastırılamaz olması
- hipotez ve otomatik aksiyonların **var olmayan alarm koduna** atıf yapması, alarmların **var olmayan eşiğe** atıf yapması
- çapraz tutarlılık: Modbus nokta adları MQTT şemasının `pt` desenine, alarm kodları hem MQTT hem senaryo etiketi desenine uyuyor mu
- OpenAPI'de frontend'in güvendiği 9 ucun ve WebSocket sözleşmesinin varlığı
- `version` alanlarının mevcudiyeti
