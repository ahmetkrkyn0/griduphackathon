# 10 — BOM, Maliyet ve ROI

> **Sahip:** Kişi C · BOM kaynağı: `hardware/pano-beyni/bom.csv` (elle düzenlenmez, oradan okunur).

## 1. Ürün paketleri (SKU)

| Paket | İçerik | Hedef |
|---|---|---|
| **Temel** | Pano Beyni + 2 ortam düğümü (T/RH/çiy noktası) + kapı sensörü + MPR-53CS/TVOC-2 Modbus okuma + termal dizi (1–2 adet) | Tüm AG panolar (yaygınlaştırma) |
| **Standart** | Temel + ana giriş ve kritik fiderlerde kablosuz bağlantı sıcaklık düğümleri (S1) + fider AT'leri (S8) | Yüksek yüklü / kritik müşterili trafolar |
| **OG+PD** | Standart + PD kartı + HFCT (rapor §3.7, bu teslimde yalnızca tasarım notu — Won't) | OG hücreli trafo merkezleri, eski kablo başlıkları |

## 2. Malzeme listesi (BOM)

Tam liste ve gerçek üretici kodları: [`hardware/pano-beyni/bom.csv`](../hardware/pano-beyni/bom.csv).
Pano Beyni kontrolcü kartı için özet:

| Ölçek | Birim maliyet (yaklaşık) |
|---|---|
| Adet 1 (prototip) | **70,73 USD**/kontrolcü kartı |
| Adet 1.000 | **47,68 USD**/kontrolcü kartı |

Bu rakamlar `bom.csv` satır kalemlerinin toplamıdır (hücresel modem dahil) ve artık **testle kilitlidir**:
`backend/tests/test_tazminat_maruziyeti.py::test_bom_toplami_csv_toplam_satirindaki_metinle_ayni` üç BOM'un
da dipnotunu satır toplamıyla karşılaştırır (bu depoda dipnot bir kez satır toplamından sapmıştı: 56/37
yazarken gerçek 70,73/47,68 idi).

Bu tablo **yalnızca kontrolcü kartıdır.** Sensör düğümü ve PD kartı ayrı BOM'lardır ve ikisi de artık
`hardware/` altında ölçülüdür — pano başına **toplam** maliyet ve geri ödeme **§7**'dedir.
SIM/veri aboneliği, kurulum işçiliği, montaj malzemesi ve tip test/sertifikasyon **hiçbir BOM'da yoktur**
ve hiçbir toplamda sayılmaz ([`docs/19`](19-tedas-sartname-uyumu.md) §3.1).

> **Düzeltilen etiket (19 Eylül 2026).** Bu paragraf daha önce sensör düğümlerini *"kavramsal seviyede"*
> diye işaretliyordu; `hardware/sensor-dugumu/` bugün **boş değildir** ve deponun kendi olgunluk ölçütünü
> karşılar: blok diyagramı + I/O tablosu + BOM üçlüsü, ki bu ölçütü [`hardware/pano-beyni/README.md`](../hardware/pano-beyni/README.md)
> tanımlamıştır ve pano-beyni de aynı üçlüyle "kavramsal" sayılmaz. Düğüm dizini ayrıca bir **enerji ve
> termal hesap** taşır (pano-beyni'nde bunun dengi yoktur). **Değişmeyen sınır:** hiçbir üretici veri
> sayfası doğrulanmadı, kart üretilmedi, tip testi yapılmadı — bu ayrı bir eksendir ve `docs/19` §3'te
> madde madde açıktır. "Tasarlanmadı" ile "doğrulanmadı" aynı şey değildir; doğru olan ikincisidir.

## 3. Maliyet ve fayda (ROI) — parametrik formül

Rapor §6.9'daki formül:

```
Yıllık beklenen fayda =
  Σ_pano [ P(arıza) × (ekipman maliyeti + arıza onarım işçiliği + kesinti tazminatı
                        + enerji satışı kaybı) × tespit oranı ]
  + planlı bakım verimliliği (yıllık termografi turlarının azalması)
```

**Kesinti tazminatı dayanağı:** EPDK Dağıtım ve Perakende Satış Faaliyetlerine İlişkin Kalite
Yönetmeliği (Ekim 2025 değişikliği) kapsamında, yıllık kesinti eşiğini ve 12 saati aşan uzun
kesintileri aşan dağıtım şirketi, aboneye **başvuru beklemeden tazminat** öder. Bir 1600 kVA
trafo yüzlerce aboneyi besler; önlenen her arıza bu tazminatı doğrudan azaltır.

### Örnek hesap (varsayımsal, jüri kendi sayısını girebilir)

| Parametre | Örnek değer |
|---|---|
| Pano başına yıllık arıza olasılığı P(arıza) | %3 |
| Arıza başına ortalama maliyet (ekipman + işçilik + tazminat) | 8.000 USD |
| Sistemin tespit oranı — **ölçülen** ([`docs/12`](12-dogrulama-sonuclari.md) §1) | **İki bloktur** (19 Eylül'de böyle oldu): **eşleşen** modelde recall **1,00** (beklenen alarmı olan 8 senaryonun 8'i), dedektörün varsaymadığı fizik eklendiğinde (**uyumsuz** blok) S13'te **0,50**'ye iniyor. Tek bir "1,00" yazmak artık yanıltıcıdır |
| Sistemin tespit oranı — **hesapta kullanılan** | **%70** — bilinçli iskonto, ölçülen değer değil. Gerekçe: ölçüm sentetik ve etiketli 10 senaryo üzerindedir; saha çeşitliliği, sensör arızası ve bakım gecikmesi bu orana dahil değildir |
| Pano başına yıllık beklenen önlenen kayıp | 0,03 × 8.000 × 0,70 ≈ **168 USD/pano/yıl** (aynı hesap ölçülen 1,00 ile 240 USD/pano/yıl verir; tabloda temkinli olan kullanıldı) |
| Pano başına sistem maliyeti (Temel paket, adet 1.000) | 47,68 USD **yalnızca kontrolcü** — pano başına toplam **§7**'dedir ve düğüm sayısına göre **103,48 – 396,43 USD** arasındadır |
| Basit geri ödeme | **Bu satır kaldırıldı.** Eskiden *"< 1 yıl"* yazıyordu; sayı yalnızca kontrolcü maliyetiyle hesaplanmıştı, yani paydası eksikti. Hesap artık **§7**'de **yürütülebilir** ve aralık olarak yayımlanıyor |

> **Not:** Bu tablo bir hesaplayıcı taslağıdır; gerçek P(arıza) ve arıza maliyeti ADM/GDZ'nin
> kendi saha verisiyle doldurulmalıdır (rapor §6.9). Sayılar iddia değil, örnektir.
>
> **Düzeltilen çelişki (19 Eylül 2026).** `README.md` *"geri ödeme süresi bu depoda hesaplanmamıştır"*
> derken bu tablo bir geri ödeme süresi (*"< 1 yıl"*) yayımlıyordu; ikisi aynı anda doğru olamazdı.
> Çözüm, sayıyı kurtarmak değil **hesabı yürütülebilir kılmak** oldu: `scripts/tazminat_maruziyeti.py`
> artık geri ödemeyi hesaplıyor, ama yalnızca P(arıza), arıza başı maliyet ve tespit oranı **dışarıdan
> verilirse**; verilmezse `veri yok` diyor. Üçü de bu tabloda duran varsayımlardır ve §7'de etiketleriyle
> birlikte basılırlar.

## 4. Ölçeklenebilirlik ile ilişkisi

Birim maliyetin adet 1.000'de düşmesi (70,73 → 47,68 USD, **%32,6** azalma), `docs/09-olceklenebilirlik.md`'deki (Kişi B)
1.000 sanal pano yük testiyle birlikte okunmalıdır: donanım maliyeti düşerken sunucu tarafı da
aynı ölçekte doğrusala yakın büyüyor (bkz. o doküman), yani birim ekonomi saha sayısı arttıkça
iyileşiyor.

## 5. Tazminat maruziyeti hesaplayıcısı (parametreli)

§3'teki örnek hesap "önlenen arıza" üzerine kuruludur ve bunu kendisi varsayım olarak işaretler. Bu bölüm
ölçülebilir olan soruyu sorar: **bu pano kesilirse, yönetmeliğe göre ne kadar tazminat doğar?** Fayda kalemi
bizim modelimize değil, dışarıda yayımlanmış bir kurala bağlanır.

Hesaplayıcı: [`scripts/tazminat_maruziyeti.py`](../scripts/tazminat_maruziyeti.py) (stdlib + mevcut harita
yükleyici + `PyYAML`; **yeni bağımlılık yok** — PyYAML zaten `backend/requirements.txt`'te ve harita
yükleyicinin kendisi onu kullanıyor).

### 5.1 Formül — EPDK Kalite Yönetmeliği'nin süre ve sayı kalemleri

```
ÖTMSÜRE = abone sayısı × abone başına ortalama talep (kW) × dağıtım bedeli (TL/kWh) × eşiği aşan süre (saat)
ÖTMSAYI = abone sayısı × eşiği aşan kesinti sayısı × kesinti başına tazminat (TL/abone)
maruziyet = ÖTMSÜRE + ÖTMSAYI
```

Eşikler, dağıtım bedeli ve abone başına ortalama talep **bu depoda yoktur**; yürürlükteki yönetmelik ve tarife
metninden girilir. Betik hiçbirini varsaymaz — parametresiz çalıştırıldığında hesap yapmaz, 1 ile çıkar:

```
$ python scripts/tazminat_maruziyeti.py --yalniz maruziyet
TAZMINAT MARUZIYETI - EPDK Kalite Yonetmeligi, sure (OTMSURE) ve sayi (OTMSAYI) kalemleri
Pano: veri yok   Para birimi: TL
  veri yok: hesap icin gereken parametreler girilmedi (--abone, --dagitim-bedeli, --esik-saat, --esik-sayi, --kesinti-basi-tazminat, --kesinti-saat, --kesinti-sayisi, --ortalama-talep-kw)
  Yonetmeligin esikleri, dagitim bedeli ve ortalama talep bu depoda yoktur; betik bunlari uydurmaz.
```

Jüri kendi tarifesini ve eşiğini girdiğinde her iki kalem de ayrı ayrı, çarpanları görünür biçimde yazılır:

```
python scripts/tazminat_maruziyeti.py --pano ADM-00001 --abone <n> --kesinti-saat <saat> --esik-saat <saat> --ortalama-talep-kw <kW> --dagitim-bedeli <TL/kWh> --kesinti-sayisi <n> --esik-sayi <n> --kesinti-basi-tazminat <TL>
```

**Dil kuralı:** çıktı yalnızca *maruziyet* der. "Şu kadar arıza önledik" cümlesi ne betikte ne bu bölümde
geçer; önlenen arıza bu teslimde ölçülemez (GK10). Erken uyarının değeri, bu maruziyetin **doğmadan önce**
görülebilmesidir; kaç kez doğmasını engellediğimiz sahada ölçülecek bir sayıdır, burada değil.

### 5.2 Eklenmediği için ödenmeyen kalemler (BOM farkı)

Mevcut enerji analizörü (MPR-53CS) ve ark koruma rölesi (TVOC-2) Modbus üzerinden **sensör olarak** okunuyor
([`contracts/modbus-map.yaml`](../contracts/modbus-map.yaml) içindeki `source:` alanları). BOM'a bu yüzden
girmeyen kalemler ve haritadan sayılan adetleri:

| Eklenmeyen kalem | Adet | Nereden sayıldı | Birim fiyat |
|---|---|---|---|
| Akım trafosu (faz + nötr) | 4 | `electrical_mirror` ← MPR-53CS (`i_l1_a`, `i_l2_a`, `i_l3_a`, `i_n_a`) | depoda yok |
| Gerilim ölçüm girişi | 3 | `electrical_mirror` ← MPR-53CS (`u_l1_v`…`u_l3_v`) | depoda yok |
| Ark dedektörü | 2 | `arc_mirror` ← TVOC-2 (`sensor_status_x2`, `sensor_status_x3`) | depoda yok |
| Ark koruma merkez ünitesi | 1 | `arc_mirror` ← TVOC-2 (`system_state`) | depoda yok |
| Ek kablaj ve işçilik | ölçülmedi | kablo boyu ve işçilik depoda kayıtlı değil | depoda yok |

Buna karşılık **ödenen** kalem ölçülüdür: `bom.csv`'deki izole RS485 arayüzü — **4,90 USD** (adet 1) /
**3,70 USD** (adet 1.000), yani kontrolcü kartının adet 1.000 maliyetinin (47,68 USD) yaklaşık **%8**'i.
BOM'da bu parçadan 2 adet var; ikincisi SCADA ağ geçidinin slave portudur, yeniden kullanımın bedeli değildir.

Kaçınılan kalemlerin birim fiyatı depoda olmadığı için **net fark "veri yok"**tur. Fiyat girilirse betik
kaçınılan toplamı ve net farkı yazar:

```
python scripts/tazminat_maruziyeti.py --yalniz bom --at-fiyat <USD> --gerilim-fiyat <USD> --ark-dedektor-fiyat <USD> --ark-unite-fiyat <USD>
```

**Dürüstlük notu:** `bom.csv`'de 3 adet INA226 akım/gerilim ADC'si *opsiyonel* olarak duruyor (fider CT
girişleri; 1,35 USD adet 1 / 0,90 USD adet 1.000). MPR-53CS okunduğu için Temel pakette kullanılmıyor — yani
"akım trafosu eklemedik" cümlesi, kartın CT giriş yolunu tamamen kaldırdığımız anlamına gelmez.

### 5.3 Başa baş eşiği — kaçınılan kalemleri fiyatsız değerlendirmek

Yukarıdaki tablonun dört satırı `veri yok` fiyatla duruyor ve bu **kalıcı bir eksiklik değil, bilinçli bir
sınırdır**: bu oturumda hiçbir tedarikçi teklifine veya kataloğa erişilmedi, dolayısıyla akım trafosunun
birim fiyatı yazılmadı. Aynı disiplin `docs/19` §3'te de geçerlidir (17 BOM satırının 17'si "doğrulanmadı",
çünkü hiçbir veri sayfasına erişilmedi).

Ama **fiyat bilinmeden de savunulabilir bir sayı vardır** ve hesaplayıcı artık onu basıyor:

```
BASA BAS ESIGI (fiyat gerektirmez, tamami olculur): 10 kalemin ORTALAMA birim fiyati
  0.49 USD (adet 1) / 0.37 USD (adet 1.000)
  degerini gectigi anda mevcut cihazi okumak kendini oder.
```

Eşiğin **payı** ödenen arayüzün `bom.csv`'deki fiyatıdır (izole RS485, 4,90 / 3,70 USD), **paydası**
sözleşmeden sayılan kalem adedidir (4 + 3 + 2 + 1 = **10**). İkisi de ölçülüdür; hiçbir dış fiyata ihtiyaç
duymaz.

> **Eşiğin payına dair bir çekince (kendi dürüstlük notumuzdan çıkarıldı).** §5.2'nin sonundaki not,
> `bom.csv`'de 3 adet INA226 akım/gerilim ADC'sinin *opsiyonel* olarak durduğunu ve MPR-53CS okunduğu için
> Temel pakette kullanılmadığını söylüyor. Ama bu üç kalem BOM satırı olarak duruyor ve 47,68 USD toplamına
> **giriyor** (3 × 0,90 = 2,70 USD). İkisinden biri doğrudur: ya kullanılmıyorlardır ve yayımlanan toplamlar
> 2,70 USD fazladır, ya kullanılıyorlardır ve mevcut cihazı okumanın bedeli yalnızca RS485 değildir — o
> zaman eşik 0,37 değil **(3,70 + 2,70) / 10 = 0,64 USD** olur. **Karar verilmedi ve verilmemesi gerekir:**
> bu, kart yerleşimi netleşince kapanacak bir tasarım sorusudur, burada seçilecek bir sayı değil. Eşiğin
> **üst** değeri olarak 0,64 USD'yi de aklınızda tutun; argüman her iki değerde de aynı yönde durur. Okunuşu şudur: *kaçınılan on kalemin ortalama birim fiyatı 0,37 USD'yi geçtiği anda mevcut cihazı
Modbus'tan okumak kendini ödemiştir.* Bu eşiğin altında bir ölçüm sınıfı akım trafosu, ark dedektörü veya
ark koruma merkez ünitesi **yoktur** — ama bunu söyleyen biz değiliz, okuyucunun kendi piyasa bilgisidir.
Eşik, yargıyı jüriye devreder ve bizim uydurmamız gereken tek bir sayı bırakmaz.

**Fiyat girilirse** betik net farkı zaten hesaplıyordu; parametre dosyasıyla da girilebilir:

```bash
python scripts/tazminat_maruziyeti.py --yalniz bom --at-fiyat <USD> --gerilim-fiyat <USD> \
    --ark-dedektor-fiyat <USD> --ark-unite-fiyat <USD>
```

`scripts/roi-ornek-parametreler.yaml` bu dört alanı `deger: null` + `guven: isletmeci-doldurur` olarak
tutar ve **kaynak sütununda ne aranacağını yazar** (örneğin akım trafosu için: oran, doğruluk sınıfı ve
burden). Fiyat arayan kişi ne soracağını bilir; betik ise doldurulmadıkça `veri yok` demeye devam eder.

---

## 6. OPEX — işletme gideri (ölçülen hacim, işletmecinin tarifesi)

§2–§5 **CAPEX** tarafıdır. Bir dağıtım şirketinin ikinci sorusu işletme gideridir ve bu bölümün tamamı tek
bir kurala uyar: **hacim ölçülmüştür, fiyat ölçülmemiştir.** Hiçbir tarife bu depoda yoktur; hücreler boş
bırakıldı ve "işletmeci doldurur" yazıldı.

### 6.1 Kalem kalem

| Kalem | Miktar (pano/yıl) | 1.000 pano / yıl | Birim fiyat | Tutar | Kaynak |
|---|---|---|---|---|---|
| Hücresel veri — **sabit 10 s** · *bugün teslim edilen davranış* | **12,85 GB** (1.071 MB/ay × 12) | 12.852 GB | işletmeci doldurur (M2M TL/GB) | işletmeci doldurur | [`docs/09`](09-olceklenebilirlik.md) §6.1 |
| Hücresel veri — **uyarlanabilir %2** · *`--adaptive` ile açılır, **varsayılan kapalı*** | **7,58 GB** (632 MB/ay × 12) | 7.584 GB | işletmeci doldurur (aynı tarife) | işletmeci doldurur | `docs/09` §6.1 |
| Sunucu — CPU | 1.000 panoda backend 0,16 (tepe 0,29) çekirdek + DB 0,05 (0,18) çekirdek | tek 4–8 vCPU VM yeter | işletmeci doldurur (VM/yıl) | işletmeci doldurur | `docs/09` §7 |
| Sunucu — RAM | 1.000 panoda DB 0,6 GB (5.000 panoda 2,1 GB) | — | işletmeci doldurur | işletmeci doldurur | `docs/09` §7 |
| Sunucu — disk (kurulu politika, 1. yıl) | **2,9 GB/pano/yıl** (25 nokta) · 1,18 GB/pano/yıl (7 nokta) | 2,9 TB (25 nokta) · 1,18 TB (7 nokta) | işletmeci doldurur (TB/yıl) | işletmeci doldurur | `docs/09` §5.2 |
| Bakım / kalibrasyon | **ölçülmedi** — periyot, düğüm başına ücret ve akredite laboratuvar bedeli depoda yok | — | işletmeci doldurur | işletmeci doldurur | `backend/app/api/nodes.py` |
| SIM aboneliği (veri hariç hat bedeli) | **ölçülmedi** | — | işletmeci doldurur | işletmeci doldurur | — |
| Saha işçiliği, yol-ziyaret, yedek parça | **ölçülmedi** — MTBF verisi depoda yok | — | işletmeci doldurur | işletmeci doldurur | — |

Vade takibinin **alanı** vardır, **bedeli** yoktur: `GET /api/v1/fleet/nodes` her düğüm için
`son_kalibrasyon_at` / `sonraki_kalibrasyon_at` tutar ve vadesi boş düğümleri sayar. Uç, yanıtının içinde
kendi sınırını da yazar: bu bir **vade takibidir**, akredite bir kalibrasyon zinciri olmadan "izlenebilir
ölçüm" iddiası kurulmaz. Kütük bu teslimde **boştur** (uydurma seri no üretilmedi), dolayısıyla düğüm
başına yıllık bir kalibrasyon maliyeti türetilemez.

### 6.2 Ölçülmüş maliyet-fayda önermesi: uyarlanabilir yayın

Bu, OPEX tarafındaki **tek ölçülmüş kaldıraçtır** ve gücü tarifeyi bilmeye ihtiyaç duymamasındadır:

> Uyarlanabilir yayın (%2 ölü bant) hücresel hacmi **%41,0 düşürür** ve **tespit hızını değiştirmez.**

Her iki yarısı da ölçüldü, ikincisi birincisinden önemlidir: arıza rejiminde **dokuz alarm kodunun tamamı
beş politikada da aynı turda** yayınlandı (`ALM-THR-TERM-ALM` beşinde de 15.161. turda, ≈42. saat).
Seyrelen yalnızca **yayındır**; tespit kenarda 10 saniyede koşmaya devam eder. Yani bu bir *ödünleşim
değildir* — bedeli ölçüldü ve **sıfır çıktı**.

Tarife bilinmeden de söylenebilecek olan şudur — **eşik tarife**:

| Politika | Hacim (pano/yıl) | §3'ün varsayımsal faydasını (168 USD/pano/yıl) sıfırlayan tarife |
|---|---:|---:|
| Sabit 10 s | 12,85 GB | **13,07 USD/GB** |
| Uyarlanabilir %2 | 7,58 GB | **22,15 USD/GB** |

Okunuşu: *uyarlanabilir yayın, projeyi zarara sokan tarife eşiğini **1,69 kat** yukarı taşır.* Bu oran
ölçülmüştür — iki eşiğin oranı, iki **hacmin** oranıdır (12.852 / 7.584 = 1,6946). `docs/09` §6.1 aynı
kaldıracı **mesaj sayısı** üzerinden verir ve **1,70×** diye yuvarlar (86.400 / 50.932 = 1,6964); ikisi
aynı büyüklük değildir, ondalıktaki fark buradan gelir. **168 USD ise varsayımdır** (§3) — fayda
değişirse iki eşik de aynı oranda değişir, aralarındaki 1,69 kat **değişmez**.

### 6.3 Bu bölümün ölçmediği altı şey (fatura bu sayılardan YÜKSEK çıkar)

Buradaki hacim bir **alt sınırdır**. Altı sebep, hepsi `docs/09`'un kendi notlarından:

1. **"Faturalanan" sütunu bir tahmin içerir:** MQTT baytına mesaj başına ~110 B TCP/IP+TLS+ACK eklendi;
   bu **ölçüm değil tahmindir** (`docs/09` §6).
2. **Bayt muhasebesi sıkıştırılmış JSON üzerinedir.** Sahadaki yayıncı (`sim/panosim.py`) boşluklu
   `json.dumps` kullanır ve bu **ölçüldü: 1,139 kat** büyüktür. Tarifeyi 632 MB ile çarpan kişi gerçek
   hacmi ~%14 eksik yazar.
3. **Operatörün yuvarlaması modellenmedi:** KB'a yuvarlama, asgari oturum bedeli, oturum kurma trafiği.
4. **632 MB, 25 noktalı pano içindir.** 7 noktalı panoda uyarlanabilir yayının oranı **ölçülmedi**;
   nokta sayısı azaldıkça ölü bandı aşma şansı düştüğü için tasarruf **daha iyi** olabilir — ama bu bir
   beklentidir, ölçüm değildir.
5. **mTLS ek yükü ölçülmedi.** Bütün yük ve bayt ölçümleri düz 1883 üzerinden alındı; mTLS kipinde
   topoloji de değişir (N pano = N bağlantı, bugünkü paylaşılan bağlantı değil).
6. **Sunucu sayıları iş istasyonunda ölçüldü** ve koşular 2–5 dakikadır; 24 saatlik etkiler (sıkıştırma
   işinin kendisi, autovacuum, parça oluşturma) ölçümün dışındadır (`docs/09` §8).

**Yeniden üretme.** Hacim ölçümünün ham çıktısı (`loadtest/results/`) depoya **girmez** (`.gitignore`),
yani bir klonda hazır bulunmaz; tablo komutla yeniden üretilir:

```bash
python loadtest/veri_butcesi.py       # 5 pano x 25 nokta, 7 gun isinma + 48 saat olcum, tohum 20260918
```

---

## 7. Pano başına toplam maliyet ve geri ödeme (ölçülen pay, varsayılan payda)

README uzun süre *"doğrulanmış bir pano başı toplam maliyet henüz yoktur"* dedi. Artık vardır — ama tek bir
sayı değil, **bir aralıktır**, çünkü eksik olan şey fiyat değil **yapılandırmaydı**: pano başına kaç sensör
düğümü takılacağı.

### 7.1 Düğüm sayısı N — ölçüldü, varsayılmadı

| Kaynak | N | Ne söylüyor |
|---|:--:|---|
| [`contracts/modbus-map.yaml`](../contracts/modbus-map.yaml) `conn_temp.points` | **25** | Sözleşmenin tanımladığı bağlantı noktalarının tamamı: ana giriş `GIRIS_L1/L2/L3/N` (4) + yedi DSYA çıkışı × üç faz (21). `check_contracts.py` bunu "25 izleme noktası" diye sayar |
| [`loadtest/fleet.py`](../loadtest/fleet.py) varsayılanı | **7** | Ana giriş (4) + ilk fider (`DSYA1_L1/L2/L3`). Az sensörlü pano; `docs/09` ölçümlerinin çoğu bu yapılandırmadadır |
| `loadtest/fleet.py` izin verilen aralık | **4–25** | 4'ün altı reddedilir, 25'in üstü sözleşmede yoktur |

Bir sensör düğümü bir bağlantı noktası ölçer (TMP117 bara teması) ve yanında ortam nem/sıcaklığını okur
(SHT40), yani **N = izlenen bağlantı noktası sayısı**. Betik N'i kendisi seçmez: `--dugum-sayisi`
verilmezse toplam `veri yok` döner ve sözleşmenin sınırlarını yazar.

> **Plandan sapan sonuç.** İş planı ([`Yapilacaklar.md`](../Yapilacaklar.md) §2 madde 8.3) N'i, `docs/10`
> §2'deki *"S1–S5"* ifadesinden **5** diye okumuştu ve pano başına ≈ **117,4 USD** öngörüyordu. Ölçüm bunu
> yanlışladı: *S1–S5* bir düğüm **sayısı** değil, raporun **senaryo/sensör türü** etiketidir; sözleşmede
> 5 noktalı bir yapılandırma **yoktur**. Gerçek aralık 103,48 – 396,43 USD'dir ve tahmin edilen 117,4 USD
> bu aralığın **alt ucuna yakın** düşer. Tek bir sayı yerine aralık yayımlıyoruz.

### 7.2 Pano başına toplam — ölçülen kalemler (adet 1.000)

| Yapılandırma | Kontrolcü | Sensör düğümü | PD kartı | **Toplam** | Geri ödeme* |
|---|---:|---:|---:|---:|---:|
| 4 düğüm (asgari) | 47,68 | 4 × 13,95 = 55,80 | — | **103,48 USD** | 7,4 ay |
| **7 düğüm (ölçümlerin çoğunun yapılandırması)** | 47,68 | 7 × 13,95 = **97,65** | — | **145,33 USD** | **10,4 ay** |
| 25 düğüm (sözleşmenin tamamı) | 47,68 | 25 × 13,95 = 348,75 | — | **396,43 USD** | 28,3 ay |
| 25 düğüm + PD (OG hücre) | 47,68 | 348,75 | 11,79 | **408,22 USD** | 29,2 ay |

\* §3'ün üç varsayımıyla (P(arıza) %3 · arıza başı 8.000 USD · tespit oranı %70 → 168 USD/pano/yıl) ve
**OPEX hariç**. OPEX girilirse geri ödeme uzar; tarife bu depoda yoktur (§6).

Adet 1 (prototip) karşılıkları: 7 düğümde **233,48 USD**, 25 düğümde **651,98 USD**
(70,73 + N × 23,25). Tabloya **girmeyen** dört kalem: kurulum işçiliği, SIM/veri aboneliği, montaj
malzemesi ve tip test/sertifikasyon — hiçbirinin BOM satırı yoktur, adet olarak bile sayılamadılar.

**Okunması gereken ilk sonuç:** pano başına maliyeti kontrolcü kartı değil **sensör düğümleri belirliyor**
— 7 düğümde toplamın **%67,2'si**, 25 düğümde **%88,0'ı**. Hackathon boyunca maliyet tartışması
kontrolcünün 47,68 USD'si üzerinden yürüdü; ölçüm bunun toplamın üçte birinden azı olduğunu gösterdi.

```bash
python scripts/tazminat_maruziyeti.py --yalniz maliyet --dugum-sayisi 7
python scripts/tazminat_maruziyeti.py --parametreler scripts/roi-ornek-parametreler.yaml
```

### 7.3 Duyarlılık — hangi varsayım sonucu belirliyor?

`--duyarlilik` her girdiyi **tek tek** ±%50 oynatır (diğerleri sabit) ve sonucun aralığını basar. Sorduğu
soru *"sonuç ne kadar kötüleşir"* değil, ***"sonucu hangi girdi belirliyor"***dur.

> **Ad çakışması uyarısı:** bu depoda "duyarlılık" sözcüğü başka bir yerde **recall** anlamında kullanılır
> (`README` §K2: "duyarlılık 1,00"). `--duyarlilik` bayrağı **parametre duyarlılığıdır**, tespit
> duyarlılığı değildir.

```
  Geri odeme (ay) - taban: 10.38

    Girdi                            Deger            -%50            +%50  Kaldirac  Guven
    ariza_olasiligi_yil               0.03           20.76            6.92     1.33x  varsayim
    ariza_basi_maliyet_usd            8000           20.76            6.92     1.33x  varsayim
    tespit_orani                       0.7           20.76            6.92     1.33x  varsayim
    dugum_sayisi                         7            7.39           14.37     0.67x  turetildi  [oynatilan deger: 4 / 11]

    OKUNUSU: 3 girdi BERABERE en cok belirliyor (1.33x): ariza_olasiligi_yil,
    ariza_basi_maliyet_usd, tespit_orani.
```

**Ölçümün söylediği üç şey:**

1. **Üç varsayımın kaldıracı birebir eşittir (1,33×).** Tesadüf değil, modelin yapısıdır: geri ödeme
   `maliyet / (P × L × r)` olduğu için her çarpanı ±%50 oynatmak aynı aralığı verir. Yani *"sonucu şu
   varsayım belirliyor"* denemez — **üçünün çarpımı** belirler. Bu, testle kilitlendi
   (`test_carpimsal_girdilerin_kaldiraci_esit_cikar`, beklenen değer tam olarak 4/3).
2. **Ölçülü tarafın kaldıracı daha küçüktür (0,67×).** Maliyet bir **toplamdır** (kontrolcü + N × düğüm),
   çarpım değil; bu yüzden N'i ±%50 oynatmak oransal etki etmez. Satırın sonundaki
   `[oynatilan deger: 4 / 11]` notu şuradan gelir: 7 düğümün −%50'si 3,5'tir ve **ne 3,5 düğüm vardır ne
   de betik 4'ün altını kabul eder**. Oynatılan değer önce yuvarlanır, sonra sözleşmenin 4–25 sınırlarına
   kırpılır ve hangi değerin kullanıldığı yazılır — aksi hâlde tablo, betiğin kendi geçersiz saydığı bir
   yapılandırmadan sayı türetirdi. (Bu kusuru bağımsız denetim buldu; ilk sürüm 3,5 düğümden hesaplıyordu.)
3. **Ama asıl belirleyici yine N'dir** — ve duyarlılık tablosu bunu *göstermez*, çünkü N bir belirsizlik
   değil bir **seçimdir**. Sözleşmenin izin verdiği 4 → 25 aralığı geri ödemeyi **7,4 aydan 28,3 aya**
   taşır (3,8 kat); ±%50'lik hiçbir varsayım bu kadar oynatmaz. Betik bunu ayrı bir tabloda, *"duyarlılık
   değil, seçim"* başlığıyla basar.

**Jüri masasında okunuşu:** *"Geri ödemeyi tek bir sayı olarak vermiyoruz. Maliyet tarafı ölçülü ve
103–396 USD arasında; nerede durduğunu kaç nokta izleyeceğiniz belirliyor. Fayda tarafı ölçülmedi ve üç
varsayımın çarpımı — üçünün de kaldıracı birebir eşit çıktı, yani biri düzeltilmeden hesap düzelmez. En
büyük tek kaldıraç ise bir belirsizlik bile değil: kaç düğüm taktığınız."*

### 7.4 Maruziyet tarafında: tarifenin kaldıracı **üstten sınırlı**, eşiğinki değil

Aynı bayrak §5'in tazminat maruziyeti hesabına uygulandığında da bir sonuç verdi — ama bu bölüm bir kez
**yanlış yazıldı ve düzeltildi**; hikâyesi sonucun kendisi kadar önemli.

**İlk yazılan (YANLIŞ):** tek bir örnek girdi setiyle koşuldu, `kesinti_sayisi` 2,02× ile en üstte,
`dagitim_bedeli` 0,19× ile en altta çıktı ve buradan *"değişmez olan sıralamadır"* diye genel bir sonuç
yazıldı. **Yanlışlandı:** bağımsız bir denetim aynı betiği başka bir makul girdi setiyle koştu —
`kesinti_basi_tazminat` 50 yerine 5 TL alındığında `dagitim_bedeli` **0,71×**'e çıkıp `esik_sayi`'yı
(0,59×) **geçiyor**. Sıralama bir ölçüm değil, seçilen örneğin artefaktıymış.

**Sonra ölçülen (DOĞRU).** Altı farklı parametre setinde tekrarlandığında değişmeyen üç şey var — ve
üçü de aritmetikten türüyor, örnekten değil:

| Girdi türü | Kaldıraç | Neden |
|---|---|---|
| `abone` | **her zaman tam 1,00×** | iki kalemi birden çarpan **tek** girdidir; ölçek değişir, oran değişmez |
| `dagitim_bedeli` · `ortalama_talep_kw` | **= ÖTMSÜRE'nin toplamdaki payı**, yani **≤ 1,00×** | yalnızca süre kalemini çarparlar |
| `kesinti_basi_tazminat` | **= ÖTMSAYI'nın payı** (= 1 − süre payı), yani **≤ 1,00×** | yalnızca sayı kalemini çarpar |
| `kesinti_saat` · `esik_saat` · `kesinti_sayisi` · `esik_sayi` | **sınırsız** — ölçülen aralık **0,09× – 3,57×** | `max(0, kesinti − eşik)` içindedirler; model burada **doğrusal değildir** |

Altı koşunun tamamında ölçülen kaldıraçlar (aynı kolonlar, farklı parametreler):

| Parametre seti | `abone` | tarife | `kesinti_basi` | `kesinti_sayisi` | `esik_sayi` | `kesinti_saat` | `esik_saat` | ÖTMSÜRE payı |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Örnek taban | 1,00 | 0,19 | 0,81 | **2,02** | 1,61 | 0,39 | 0,19 | 0,194 |
| `kesinti_basi` = 5 | 1,00 | **0,71** | 0,29 | 0,74 | 0,59 | **1,41** | 0,71 | 0,706 |
| `kesinti_basi` = 10 | 1,00 | 0,55 | 0,45 | **1,14** | 0,91 | 1,09 | 0,55 | 0,545 |
| Eşikten uzak (40 s) | 1,00 | 0,81 | 0,19 | 0,75 | 0,56 | **0,90** | 0,09 | 0,812 |
| Eşiğe yakın (5 s) | 1,00 | 0,11 | 0,89 | **3,57** | 2,68 | 0,38 | 0,32 | 0,107 |
| Tarife = 30 | 1,00 | 0,71 | 0,29 | 0,74 | 0,59 | **1,41** | 0,71 | 0,706 |

Her satırda en yüksek kaldıraç **koyu**: üç satırda bir eşik kalemi, üç satırda başka bir eşik kalemi —
ama **hiçbir satırda tarife değil**, ve olamaz da.

**"Tarifeyi bilmiyorsunuz" itirazının cevabı budur ve artık savunulabilir:** tarifeyi ±%50 yanlış bilmek
sonucu **en fazla** ±%50 oynatır (kaldıracı 1,00× ile sınırlıdır ve pratikte ondan küçüktür), eşiğe olan
mesafe ise **sınırsızdır** ve ölçümde 3,57×'e kadar çıktı. Yani tarife bu hesabın belirsizliğinin baskın
kaynağı **olamaz**; belirleyen şey panonun eşiğe ne kadar yakın olduğudur — ve eşiğe olan mesafe tam da
erken uyarının değiştirdiği büyüklüktür.

Testler bu sefer **örneği değil özelliği** kilitliyor
(`test_maruziyet_kaldiraclarinin_yapisal_sinirlari`, beş parametre setinde): `abone` her setde tam 1,00×,
düz çarpanların kaldıracı kendi kaleminin payına **birebir eşit**, ve eşik kalemleri en az bir setde
1,00×'i aşıyor.

```bash
python scripts/tazminat_maruziyeti.py --yalniz maruziyet --duyarlilik --pano ADM-00001 \
    --abone 412 --kesinti-saat 8 --esik-saat 4 --ortalama-talep-kw 2 --dagitim-bedeli 3 \
    --kesinti-sayisi 6 --esik-sayi 4 --kesinti-basi-tazminat 50
```

> **Kenar durum:** pano eşiğin **altındaysa** maruziyet 0'dır ve hiçbir girdinin kaldıracı tanımlı
> değildir; betik o hücrelere `veri yok` yazar, 0 yazmaz.

### 7.5 Parametre dosyası — üç sütun kuralı

[`scripts/roi-ornek-parametreler.yaml`](../scripts/roi-ornek-parametreler.yaml) jürinin çalıştırabileceği
bir başlangıç noktasıdır. Her girdi **üç sütun** taşır ve üçü de zorunludur:

| Sütun | Ne yazar |
|---|---|
| `deger` | sayı ya da `null` |
| `kaynak` | bu değerin nereden geldiği — depo içinde `dosya:satır`, dışarıda hangi belge |
| `guven` | `olculdu` · `turetildi` · `varsayim` · `ornek` · `isletmeci-doldurur` |

Kural betikte **denetlenir**, belgede tavsiye edilmez: `guven: isletmeci-doldurur` olan bir girdiye değer
yazılırsa dosya reddedilir. Aksi hâlde uydurulmuş bir sayı, kaynağı "işletmeci" gösterilerek tabloya
girebilirdi. Kaynaksız girdi de reddedilir. Beş denetimin tamamı testle kilitlidir
(`backend/tests/test_tazminat_maruziyeti.py`, 20 yeni test).

Örnek dosyada **tarife, yönetmelik eşiği ve kaçınılan kalem fiyatlarının tamamı `null`dur** ve testle öyle
tutulur (`test_ornek_dosyadaki_tarife_ve_esik_alanlari_hala_bos`): bu dosya doldurulmaya başlanırsa test
kırılır. Geri ödemeyi belirleyen üç sayı `guven: varsayim` etiketiyle durur ve raporun her satırında
etiketleriyle basılırlar.
