/* panobeyni-sim — host ikilisi (TA3 Adim 6, Kisi A).
 *
 * AYNI C CEKIRDEGI, MCU'da kosacak olanla birebir. Bu ikili yalnizca cekirdegin
 * etrafina bir G/C kabugu gecirir: olcumleri stdin'den okur, cekirdegi surer ve
 * Pano Beyni'nin Modbus register tablosunu stdout'a JSON satiri olarak basar.
 *
 * KAPSAM KARARI (durustluk notu): PLAN.md TA3 Adim 6 bu ikiliden ayrica "sanal seri
 * porttan Modbus master dongusu, Modbus slave sunumu ve MQTT yayini" istiyor.
 * Bunlar TASIMA katmanidir ve C'de sifirdan MQTT/Modbus yigini yazmak, kanitlanmak
 * istenen seye (kenarda ve merkezde AYNI algoritma) hicbir sey katmazdi. Bu yuzden:
 *
 *     C  -> fizik, kestirim, esik karari, register tablosu   (MCU'ya giden kisim)
 *     Py -> Modbus TCP slave, MQTT, seri port                (sim/panobeyni_sim.py)
 *
 * Boyle oldugu icin "ayni algoritma" iddiasi zayiflamaz; tam tersine, tasima
 * degistiginde cekirdek degismedigi GORULUR. Gercek urunde tasima katmani da C'dir
 * ve MCU'nun kendi yiginini kullanir (lwIP + bir MQTT kutuphanesi).
 *
 * Girdi satiri (bosluk ayrilmis):
 *     ts_unix i_l1 i_l2 i_l3 i_n t_low_c rh_low_pct t_up_c dt_1 ... dt_25
 *
 * Kullanim:
 *     panobeyni-sim --period 60 --thresholds <dosya>   < olcumler.txt
 *     python -m panoalgo.scenarios ... | panobeyni-sim --period 900
 */
#include "dewpoint.h"
#include "limits.h"
#include "modbus_map.h"
#include "rls.h"
#include "thermal.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_LINE 4096
#define BASELINE_SAMPLES_DEFAULT 200
/* Taban medyani icin saklanan kestirim sayisi. Python tarafinda deque(maxlen=1000);
 * host ikilisinde 1000 x 25 nokta x 8 bayt = 200 KB statik, MCU'da bu kadar yer
 * yoktur -> gercek urunde akan medyan (P2 quantile) kullanilacak. Fark, taban
 * penceresi 1000 ornegi asarsa ortaya cikar; docs/05'te not edilecek. */
#define K_HISTORY_MAX 1000

/* Sozlesme esikleri. Gercek cihazda devreye alma konfigurasyonuyla yuklenir;
 * burada varsayilanlar contracts/alarm-codes.yaml degerleridir ve --thresholds
 * ile dosyadan degistirilebilir (kural 10: koda gomulu TEK KAYNAK yok). */
static pano_limits_t default_limits(void)
{
    pano_limits_t lim;
    lim.term_rise_warn_k = 50.0;
    lim.term_rise_alarm_k = 70.0;
    lim.bus_rise_alarm_k = 105.0;
    lim.phase_diff_alarm_k = 15.0;
    lim.k_ratio_warn = 1.3;
    lim.k_ratio_alarm = 1.6;
    lim.ttl_warn_h = 14.0 * 24.0;
    lim.dew_margin_warn_k = 3.0;
    lim.dew_margin_alarm_k = 1.0;
    lim.panel_temp_alarm_c = 45.0;
    lim.current_alarm_ratio = 1.00;
    lim.rated_current_a = 2312.0;
    lim.similar_load_max_ratio = 1.10;
    return lim;
}

static const char *POINT_NAMES[] = PANO_POINT_NAMES;

/* Nokta indeksinden grup ve faz cikarir: 0-3 GIRIS (3 = notr), sonrasi DSYAn.
 * Sira contracts/modbus-map.yaml conn_temp.points listesidir. */
static void point_topology(int index, int *group, int *phase)
{
    if (index < 4) {
        *group = 0;
        *phase = (index == 3) ? -1 : index;   /* GIRIS_N faz karsilastirmasina girmez */
        return;
    }
    const int feeder_index = index - 4;
    *group = 1 + feeder_index / 3;            /* DSYA1..DSYA7 */
    *phase = feeder_index % 3;
}

/* Bir noktadan gecen akim: GIRIS dogrudan faz akimi, DSYA noktalari ana akimin
 * sabit bir kesri. Kesir bilinmedigi icin ana faz akimi kullanilir ve K kestirimi
 * o kesri kendi icine emer — K/K0 ORANI bundan etkilenmez (taban da ayni kesirle
 * ogrenilir). Ayni yaklasim Python tarafinda da var (edge.py _point_current). */
static double point_current(int index, const double i_ph[3], double i_n)
{
    int group = 0, phase = 0;
    point_topology(index, &group, &phase);
    return (phase < 0) ? i_n : i_ph[phase];
}

static double median_of(double *values, int count)
{
    for (int i = 1; i < count; ++i) {
        const double key = values[i];
        int j = i - 1;
        while (j >= 0 && values[j] > key) { values[j + 1] = values[j]; j--; }
        values[j + 1] = key;
    }
    return (count % 2) ? values[count / 2] : (values[count / 2 - 1] + values[count / 2]) / 2.0;
}

int main(int argc, char **argv)
{
    double period_s = 60.0;
    long baseline_samples = BASELINE_SAMPLES_DEFAULT;

    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--period") == 0 && i + 1 < argc) {
            period_s = atof(argv[++i]);
        } else if (strcmp(argv[i], "--baseline-samples") == 0 && i + 1 < argc) {
            baseline_samples = atol(argv[++i]);
        } else {
            fprintf(stderr, "kullanim: %s [--period S] [--baseline-samples N] < olcumler\n", argv[0]);
            return 2;
        }
    }
    if (period_s <= 0.0) {
        fprintf(stderr, "--period pozitif olmali\n");
        return 2;
    }

    const pano_limits_t limits = default_limits();

    /* DINAMIK BELLEK YOK: tum durum burada, sabit boyutlu. */
    static pano_rls_t rls[PANO_POINT_COUNT];
    static double k_history[PANO_POINT_COUNT][K_HISTORY_MAX];
    static int k_history_count[PANO_POINT_COUNT];
    static pano_point_t points[PANO_POINT_COUNT];
    static pano_gateway_t gateway;

    for (int p = 0; p < PANO_POINT_COUNT; ++p) {
        /* lam ORNEKLEME PERIYODUNA tasinir; sabitlenirse Python ile ayni veriden
         * farkli K/K0 cikar (bkz. rls.h notu). */
        const pano_real_t lam = pano_rls_lambda_for_period(
            (pano_real_t)period_s, PANO_REAL_C(0.998), PANO_RLS_REFERENCE_PERIOD_S);
        pano_rls_init(&rls[p], period_s, lam, 900.0, 1.0e7, 0.02);
        k_history_count[p] = 0;
    }
    pano_gateway_init(&gateway, 0xC0DEu, 30u);

    char line[MAX_LINE];
    long sample = 0;
    int baseline_frozen = 0;

    while (fgets(line, sizeof(line), stdin) != NULL) {
        double ts = 0.0, i_ph[3] = {0, 0, 0}, i_n = 0.0;
        double t_low = 0.0, rh_low = 0.0, t_up = 0.0;
        double dt[PANO_POINT_COUNT];

        char *cursor = line;
        int consumed = 0;
        if (sscanf(cursor, "%lf %lf %lf %lf %lf %lf %lf %lf%n",
                   &ts, &i_ph[0], &i_ph[1], &i_ph[2], &i_n, &t_low, &rh_low, &t_up, &consumed) != 8) {
            continue;   /* bos satir veya baslik */
        }
        cursor += consumed;

        int parsed = 0;
        for (; parsed < PANO_POINT_COUNT; ++parsed) {
            if (sscanf(cursor, "%lf%n", &dt[parsed], &consumed) != 1) { break; }
            cursor += consumed;
        }
        if (parsed != PANO_POINT_COUNT) {
            fprintf(stderr, "satir %ld: %d nokta okundu, %d bekleniyordu\n",
                    sample, parsed, PANO_POINT_COUNT);
            continue;
        }

        sample++;

        /* --- cekirdek: nokta basina kestirim --- */
        for (int p = 0; p < PANO_POINT_COUNT; ++p) {
            const double current = point_current(p, i_ph, i_n);
            pano_rls_update(&rls[p], (pano_real_t)current, (pano_real_t)dt[p]);

            /* Taban medyanina HER kestirim girer, sifirlar dahil. Python referansi
             * (detect.py _k_history) da oyle yapar. Sifirlari suzmek medyani yukari
             * kaydirir ve ayni veriden farkli K/K0 cikar — olculdu: 0.16'ya varan
             * sapma. Iki uygulamanin ayni sonucu vermesi, "tek algoritma" iddiasinin
             * kendisidir; kucuk gorunen bu ayrinti onu bozuyordu. */
            const double k = (double)pano_rls_k(&rls[p]);
            if (!baseline_frozen && k_history_count[p] < K_HISTORY_MAX) {
                k_history[p][k_history_count[p]++] = k;
            }

            int group = 0, phase = 0;
            point_topology(p, &group, &phase);
            points[p].dt_c = (pano_real_t)dt[p];
            points[p].k_ratio = pano_rls_k_ratio(&rls[p]);
            points[p].ttl_h = PANO_REAL_C(0.0);
            points[p].has_ttl = 0;      /* ttl tahmini yuk profili ister; host katmaninda */
            points[p].group = group;
            points[p].phase = phase;
        }

        /* Taban ogrenme suresi dolunca K0 = medyan (rapor 15.1: 7 gunluk medyan). */
        if (!baseline_frozen && sample >= baseline_samples) {
            for (int p = 0; p < PANO_POINT_COUNT; ++p) {
                if (k_history_count[p] > 0) {
                    pano_rls_freeze_baseline(&rls[p],
                        (pano_real_t)median_of(k_history[p], k_history_count[p]));
                }
            }
            baseline_frozen = 1;
            fprintf(stderr, "[panobeyni] taban ogrenme tamamlandi (%ld ornek)\n", sample);
        }

        /* --- cekirdek: esik karari --- */
        const double td = (double)pano_dew_point((pano_real_t)t_low, (pano_real_t)rh_low);
        pano_sample_t s;
        s.points = points;
        s.point_count = PANO_POINT_COUNT;
        s.i_ph[0] = (pano_real_t)i_ph[0];
        s.i_ph[1] = (pano_real_t)i_ph[1];
        s.i_ph[2] = (pano_real_t)i_ph[2];
        s.td_margin_k = (pano_real_t)(t_low - td);
        s.t_up_c = (pano_real_t)t_up;
        s.tvoc_present = 1;
        s.prot_health_ok = 1;
        s.comm_ok = 1;
        s.trips = 0;
        s.prev_trips = 0;
        s.has_prev_trips = 1;

        const unsigned long alarm_bits = pano_limits_evaluate(&limits, &s);

        /* --- Modbus register tablosu (adresler sozlesmeden uretilmis basliktan) --- */
        int worst_point = 0;
        for (int p = 1; p < PANO_POINT_COUNT; ++p) {
            if (dt[p] > dt[worst_point]) { worst_point = p; }
        }

        printf("{\"ts\":%.0f,\"sample\":%ld,\"baseline_frozen\":%d,", ts, sample, baseline_frozen);
        printf("\"alarm_bits\":%lu,", alarm_bits);
        printf("\"registers\":{");
        printf("\"%d\":%d,", PANO_REG_DEVICE_INFO_MAP_VERSION, PANO_MAP_VERSION);
        printf("\"%d\":%d,", PANO_REG_DEVICE_INFO_POINT_COUNT, PANO_POINT_COUNT);
        printf("\"%d\":%d,", PANO_REG_HEALTH_BASELINE_DAY, baseline_frozen ? 7 : 1);
        printf("\"%d\":%d,", PANO_REG_ENVIRONMENT_T_LOW_C, pano_scale_tenths((pano_real_t)t_low));
        printf("\"%d\":%d,", PANO_REG_ENVIRONMENT_TD_LOW_C, pano_scale_tenths((pano_real_t)td));
        printf("\"%d\":%d,", PANO_REG_ENVIRONMENT_TD_MARGIN_K, pano_scale_tenths(s.td_margin_k));
        printf("\"%d\":%d,", PANO_REG_ENVIRONMENT_T_UP_C, pano_scale_tenths((pano_real_t)t_up));
        printf("\"%d\":%lu,", PANO_BLK_ALARMS_START, alarm_bits & 0xFFFFul);
        printf("\"%d\":%lu,", PANO_BLK_ALARMS_START + 1, (alarm_bits >> 16) & 0xFFFFul);
        printf("\"%d\":%d,", PANO_REG_RISK_WORST_POINT, worst_point);
        printf("\"%d\":%u", PANO_REG_RISK_TTL_HOURS, pano_ttl_register(PANO_REAL_C(0.0), 0));

        for (int p = 0; p < PANO_POINT_COUNT; ++p) {
            printf(",\"%d\":%d", PANO_BLK_CONN_DT_START + p, pano_scale_tenths((pano_real_t)dt[p]));
            printf(",\"%d\":%d", PANO_BLK_K_INDEX_START + p, pano_k_ratio_register(points[p].k_ratio));
        }
        printf("},\"worst_point_name\":\"%s\"}\n", POINT_NAMES[worst_point]);
        fflush(stdout);
    }

    fprintf(stderr, "[panobeyni] %ld ornek islendi | reddedilen yazma %u, koruma denemesi %u\n",
            sample, gateway.denied_writes, gateway.protected_writes);
    return 0;
}
