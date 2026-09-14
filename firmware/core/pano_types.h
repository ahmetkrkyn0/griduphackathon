/* Ortak tipler ve derleme secenekleri (TA3, Kisi A).
 *
 * TASINABILIRLIK KURALLARI (PLAN.md TA3 Adim 5):
 *   - dinamik bellek YOK: malloc/free/calloc hicbir yerde cagrilmaz,
 *   - her durum sabit boyutludur ve cagiranin verdigi yapinin icinde yasar,
 *   - standart kutuphane disinda bagimlilik yok (yalnizca <math.h>, <stddef.h>),
 *   - hicbir cekirdek dosyasi printf/dosya/soket kullanmaz; G/C host tarafindadir.
 *
 * SAYI HASSASIYETI: cekirdek `pano_real_t` uzerinden yazildi.
 *   - `double` (varsayilan): Python referans uygulamasiyla bit bit ayni yolu izler,
 *     PLAN.md TA3'un 1e-6 esigini rahatca gecer. Host ikilisi bunu kullanir.
 *   - `float` (PANO_USE_FLOAT ile): FPU'su yalnizca tek duyarlikli olan MCU'larda
 *     (or. Cortex-M4F) cok daha hizli ve kucuktur; karsilik olarak 240 adimlik
 *     vektorde Python ile fark 1e-6'nin ustune cikabilir. Bu bir bozulma degil
 *     bilincli bir takastir ve testte ayri tolerans ile dogrulanir.
 */
#ifndef PANO_TYPES_H
#define PANO_TYPES_H

#include <stddef.h>

#ifdef PANO_USE_FLOAT
typedef float pano_real_t;
#define PANO_REAL_C(x) (x##f)
#else
typedef double pano_real_t;
#define PANO_REAL_C(x) (x)
#endif

/* Bir panodaki en fazla izleme noktasi sayisi.
 * contracts/modbus-map.yaml conn_temp.count = 50 register / 2 = 25 nokta;
 * telemetri semasi t_conn maxItems = 25. Ikisi de ayni sayiyi soyler. */
#define PANO_MAX_POINTS 25

/* Kalici uyarim penceresi. Python referansiyle AYNI olmak zorunda: excited karari
 * ortak test vektorunun bir sutunudur (data/fixtures/rls_vectors.csv). */
#define PANO_EXCITATION_WINDOW 30

typedef enum {
    PANO_OK = 0,
    PANO_ERR_ARG = -1
} pano_status_t;

#endif /* PANO_TYPES_H */
