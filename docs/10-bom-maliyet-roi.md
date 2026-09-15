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
| Adet 1 (prototip) | ~56 USD/kontrolcü kartı |
| Adet 1.000 | ~37 USD/kontrolcü kartı |

Bu rakamlara sensör düğümleri (S1–S5), SIM/veri aboneliği ve kurulum işçiliği **dahil değildir**
(BOM yalnızca Pano Beyni kartını kapsar; sensör düğümleri bu teslimde kavramsal seviyede,
`hardware/sensor-dugumu/` içinde ayrı bir revizyon olarak planlanmıştır).

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
| Sistemin tespit oranı — **ölçülen** ([`docs/12`](12-dogrulama-sonuclari.md) §1) | Etiketli senaryo setinde **recall 1,00**: beklenen alarmı olan 8 senaryonun 8'inde kaçan yok, yasaklı alarm yok |
| Sistemin tespit oranı — **hesapta kullanılan** | **%70** — bilinçli iskonto, ölçülen değer değil. Gerekçe: ölçüm sentetik ve etiketli 10 senaryo üzerindedir; saha çeşitliliği, sensör arızası ve bakım gecikmesi bu orana dahil değildir |
| Pano başına yıllık beklenen önlenen kayıp | 0,03 × 8.000 × 0,70 ≈ **168 USD/pano/yıl** (aynı hesap ölçülen 1,00 ile 240 USD/pano/yıl verir; tabloda temkinli olan kullanıldı) |
| Pano başına sistem maliyeti (Temel paket, adet 1.000) | ~37 USD (yalnızca kontrolcü) + sensör/kurulum |
| Basit geri ödeme (yalnızca kontrolcü maliyetiyle) | < 1 yıl |

> **Not:** Bu tablo bir hesaplayıcı taslağıdır; gerçek P(arıza) ve arıza maliyeti ADM/GDZ'nin
> kendi saha verisiyle doldurulmalıdır (rapor §6.9). Sayılar iddia değil, örnektir.

## 4. Ölçeklenebilirlik ile ilişkisi

Birim maliyetin adet 1.000'de düşmesi (%34 azalma), `docs/09-olceklenebilirlik.md`'deki (Kişi B)
1.000 sanal pano yük testiyle birlikte okunmalıdır: donanım maliyeti düşerken sunucu tarafı da
aynı ölçekte doğrusala yakın büyüyor (bkz. o doküman), yani birim ekonomi saha sayısı arttıkça
iyileşiyor.

## 5. Tazminat maruziyeti hesaplayıcısı (parametreli)

§3'teki örnek hesap "önlenen arıza" üzerine kuruludur ve bunu kendisi varsayım olarak işaretler. Bu bölüm
ölçülebilir olan soruyu sorar: **bu pano kesilirse, yönetmeliğe göre ne kadar tazminat doğar?** Fayda kalemi
bizim modelimize değil, dışarıda yayımlanmış bir kurala bağlanır.

Hesaplayıcı: [`scripts/tazminat_maruziyeti.py`](../scripts/tazminat_maruziyeti.py) (yalnızca stdlib + mevcut
harita yükleyici; yeni bağımlılık yok).

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
**3,70 USD** (adet 1.000), yani kontrolcü kartının adet 1.000 maliyetinin (~37 USD) yaklaşık **%10**'u.
BOM'da bu parçadan 2 adet var; ikincisi SCADA ağ geçidinin slave portudur, yeniden kullanımın bedeli değildir.

Kaçınılan kalemlerin birim fiyatı depoda olmadığı için **net fark "veri yok"**tur. Fiyat girilirse betik
kaçınılan toplamı ve net farkı yazar:

```
python scripts/tazminat_maruziyeti.py --yalniz bom --at-fiyat <USD> --gerilim-fiyat <USD> --ark-dedektor-fiyat <USD> --ark-unite-fiyat <USD>
```

**Dürüstlük notu:** `bom.csv`'de 3 adet INA226 akım/gerilim ADC'si *opsiyonel* olarak duruyor (fider CT
girişleri; 1,35 USD adet 1 / 0,90 USD adet 1.000). MPR-53CS okunduğu için Temel pakette kullanılmıyor — yani
"akım trafosu eklemedik" cümlesi, kartın CT giriş yolunu tamamen kaldırdığımız anlamına gelmez.
