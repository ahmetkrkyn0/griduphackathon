/* Sayisal dayaniklilik testi (TA3, Kisi A).
 *
 * Ortak vektor testi (test_rls.c) algoritmanin DOGRU calistigini kanitlar; bu test
 * ZORLANDIGINDA da bozulmadigini kanitlar. Iki koruma sinaniyor:
 *
 *   1. Kovaryans sifirlama. Unutma faktoru her adimda P'yi buyutur; kosegen
 *      negatife duserse kestirim anlamsizlasir. Python tarafinda bu GERCEKTEN
 *      yasandi (P izi negatif, K/K0 12.000).
 *
 *      DURUSTLUK NOTU: o patlamanin asil sebebi kovaryansin kendisi degil, sifirinci
 *      derece tutucu INDIS HATASIYDI — uretec I[k+1], kestirimci I[k] kullaniyordu,
 *      yani RLS tutarsiz bir modeli cozmeye calisiyordu. Indis duzeltildikten sonra
 *      temiz sentetik veride patlama YENIDEN URETILEMEDI (lam 0.835-0.95 ve genis
 *      genlik araliginda tarandi, P hic negatife dusmedi).
 *      Koruma yine de duruyor ve ASAGIDA DOGRUDAN test ediliyor: gercek sensor
 *      verisi modele birebir uymaz (modellenmemis dinamik, ornekleme titremesi,
 *      sensor arizasi) ve gomulu hedefte patlayan bir kestirim sahte bir P1 alarmina
 *      donusur. "Tetikleyemedim" ile "olamaz" ayni sey degildir.
 *   2. tau kirpma. K = beta/(1-a) oldugu icin a 1'e yaklastikca K patlar.
 *
 * Gomulu hedefte bu korumalar daha da kritiktir: orada patlayan bir kestirim
 * sahte bir P1 alarmina ve gereksiz bir saha ziyaretine donusur.
 */
#include "rls.h"

#include <math.h>
#include <stdio.h>

#define AGGRESSIVE_LAM  0.80    /* cok kisa hafiza: kovaryansi zorlar */
#define SAMPLE_PERIOD_S 900.0
#define STEPS           4000

/* Fiziksel olarak makul ust sinir: K * I^2 = dT oldugu icin 300 A'lik bir noktada
 * K = 1e-2 bile 900 K artis demektir. Bunun ustu kestirim patlamasidir. */
#define K_SANE_MAX 1.0e-2

int main(void)
{
    pano_rls_t rls;
    if (pano_rls_init(&rls, SAMPLE_PERIOD_S, AGGRESSIVE_LAM, 900.0, 1.0e7, 0.02) != PANO_OK) {
        fprintf(stderr, "kestirimci baslatilamadi\n");
        return 2;
    }

    int failures = 0;
    double worst_k = 0.0;
    double dt_c = 5.0;

    for (int step = 0; step < STEPS; ++step) {
        /* Neredeyse sabit yuk: uyarim kil payi var, RLS'i en zorlayan bolge. */
        const double i_a = 300.0 + 3.0 * sin((double)step / 37.0);
        /* 1000. adimda yuk basamagi — Python'da patlamayi tetikleyen desen. */
        const double load = (step > 1000) ? i_a * 1.35 : i_a;
        dt_c = 0.6 * dt_c + 0.4 * (2.0e-4 * load * load);

        pano_rls_update(&rls, (pano_real_t)load, (pano_real_t)dt_c);

        const double k = (double)pano_rls_k(&rls);
        const double tau = (double)pano_rls_tau_s(&rls);

        if (k > worst_k) { worst_k = k; }

        if (isnan(k) || isinf(k)) {
            fprintf(stderr, "adim %d: K sayi degil (%f)\n", step, k);
            failures++;
            break;
        }
        if (k > K_SANE_MAX) {
            fprintf(stderr, "adim %d: K fiziksel siniri asti: %.6e\n", step, k);
            failures++;
            break;
        }
        if (isnan(tau) || tau < 59.0 || tau > 21601.0) {
            fprintf(stderr, "adim %d: tau fiziksel arali disinda: %.3f\n", step, tau);
            failures++;
            break;
        }
    }

    /* --- Kovaryans sifirlamanin DOGRUDAN testi ---------------------------------
     * Yukaridaki dongu bu korumayi TETIKLEMEZ (bkz. dosya basindaki durustluk notu),
     * bu yuzden guard'in sozlesmesi dogrudan sinaniyor: kovaryans pozitif
     * tanimliligini kaybederse bir sonraki guncelleme onu baslangic degerine
     * dondurmeli ve kestirim kullanilabilir kalmali. */
    pano_rls_t broken;
    if (pano_rls_init(&broken, 60.0, 0.998, 900.0, 1.0e7, 0.02) != PANO_OK) {
        fprintf(stderr, "ikinci kestirimci baslatilamadi\n");
        return 2;
    }
    for (int step = 0; step < 40; ++step) {
        const double i_a = 200.0 + 150.0 * sin((double)step / 8.0);
        pano_rls_update(&broken, (pano_real_t)i_a, (pano_real_t)(2.0e-4 * i_a * i_a));
    }

    broken.p[0][0] = PANO_REAL_C(-1.0); /* kovaryansi bilerek bozuyoruz */
    pano_rls_update(&broken, PANO_REAL_C(350.0), PANO_REAL_C(24.5));

    if (broken.p[0][0] != PANO_RLS_P0 || broken.p[1][1] != PANO_RLS_P0) {
        fprintf(stderr, "bozuk kovaryans sifirlanmadi: p00=%g p11=%g\n",
                (double)broken.p[0][0], (double)broken.p[1][1]);
        failures++;
    }
    if (isnan((double)pano_rls_k(&broken)) || isinf((double)pano_rls_k(&broken))) {
        fprintf(stderr, "sifirlamadan sonra K sayi degil\n");
        failures++;
    }

    if (failures > 0) {
        return 1;
    }
    printf("%d adim zorlandi (lam=%.2f, yuk basamagi) | en buyuk K %.3e, sinir %.0e\n",
           STEPS, AGGRESSIVE_LAM, worst_k, (double)K_SANE_MAX);
    printf("tau kirpma sinirladi; bozulan kovaryans bir adimda geri kazanildi.\n");
    return 0;
}
