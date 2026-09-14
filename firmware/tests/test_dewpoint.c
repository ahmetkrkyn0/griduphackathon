/* Ciy noktasi testi (PLAN.md TA3, Kisi A).
 *
 * Beklenen degerler HACKATHON_ANALIZ_RAPORU.md 15.1 tablosundan alinmistir —
 * Python tarafindaki libs/panoalgo/tests/test_dewpoint.py ile AYNI dort referans.
 */
#include "dewpoint.h"

#include <math.h>
#include <stdio.h>

#define TOLERANCE 0.1

struct case_t {
    double t_c;
    double rh_pct;
    double expected;
};

int main(void)
{
    /* Rapor 15.1 tablosu. */
    const struct case_t cases[] = {
        {25.0, 60.0, 16.7},
        {20.0, 85.0, 17.4},
        {15.0, 95.0, 14.2},
        {35.0, 50.0, 23.0},
    };
    const int count = (int)(sizeof(cases) / sizeof(cases[0]));
    int failures = 0;

    for (int i = 0; i < count; ++i) {
        const double got = (double)pano_dew_point((pano_real_t)cases[i].t_c,
                                                  (pano_real_t)cases[i].rh_pct);
        const double diff = fabs(got - cases[i].expected);
        if (diff > TOLERANCE) {
            fprintf(stderr, "T=%.1f RH=%.1f -> %.3f, beklenen %.1f (fark %.3f)\n",
                    cases[i].t_c, cases[i].rh_pct, got, cases[i].expected, diff);
            failures++;
        }
    }

    /* Gecersiz nem: C'de istisna yok, NAN doner. */
    if (!isnan((double)pano_dew_point(20.0, 0.0))) {
        fprintf(stderr, "RH=0 icin NAN bekleniyordu\n");
        failures++;
    }

    /* Marj isareti: yuzey ciy noktasinin altindaysa NEGATIF olmali (yogusma). */
    if (!(pano_dew_point_margin(15.0, 20.0, 85.0) < 0.0)) {
        fprintf(stderr, "soguk yuzeyde marj negatif olmaliydi\n");
        failures++;
    }
    if (!(pano_dew_point_margin(25.0, 20.0, 85.0) > 0.0)) {
        fprintf(stderr, "sicak yuzeyde marj pozitif olmaliydi\n");
        failures++;
    }

    if (failures > 0) {
        return 1;
    }
    printf("%d referans deger + 3 sinir kosulu gecti.\n", count);
    return 0;
}
