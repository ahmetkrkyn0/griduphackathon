# 18 Eylül 2026 — Onay/raf kimliği gövdeden değil kimlik belirtecinden alınır (F-19)

**Dosya:** `contracts/openapi.yaml`
**Öneren:** Kişi A (Tuna)
**Durum:** **KABUL EDİLDİ ve UYGULANDI — 18 Eylül 2026**
**Sürüm etkisi:** `1.1.0` → `1.2.0`

**Ne değişiyor:**
1. `POST /alarms/{id}/ack` ve `POST /alarms/{id}/shelve` gövdelerinden **`by` alanı kalkıyor**.
2. Her iki uca `security: [operatorToken]` ekleniyor; `components.securitySchemes.operatorToken`
   (HTTP bearer) tanımlanıyor.
3. İki yeni ortak yanıt: `Unauthorized` (401) ve `Forbidden` (403).

**Neden:** Onaylayanın adını **istemci yazıyordu**. `by: str = Field(min_length=1)` tek kısıtı
"boş olmasın"dı; denetim izine (`alarm_journal.by_user`) giren değer doğrulanmamış serbest
metindi. ISA-18.2 denetim izinin taşıdığı kimlik doğrulanabilir olmalıdır.

**Etkilenen kulvarlar:** B (backend uçları), C (istemci ve iki ekran)
**Geri uyumlu mu:** **hayır.** İstemci artık `Authorization` başlığı gönderir.

**Onaylar:** [x] A  [x] B  [x] C

---

## Bu, depoda zaten iki kez uygulanmış bir ilkenin üçüncü kanala taşınmasıdır

Bu maddenin "yeni bir güvenlik mimarisi" olmadığını görmek önemli — kod tabanı bu ilkeyi
zaten iki yerde uyguluyordu ve **HTTP tek istisnaydı**:

| Kanal | `by` nereden geliyor | Dosya |
|---|---|---|
| SCADA (Modbus) | TCP oturumunun peer adresi | `backend/app/scada/gateway.py` |
| SMS | Beyaz listeye doğrulanmış gönderen numara; kayıtsız numara **yok sayılır** | `backend/app/notify/dispatcher.py` |
| HTTP | ~~istek gövdesi~~ → **doğrulanmış Authorization başlığı** | `backend/app/auth.py` (bu değişiklik) |

## Mekanizma ve neden OIDC/SSO değil

**GK4 public cloud'u yasaklıyor:** Auth0 / Entra / Cognito kullanılamaz. On-prem bir OIDC
sağlayıcısı (Keycloak vb.) kurmak yeni bir servis, yeni bir bağımlılık ve yeni bir işletim
yükü demektir; `backend/requirements.txt` de kilitli bir dosyadır.

Bu yüzden **yeni bağımlılık eklenmedi**: taşıyıcı belirteç, yapılandırmadan okunan bir
operatör tablosuna karşı doğrulanır. Karşılaştırma `hmac.compare_digest` ile sabit zamanlıdır
ve arama döngüsü erken kesilmez (erken kesilseydi sabit zamanlılık bozulurdu).

Roller `docs/15-guvenlik-kvkk.md` §2 C4 satırındaki üçlüdür: **izleyici < operator < muhendis**.

## Bunun OLMADIĞI şey — dürüstlük sınırları

Bunlar eksiklik değil, bu dilimin **beyan edilmiş kapsamıdır**; `docs/15` §5'te de yazar:

1. **Kurumsal SSO / OIDC / LDAP değildir.** Belirteçler yapılandırmada duran **paylaşılan
   sırlardır**. Kullanıcı parolası, parola özeti, oturum süresi, belirteç yenileme, iptal
   listesi ve hesap kilitleme **yoktur**.
2. **Yalnızca yazma uçlarını korur.** Filo listesi, pano detayı, seri, kara kutu, KPI,
   cihaz sağlığı ve WebSocket akışı belirteç istemez. Bu testle kilitli
   (`test_reads_stay_open_and_this_is_a_declared_limit`) ki ileride yanlışlıkla değişirse
   fark edilsin.
3. **Ekranlarda role göre gizleme yapılmadı.** Backlog F-19'un "ekranlarda role göre gizlenen
   eylemler" vaadi bu dilimde **karşılanmadı**; arayüz belirteci gönderir ve 401/403'ü
   gösterir, ama izleyici rolündeki bir kullanıcıya onay düğmesi yine görünür (basınca
   403 alır). Yetki kararı **sunucudadır**, ki doğru yer orasıdır; eksik olan arayüz cilasıdır.
4. **Grafana hâlâ anonim izleyici** (`deploy/compose.yaml` `GF_AUTH_ANONYMOUS_ENABLED`).
   Bu değişiklik ona dokunmadı.
5. **TLS yok.** Belirteç düz HTTP üzerinde gider. Demo tek makinede çalışır (GK4); sahada
   HTTPS şarttır ve `docs/15` §5 bunu zaten üretim farkı olarak yazıyor. **Belirteç
   doğrulaması, taşımanın şifreli olduğu iddiası değildir.**

## Operatör tablosu boşken kimlik doğrulama KAPALIDIR — ve bu görünür

`GRIDUP_OPERATORS` tanımsızsa kimlik doğrulama kapanır ve yazma uçları belirteçsiz çalışır.
Gerekçe GK4'tür: yığın, sertifika/belirteç dağıtmadan tek komutla ayağa kalkabilmelidir.

**Bu sessiz bir varsayılan değildir:**
- `GET /health` → `auth: {enabled: false, users: [], protects: [...]}`
- Başlangıçta `WARNING` seviyesinde log.
- Denetim izine yazılan ad **`"anonim (kimlik dogrulama kapali)"`** olur. Bunun gerçek bir
  kullanıcı adına benzememesi kasıtlıdır: kayda bakan biri değerin doğrulanmamış olduğunu
  görmelidir. Eski davranışta oraya istemcinin yazdığı `"kontrol-odasi"` düşüyordu ve bu,
  doğrulanmamış bir adın doğrulanmış gibi görünmesiydi.

## Bozuk yapılandırma satırı sessizce atlanmaz

`GRIDUP_OPERATORS` içinde hatalı bir satır `ValueError` atar ve servis açılmaz. Gerekçe,
`contracts/README.md`'deki "sözleşme bozuksa servis başlamaz" kuralının aynısıdır: yanlış
yazılmış bir satır yüzünden bir operatörün **sessizce yetkisiz kalması**, servisin hiç
açılmamasından daha kötüdür — çünkü ilkini ancak alarmı onaylamaya çalıştığında öğrenir.

## Ölçülen

- `scripts/check_contracts.py`: "SOZLESMELER TUTARLI", 10 uç.
- `backend/tests/test_auth.py`: **23 test**. Asıl kilit:
  `test_body_by_is_ignored_and_journal_gets_the_token_identity` — istemci gövdeye
  `"baskasinin.adi"` yazar, denetim izine **belirtecin sahibi** (`vardiya.amiri`) düşer.
- Reddedilen isteğin **yan etkisi yok**: 401/403 alan çağrıdan sonra alarm hâlâ onaysız.
