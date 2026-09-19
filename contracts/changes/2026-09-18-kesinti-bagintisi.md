# 18 Eylül 2026 — Üst şebeke kesintisi bağıntısı: aynı anda susan N pano tek olaydır (F-22)

**Dosya:** `contracts/alarm-codes.yaml`, `contracts/openapi.yaml`
**Öneren:** Kişi A (Tuna)
**Durum:** **KABUL EDİLDİ ve UYGULANDI — 18 Eylül 2026**
**Sürüm etkisi:** `alarm-codes.yaml` **v2 → v3** · `openapi.yaml` **1.3.0 → 1.4.0**

**Ne değişiyor:**
1. `alarm-codes.yaml` `thresholds:` altına **iki eşik**: `outage_min_panels` ve
   `outage_window_min`. **Yeni alarm kodu EKLENMEDİ** (gerekçe aşağıda).
2. `openapi.yaml`: `OutageEvent` şeması + `GET /api/v1/outages` ve
   `GET /api/v1/outages/{outage_id}`. `Alarm` şemasına `outage_id` alanı (alt alarmı
   olaya bağlar).

**Neden:** Olay gruplama bugün **pano içidir**; panolar arası hiçbir bağıntı yok. Bir fider
açıldığında merkez bunu **N ayrı arıza** olarak görür — oysa doğru yorum tersidir: N panonun
aynı anda susması, panoların değil **üst şebekenin** arızasıdır.

Bunun ölçülebilir bedeli sözleşmede yazılı: bir fider düştüğünde konsola **iki kod birden**
düşer — `ALM-COMMS-LOST` (bit 18, **SYS**, `sms: digest_only`) ve `ALM-LASTGASP`
(bit 20, **P2**, `sms: true`, `whatsapp: true`, `work_order: true`). Yani sel yalnızca günlük
özete düşen SYS akışı değil, **gerçek SMS üreten P2 akışıdır**: `ALM-LASTGASP` kenarın
gönderdiği "son nefes" olayıdır (`libs/panoalgo/panoalgo/limits.py`: *"besleme kesilme OLAYI,
eşik değil"*), yani her pano kendi başına bir P2 üretir.

**Etkilenen kulvarlar:** B (alarm servisi, depo, iki uç), C (bölge haritası)
**Geri uyumlu mu:** **evet.** Yalnızca ekleme; `outage_id` `required` değil ve bağıntı
kurulmayan alarmda yok.

**Onaylar:** [x] A  [x] B  [x] C

---

## Neden yeni bir alarm kodu EKLENMEDİ

Eklemek teknik olarak mümkündü (boş bit 22) ama **doğru araç değil**:

1. Kesinti bir **alarm** değil, alarmları **açıklayan bir olaydır**. Alt alarmlar
   (`ALM-LASTGASP`, `ALM-COMMS-LOST`) zaten var ve **doğrudur** — panolar gerçekten sustu.
   Üstlerine bir kod daha eklemek konsola **bir satır daha** koyardı; oysa madde konsoldaki
   satır sayısını **azaltmayı** hedefliyor.
2. Yeni kod `docs/04` (IEC 104 IOA 2000+bit) ve `docs/06` çıktılarını değiştirir ve SCADA
   nokta listesini büyütür. Bir **gruplama** kavramı için protokol yüzeyini genişletmek
   orantısızdır.

Bunun yerine kesinti **kendi tablosunda** (`outages`) yaşar ve alt alarmlar ona `outage_id`
ile bağlanır.

## Eşikler neden `alarm-codes.yaml`'da, `Settings`'te değil

Depodaki ayrım şudur: **fiziksel/alarm eşikleri** `alarm-codes.yaml`'da
(`heartbeat_timeout_min`, `term_rise_warn_k`…), **işletme ayarları** `Settings`'te
(`alarm_tick_s`, `digest_at`, `modbus_*`). "Kaç pano bir kesinti sayılır" ikisinin arasında
durur ve tartışılabilir.

Karar `alarm-codes.yaml` yönünde verildi, **mühendislik gerekçesiyle**: `AlarmService`
uygulama fabrikasında **`Settings` almadan** kuruluyor (`backend/app/main.py`) ama `Contracts`
**alıyor** ve `heartbeat_timeout_min`'i zaten oradan okuyor. Eşiği `Settings`'e koymak ya bir
imza değişikliği ya `digest_at` gibi ikinci bir ortam-okuma yolu gerektirirdi; `contracts`
üzerinden okumak **hiçbir yeni yol açmıyor** ve eşiği doğrudan ilgili olduğu
`heartbeat_timeout_min`'in yanına koyuyor. PLAN.md kural 10 ("eşik koda gömülmez") her iki
durumda da sağlanırdı; seçilen yol daha az hareketli parça içeriyor.

## İki eşik de TÜRETİLMİŞTİR, ölçülmemiştir

GK10 gereği açıkça yazılır — `neutral_current_ratio_warn` satırlarındaki aynı dürüstlük:

| Eşik | Değer | Nereden |
|---|---|---|
| `outage_min_panels` | 3 | **Türetilmiş.** İki pano rastlantı olabilir; üç pano aynı fiderde ve aynı pencerede susarsa üst şebeke açıklaması daha olasıdır. **Ölçülmedi** — bu depoda gerçek fider topolojisi ve gerçek kesinti kaydı yok (GK3). |
| `outage_window_min` | 2 | **Türetilmiş.** Fider açılması panoları fiilen eşzamanlı susturur; pencere telemetri periyodu (10 s) ve ağ gecikmesi için cömert bırakıldı. **Ölçülmedi.** |

## Tek panolu durumda eski davranış AYNEN korunur

Backlog'un "Dikkat" satırının şartı. `outage_min_panels = 3` olduğu için tek bir panonun
susması **hiçbir zaman** kesinti olayı doğurmaz ve `ALM-COMMS-LOST` bugünkü gibi üretilir.
Bu, adı konmuş bir regresyon testiyle kilitlidir:
`test_tek_pano_susunca_eski_davranis_aynen_korunur`.

## Fider bilgisi yoksa bağıntı KURULMAZ

Bağıntı `panels.fider_id` üzerinden yapılır ve bu alan **F-21'in içe aktardığı** künyeden
gelir. Künyesi olmayan panolar **gruplanmaz**: aynı anda sustukları için "aynı fiderdedir"
diye varsaymak, ölçmediğimiz bir topolojiyi uydurmak olurdu. **Bu teslimde demo filosunun
künyesi boş olduğu için bağıntı demo veritabanında hiç tetiklenmez** ve bu gizlenmiyor —
`GET /outages` boş döner, davranış testlerle gösterilir.

Bu aynı zamanda beyan edilmiş bir **risk**tir: yanlış fider eşlemesi, N panoyu yanlış tek
olaya toplar. Bağıntı gerçek bir şebeke topolojisinden değil, **içe aktarılmış bir etiketten**
türer.

## Bu dilimde YAPILMAYAN — alarm bastırma

Kesinti olayı alt alarmları **bağlar, bastırmaz**. Alarmlar aynen üretilmeye devam eder ve
bildirim davranışı **değişmez**. Bastırma bir ISA-18.2 kararıdır (hangi alarmın, hangi koşulda,
kim tarafından bastırıldığı denetlenebilir olmalı) ve en yüksek öncelikli alarmın asla
bastırılmadığı bir durum makinesi ister — bu, iş emri ve bakım penceresi maddesinin (F-25)
konusudur. Bu dilimde bağıntı **toplayıcıdır, susturucu değil**: konsol ve harita tek olayı
gösterir, ama hiçbir alarm kaybolmaz.

`/fleet/kpi` `comms_ok_pct` **yeniden yazılmadı** — "eşzamanlı sessiz pano sayısı" göstergesi
zaten orada ve Grafana "Haberleşme sağlığı" panelinde görünüyor.

## Denetim izi (F-20 hash zinciri) etkilenmedi

`alarm_journal.alarm_id` **NOT NULL REFERENCES alarms(id)** olduğu için alarma bağlı olmayan
bir denetim izi satırı yazılamaz. Kesinti olayı **kendi tablosunda** yaşar ve
`alarm_journal`'a **yazmaz**; alt alarmlar ise bugünkü yoldan (tek yazıcı
`PgStore.save_alarm_changes`, advisory kilit + `link_hash` sırası) journal'a yazmaya devam
eder. Yani zincir **ne çatallandı ne de anlamı değişti**; `scripts/verify_journal.py` aynen
çalışır.

## Ölçülen

- `scripts/check_contracts.py`: "SOZLESMELER TUTARLI", 13 uç.
- Beş üreteç de `--check` "guncel".
- `backend/tests/test_outage.py`: bağıntı, tek panolu regresyon, fider eşiği, pencere sınırı
  ve künyesiz panonun gruplanmaması kilitli.
