/* L0/L1 esik karari testi (TA3, Kisi A).
 *
 * Python tarafindaki libs/panoalgo/tests/test_limits.py ile AYNI davranislari
 * kilitler. Esikler sozlesme degerleridir (contracts/alarm-codes.yaml) ve teste
 * konfigurasyon olarak verilir — gomulu tarafta da oyle gelecek.
 *
 * En kritik iki iddia:
 *   - tam esikteki deger alarm URETMEZ (kesin buyuktur),
 *   - faz dengesizligi TEK BASINA faz farki alarmi uretmez ("benzer yukte" kosulu).
 */
#include "limits.h"

#include <stdio.h>

#define BIT(n) (1UL << (unsigned)(n))

/* contracts/alarm-codes.yaml thresholds blogundan. */
static pano_limits_t contract_limits(void)
{
    pano_limits_t lim;
    lim.term_rise_warn_k = 50.0;
    lim.term_rise_alarm_k = 70.0;
    lim.bus_rise_alarm_k = 105.0;
    lim.phase_diff_alarm_k = 15.0;
    lim.k_ratio_warn = 1.3;
    lim.k_ratio_alarm = 1.6;
    lim.ttl_warn_h = 14.0 * 24.0;      /* sozlesme GUN verir, burada SAAT */
    lim.dew_margin_warn_k = 3.0;
    lim.dew_margin_alarm_k = 1.0;
    lim.panel_temp_alarm_c = 45.0;
    lim.current_alarm_ratio = 1.00;
    lim.rated_current_a = 2312.0;
    lim.similar_load_max_ratio = 1.10;
    return lim;
}

/* Saglikli bir pano: 3 faz GIRIS + 3 faz DSYA1, hepsi serin ve dengeli. */
static pano_sample_t healthy_sample(pano_point_t *points)
{
    for (int i = 0; i < 6; ++i) {
        points[i].dt_c = 20.0;
        points[i].k_ratio = 1.0;
        points[i].ttl_h = 0.0;
        points[i].has_ttl = 0;
        points[i].group = (i < 3) ? 0 : 1;
        points[i].phase = i % 3;
    }

    pano_sample_t s;
    s.points = points;
    s.point_count = 6;
    s.i_ph[0] = 1000.0;
    s.i_ph[1] = 1000.0;
    s.i_ph[2] = 1000.0;
    s.td_margin_k = 8.0;
    s.t_up_c = 38.0;
    s.tvoc_present = 1;
    s.prot_health_ok = 1;
    s.comm_ok = 1;
    s.trips = 4;
    s.prev_trips = 4;
    s.has_prev_trips = 1;
    return s;
}

static int checks = 0;
static int failures = 0;

static void expect(int condition, const char *what)
{
    checks++;
    if (!condition) {
        fprintf(stderr, "BASARISIZ: %s\n", what);
        failures++;
    }
}

int main(void)
{
    const pano_limits_t lim = contract_limits();
    pano_point_t points[6];

    /* --- saglikli taban --- */
    pano_sample_t s = healthy_sample(points);
    expect(pano_limits_evaluate(&lim, &s) == 0UL, "saglikli panoda hicbir alarm cikmamali");

    /* --- sicaklik artisi: tam esik alarm DEGIL --- */
    s = healthy_sample(points);
    for (int i = 0; i < 6; ++i) { points[i].dt_c = lim.term_rise_warn_k; }
    expect(!(pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_THR_TERM_WARN)),
           "tam esikteki artis uyari uretmemeli (kesin buyuktur)");

    points[2].dt_c = lim.term_rise_warn_k + 0.1;
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_THR_TERM_WARN)) != 0UL,
           "esigin hemen ustu uyari uretmeli");

    /* --- 70 K'yi gecen deger 50 K'yi de gecmistir --- */
    s = healthy_sample(points);
    points[0].dt_c = lim.term_rise_alarm_k + 1.0;
    {
        const unsigned long bits = pano_limits_evaluate(&lim, &s);
        expect((bits & BIT(PANO_BIT_THR_TERM_ALM)) != 0UL, "70 K ustu alarm uretmeli");
        expect((bits & BIT(PANO_BIT_THR_TERM_WARN)) != 0UL, "70 K ustu uyariyi da icermeli");
        expect((bits & BIT(PANO_BIT_THR_BUS_ALM)) == 0UL, "105 K altinda bara alarmi olmamali");
    }

    /* --- faz farki: BENZER YUKTE --- */
    s = healthy_sample(points);
    points[3].dt_c = 20.0 + lim.phase_diff_alarm_k + 1.0;
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_THR_PHASE_DIF)) != 0UL,
           "benzer yukte 15 K ustu fark alarm uretmeli");

    /* Ayni sicaklik farki, ama fazlar farkli yuk tasiyor -> anomali DEGIL. */
    s.i_ph[0] = 1000.0;
    s.i_ph[1] = 1000.0;
    s.i_ph[2] = 1400.0;   /* oran 1.4 > similar_load_max_ratio */
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_THR_PHASE_DIF)) == 0UL,
           "dengesiz yukte ham sicaklik farki alarm uretmemeli");

    /* Notr faz karsilastirmasina girmez. */
    s = healthy_sample(points);
    points[0].phase = -1;
    points[0].dt_c = 0.0;
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_THR_PHASE_DIF)) == 0UL,
           "notr nokta faz farkina girmemeli");

    /* Farkli fiderler birbiriyle kiyaslanmaz. */
    s = healthy_sample(points);
    for (int i = 3; i < 6; ++i) { points[i].dt_c = 20.0 + lim.phase_diff_alarm_k + 2.0; }
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_THR_PHASE_DIF)) == 0UL,
           "farkli fiderler arasi fark alarm uretmemeli");

    /* --- K/K0 --- */
    s = healthy_sample(points);
    points[4].k_ratio = lim.k_ratio_warn;
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_K_WARN)) == 0UL,
           "tam esikteki K/K0 uyari uretmemeli");
    points[4].k_ratio = lim.k_ratio_alarm + 0.01;
    {
        const unsigned long bits = pano_limits_evaluate(&lim, &s);
        expect((bits & BIT(PANO_BIT_K_ALM)) != 0UL, "1.6 ustu K/K0 alarm uretmeli");
        expect((bits & BIT(PANO_BIT_K_WARN)) != 0UL, "1.6 ustu 1.3'u de gecmistir");
    }

    /* --- sinira kalan sure: SAAT, ve "tahmin yok" != "sifir saat" --- */
    s = healthy_sample(points);
    points[1].has_ttl = 1;
    points[1].ttl_h = lim.ttl_warn_h - 1.0;
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_TTL_14D)) != 0UL,
           "14 gunden az kalan sure alarm uretmeli");
    points[1].ttl_h = lim.ttl_warn_h + 1.0;
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_TTL_14D)) == 0UL,
           "14 gunden fazla kalan sure alarm uretmemeli");
    s = healthy_sample(points);   /* has_ttl = 0 */
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_TTL_14D)) == 0UL,
           "tahmin yokken ttl alarmi cikmamali");

    /* --- asiri akim: ana giris anma degeri --- */
    s = healthy_sample(points);
    s.i_ph[0] = lim.current_alarm_ratio * lim.rated_current_a;
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_I_OVER)) == 0UL,
           "tam anma akimi alarm uretmemeli");
    s.i_ph[0] = lim.current_alarm_ratio * lim.rated_current_a + 1.0;
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_I_OVER)) != 0UL,
           "anma akiminin ustu alarm uretmeli");

    /* --- yogusma --- */
    s = healthy_sample(points);
    s.td_margin_k = lim.dew_margin_warn_k - 0.1;
    {
        const unsigned long bits = pano_limits_evaluate(&lim, &s);
        expect((bits & BIT(PANO_BIT_DEW_WARN)) != 0UL, "3 K altinda yogusma uyarisi");
        expect((bits & BIT(PANO_BIT_DEW_ALM)) == 0UL, "3 K altinda henuz alarm yok");
    }
    s.td_margin_k = lim.dew_margin_alarm_k - 0.1;
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_DEW_ALM)) != 0UL,
           "1 K altinda yogusma alarmi");

    /* --- pano ic sicakligi --- */
    s = healthy_sample(points);
    s.t_up_c = lim.panel_temp_alarm_c + 1.0;
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_PANEL_TEMP)) != 0UL,
           "45 degC ustu pano sicaklik alarmi");

    /* --- koruma sagligi ve ark --- */
    s = healthy_sample(points);
    s.prot_health_ok = 0;
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_PROT_HEALTH)) != 0UL,
           "dedektor arizasi koruma alarmi uretmeli");

    s = healthy_sample(points);
    s.comm_ok = 0;
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_PROT_HEALTH)) != 0UL,
           "cevap vermeyen TVOC-2 koruma alarmi uretmeli");

    s = healthy_sample(points);
    s.tvoc_present = 0;
    s.prot_health_ok = 0;
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_PROT_HEALTH)) == 0UL,
           "TVOC-2 olmayan panoda koruma alarmi cikmamali");

    s = healthy_sample(points);
    s.trips = 5;   /* prev_trips = 4 */
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_ARC_TRIP)) != 0UL,
           "artan trip sayaci ark alarmi uretmeli");

    s = healthy_sample(points);
    s.trips = 9;
    s.prev_trips = 9;
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_ARC_TRIP)) == 0UL,
           "degismeyen trip sayaci alarmi mandallamamali");

    s = healthy_sample(points);
    s.trips = 9;
    s.has_prev_trips = 0;
    expect((pano_limits_evaluate(&lim, &s) & BIT(PANO_BIT_ARC_TRIP)) == 0UL,
           "onceki ornek yokken gecis karari verilmemeli");

    if (failures > 0) {
        fprintf(stderr, "%d/%d kontrol basarisiz\n", failures, checks);
        return 1;
    }
    printf("%d kontrol gecti (esikler sozlesmeden, karsilastirma kesin buyuktur).\n", checks);
    return 0;
}
