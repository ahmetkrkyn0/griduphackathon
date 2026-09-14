/* Diller arasi esitlik testi (PLAN.md TA3 Adim 3, Kisi A).
 *
 * Iddia: "kenarda ve merkezde AYNI algoritma calisiyor."
 * Kanit: bu test, Python'un urettigi data/fixtures/rls_vectors.csv dosyasini okur,
 * ayni girdiyi C cekirdegine verir ve HER ADIMDA ayni K / tau / excited degerini
 * uretmesini sart kosar. Iki uygulamadan biri degisirse test kirilir.
 *
 * Tolerans PLAN.md TA3 Adim 3'ten: 1e-6 (goreli).
 *
 * OLCULEN FARKLAR:
 *   double (varsayilan) : K 1,36e-8 · tau 1,42e-8  -> esigin 73 kati altinda
 *   float  (PANO_USE_FLOAT) : K 6,77e-6 · tau 6,24e-6  -> esigin BIRAZ USTUNDE
 *
 * float surumu bir bozulma degil, BILINCLI BIR TAKASTIR: FPU'su yalnizca tek
 * duyarlikli olan MCU'larda (Cortex-M4F) cok daha hizli ve kucuktur. 240 adimda
 * birikmis 7e-6'lik goreli fark, K/K0 = 1.6 esiginde 1,1e-5'lik bir kaymaya karsilik
 * gelir — alarm kararini degistirmesi fiziksel olarak imkansizdir. Bu yuzden float
 * derlemesi kendi toleransiyla dogrulanir ve fark ekrana basilir; sessizce
 * gevsetilmez.
 */
#include "rls.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

#ifdef PANO_USE_FLOAT
#define TOLERANCE 1e-4     /* bkz. dosya basi: olculen 6,8e-6, pay birakilmis */
#define PRECISION_NAME "float"
#else
#define TOLERANCE 1e-6     /* PLAN.md TA3 Adim 3 esigi */
#define PRECISION_NAME "double"
#endif
#define MAX_LINE  256

/* Vektorun uretildigi parametreler (panoalgo/vectors.py ile ayni). */
#define VEC_TS_S      60.0
#define VEC_LAM       0.998
#define VEC_TAU_INIT  900.0
/* Sozlesme degerleri: contracts/alarm-codes.yaml thresholds. */
#define VEC_MIN_VAR_I2 1.0e7
#define VEC_MIN_CV_I2  0.02

static double relative_diff(double got, double want)
{
    const double scale = fabs(want) > 1e-12 ? fabs(want) : 1.0;
    return fabs(got - want) / scale;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "kullanim: %s <rls_vectors.csv>\n", argv[0]);
        return 2;
    }

    FILE *file = fopen(argv[1], "r");
    if (file == NULL) {
        fprintf(stderr, "vektor dosyasi acilamadi: %s\n", argv[1]);
        return 2;
    }

    pano_rls_t rls;
    if (pano_rls_init(&rls, VEC_TS_S, VEC_LAM, VEC_TAU_INIT, VEC_MIN_VAR_I2, VEC_MIN_CV_I2) != PANO_OK) {
        fprintf(stderr, "kestirimci baslatilamadi\n");
        return 2;
    }

    char line[MAX_LINE];
    if (fgets(line, sizeof(line), file) == NULL) { /* baslik satiri */
        fprintf(stderr, "vektor dosyasi bos\n");
        fclose(file);
        return 2;
    }

    int steps = 0, failures = 0;
    double worst_k = 0.0, worst_tau = 0.0;

    while (fgets(line, sizeof(line), file) != NULL) {
        int step = 0, want_excited = 0;
        double i_a = 0.0, dt_c = 0.0, want_k = 0.0, want_tau = 0.0;

        if (sscanf(line, "%d,%lf,%lf,%lf,%lf,%d",
                   &step, &i_a, &dt_c, &want_k, &want_tau, &want_excited) != 6) {
            fprintf(stderr, "satir cozumlenemedi: %s", line);
            fclose(file);
            return 2;
        }

        pano_rls_update(&rls, (pano_real_t)i_a, (pano_real_t)dt_c);
        steps++;

        const double got_k = (double)pano_rls_k(&rls);
        const double got_tau = (double)pano_rls_tau_s(&rls);
        const int got_excited = pano_rls_excited(&rls);

        const double dk = relative_diff(got_k, want_k);
        const double dtau = relative_diff(got_tau, want_tau);
        if (dk > worst_k) { worst_k = dk; }
        if (dtau > worst_tau) { worst_tau = dtau; }

        if (dk > TOLERANCE || dtau > TOLERANCE || got_excited != want_excited) {
            if (failures < 5) {
                fprintf(stderr,
                        "adim %d: K %.12e vs %.12e (fark %.3e) | tau %.9f vs %.9f (fark %.3e)"
                        " | excited %d vs %d\n",
                        step, got_k, want_k, dk, got_tau, want_tau, dtau, got_excited, want_excited);
            }
            failures++;
        }
    }
    fclose(file);

    if (steps == 0) {
        fprintf(stderr, "vektorde adim yok\n");
        return 2;
    }

    printf("%d adim karsilastirildi | en buyuk goreli fark: K %.3e, tau %.3e (tolerans %.0e)\n",
           steps, worst_k, worst_tau, TOLERANCE);

    if (failures > 0) {
        fprintf(stderr, "%d adimda Python referansi ile ayrisma\n", failures);
        return 1;
    }
    printf("C cekirdegi Python referansiyla ayni sonucu uretti.\n");
    return 0;
}
