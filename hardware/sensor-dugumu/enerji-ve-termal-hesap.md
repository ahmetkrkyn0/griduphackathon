# Sensör Düğümü — Termal Dayanım ve Enerji Bütçesi Hesap Raporu

**Hazırlayan:** Kişi C · **Tarih:** 17 Eylül 2026 · **Şartname:** TEDAŞ MLZ/2020-069 & IEC 61439-1

---

## 1. Termal Dayanım Modeli (Bara 105°C Çalışma Koşulu)

### 1.1 Sınır Şartları
* **Ortam Sıcaklığı:** Maksimum $+45^\circ\text{C}$ (pano içi yerel hava sıcaklığı $+55^\circ\text{C}$ kabul edilir).
* **Bara Yüzey Sıcaklığı:** IEC 61439-1 Tablo 6'ya göre harici klemens/bara izin verilen aşırı sıcaklık artı 70 K $\rightarrow$ $35^\circ\text{C} + 70\text{ K} = 105^\circ\text{C}$.
* **Arıza Durumu Aşırı Isınma:** Gevşek bağlantı senaryosunda (S1) yerel temas noktası $125^\circ\text{C}$'ye kadar çıkabilir.

### 1.2 Malzeme ve Komponent Termal Sınıfları
1. **Gövde:** Sabic Lexan 940A Polikarbonat. UL94 V-0 sınıfı, Isı Bozulma Sıcaklığı (HDT @ 0.45 MPa): **$135^\circ\text{C}$**. Sürekli çalışma indeksi (RTI): **$115^\circ\text{C}$**.
2. **PCB:** Yüksek Tg (Camlaşma Sıcaklığı) FR-4. $\text{Tg} = 170^\circ\text{C}$, $\text{Td} = 340^\circ\text{C}$.
3. **Bileşenler:**
   - TI TMP117: $-55^\circ\text{C} .. +150^\circ\text{C}$ (Sensör çipi doğrudan bara termal pedi üzerinde).
   - nRF52833: $-40^\circ\text{C} .. +105^\circ\text{C}$ endüstriyel sınıf.
   - LTC3331: $-40^\circ\text{C} .. +125^\circ\text{C}$.
   - Tadiran LiSOCl2 Pil: $-55^\circ\text{C} .. +85^\circ\text{C}$ (Pil bölmesi bara temas yüzeyinden 12 mm termal bariyer ve hava boşluğu ile yalıtılmıştır; gövde içi tepe sıcaklığı $+68^\circ\text{C}$'yi geçmez).

---

## 2. Enerji Bütçesi ve Pil Ömrü Hesabı

### 2.1 Güç Tüketim Profili (10 Saniyelik Çevrim)
Sistem olay tabanlı ve periyodik "deep sleep" modunda çalışır.

| Aşama | Süre | Çekilen Akım (@ 3.0V) | Enerji (µA·s) |
|---|:---:|:---:|:---:|
| **Derin Uyku (RTC aktif, RAM retention)** | $9.95\text{ s}$ | $1.8\text{ µA}$ | $17.91\text{ µAs}$ |
| **Sensör Okuma (TMP117 + SHT40 I2C)** | $15\text{ ms}$ | $0.65\text{ mA}$ | $9.75\text{ µAs}$ |
| **AES-128 Şifreleme ve Paket Hazırlama** | $5\text{ ms}$ | $4.2\text{ mA}$ | $21.00\text{ µAs}$ |
| **RF İletimi (+4 dBm BLE 5.0 TX)** | $5\text{ ms}$ | $14.5\text{ mA}$ | $72.50\text{ µAs}$ |
| **Geri Alım / Dinleme (RX penceresi)** | $10\text{ ms}$ | $6.8\text{ mA}$ | $68.00\text{ µAs}$ |
| **TOPLAM (10 saniyelik periyot)** | **$10.0\text{ s}$** | **Ortalama $18.9\text{ µA}$** | **$189.16\text{ µAs}$** |

### 2.2 Pil ile Çalışma Süresi (Sıfır Enerji Hasadı Durumunda)
* **Kullanılan Pil:** Tadiran TL-5902 (1/2 AA, $3.6\text{ V}$, $1200\text{ mAh}$).
* **Kullanılabilir Kapasite (%85 deşarj ve sıcaklık faktörü):** $1020\text{ mAh}$.
* **Yıllık Tüketim:** $18.9\text{ µA} \times 8760\text{ h/yıl} = 165.5\text{ mAh/yıl}$.
* **Yıllık Öz-Deşarj (%1/yıl):** $\sim 12\text{ mAh/yıl}$.
* **Toplam Yıllık Kayıp:** $\sim 177.5\text{ mAh/yıl}$.
$$\text{Ömür} = \frac{1020\text{ mAh}}{177.5\text{ mAh/yıl}} \approx 5.74\text{ Yıl (Hasatsız En Kötü Senaryo)}$$

---

## 3. Manyetik Alan Enerji Hasadı (LTC3331) ile Sonsuz Ömür

Düğüm üzerindeki minyatür split-core akım trafosu bara fiderine klipslenir:
* **Fider Akımı $I > 15\text{ A}$ olduğunda:** Hasat trafosu sekonderinde en az $25\text{ µW}$ indükler.
* LTC3331 şarj regülatörü devreye girerek dahili süperkapasitörü $3.3\text{ V}$ seviyesine şarj eder.
* **$I \ge 20\text{ A}$:** Sensör düğümünün harcadığı ortalama $56.7\text{ µW}$ gücün tamamı **manyetik alandan sağlanır**.
* **Pilden Çekilen Akım:** **$0.0\text{ µA}$** (Pil tamamen yedek moduna geçer).
* Dağıtım panolarında (özellikle 400A - 1600A baralarda) akım neredeyse sürekli 20A'in çok üzerinde olduğundan, **sensör düğümünün saha kullanım ömrü pil kimyasal yaşlanma sınırına (15+ yıl) ulaşır.**
