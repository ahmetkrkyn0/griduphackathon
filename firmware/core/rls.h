/* Isil direnc indeksi kestirimi — unutma faktorlu RLS (TA3, Kisi A).
 *
 * Bu dosya libs/panoalgo/panoalgo/detect.py icindeki KIndexEstimator sinifinin
 * C karsiligidir ve SATIR SATIR ayni yolu izler. Iddia dosyayla kanitlanir:
 * firmware/tests/test_rls.c, Python'un urettigi data/fixtures/rls_vectors.csv
 * dosyasini okur ve her adimda ayni K / tau / excited degerini uretmek zorundadir.
 *
 * Model (rapor 15.1):
 *     dT[k+1] = a*dT[k] + beta*I2[k],   a = exp(-Ts/tau)
 *     K   = beta / (1 - a)
 *     tau = -Ts / ln(a)
 */
#ifndef PANO_RLS_H
#define PANO_RLS_H

#include "pano_types.h"

/* Regresor olcegi: dT ~ 10 K iken I^2 ~ 1e5 A^2'dir. Olceklenmeden P matrisi kotu
 * kosullanir. Python tarafindaki I2_SCALE ile AYNI deger olmak zorunda. */
#define PANO_RLS_I2_SCALE PANO_REAL_C(1.0e5)
#define PANO_RLS_P0       PANO_REAL_C(10.0)

/* tau'nun fiziksel araligi. K = beta/(1-a) oldugu icin a 1'e yaklastikca K patlar;
 * gercek kisit tau'dur (Python: TAU_REPORT_MIN_S / TAU_REPORT_MAX_S). */
#define PANO_TAU_MIN_S PANO_REAL_C(60.0)
#define PANO_TAU_MAX_S PANO_REAL_C(21600.0)

/* Tek bir olcum noktasinin kestirim durumu. Sabit boyutlu, isaretci tasimaz;
 * dizi olarak statik ayrilabilir. */
typedef struct {
    pano_real_t ts;                 /* ornekleme periyodu (s)                */
    pano_real_t lam;                /* unutma faktoru                        */
    pano_real_t min_var_i2;         /* mutlak kalici uyarim esigi            */
    pano_real_t min_cv_i2;          /* olcege bagimsiz uyarim esigi          */
    pano_real_t a_min;              /* tau ust sinirindan gelen a alt siniri */
    pano_real_t a_max;              /* tau alt sinirindan gelen a ust siniri */

    pano_real_t theta[2];           /* [a, beta * I2_SCALE]                  */
    pano_real_t p[2][2];            /* kovaryans                             */

    pano_real_t prev_dt;            /* bir onceki sicaklik artisi            */
    pano_real_t prev_i2;            /* bir onceki akimin karesi              */
    int         has_prev;

    pano_real_t window[PANO_EXCITATION_WINDOW];  /* son I^2 degerleri        */
    int         window_count;
    int         window_head;

    pano_real_t k0;                 /* dondurulmus taban; 0 = henuz yok      */
    int         excited;
} pano_rls_t;

/* Kestirimciyi baslatir. tau_init_s ve esikler sozlesmeden gelir (host okur).
 * Basarisizlik yalnizca gecersiz argumandandir; bellek ayrilmaz. */
pano_status_t pano_rls_init(pano_rls_t *self,
                            pano_real_t ts_s,
                            pano_real_t lam,
                            pano_real_t tau_init_s,
                            pano_real_t min_var_i2,
                            pano_real_t min_cv_i2);

/* Bir olcum ciftini isler. Kalici uyarim yoksa parametreler GUNCELLENMEZ. */
void pano_rls_update(pano_rls_t *self, pano_real_t i_a, pano_real_t dt_c);

/* Anlik kestirimler. */
pano_real_t pano_rls_k(const pano_rls_t *self);
pano_real_t pano_rls_tau_s(const pano_rls_t *self);
pano_real_t pano_rls_k_ratio(const pano_rls_t *self);
int         pano_rls_excited(const pano_rls_t *self);

/* Tabani verilen degerde sabitler (7 gunluk medyan host tarafinda hesaplanir;
 * cekirdek medyan icin gecmis TUTMAZ — bellek butcesi buna izin vermez). */
void pano_rls_freeze_baseline(pano_rls_t *self, pano_real_t k0);

#endif /* PANO_RLS_H */
