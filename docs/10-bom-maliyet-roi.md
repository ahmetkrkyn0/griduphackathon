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
