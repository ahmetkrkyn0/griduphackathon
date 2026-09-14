/* Bkz. limits.h — Python limits.evaluate()'in C karsiligi. */
#include "limits.h"

#define BIT(n) (1UL << (unsigned)(n))

/* Faz farki kurali sozlesmede "BENZER YUKTE fazlar arasi fark 15 K ustu" seklinde
 * yazilidir. Niteleme atlanirsa faz dengesizligi TEK BASINA alarm uretir: dT = K*I^2
 * oldugu icin %14 akim farki %31 sicaklik farki demektir ve 45 K'lik bir noktada 14 K
 * eder. Python tarafinda olculdu — niteleme olmadan SAGLIKLI pano orneklerinin
 * %33'unde yanlis alarm cikiyordu. */
static int phases_similarly_loaded(const pano_limits_t *lim, const pano_real_t i_ph[3])
{
    pano_real_t low = i_ph[0];
    pano_real_t high = i_ph[0];
    for (int i = 1; i < 3; ++i) {
        if (i_ph[i] < low) { low = i_ph[i]; }
        if (i_ph[i] > high) { high = i_ph[i]; }
    }
    if (!(low > PANO_REAL_C(0.0))) {
        return 0;
    }
    return (high / low) <= lim->similar_load_max_ratio;
}

static unsigned long point_bits(const pano_limits_t *lim, const pano_sample_t *sample)
{
    unsigned long bits = 0UL;
    for (int i = 0; i < sample->point_count; ++i) {
        const pano_point_t *p = &sample->points[i];

        if (p->dt_c > lim->term_rise_warn_k)  { bits |= BIT(PANO_BIT_THR_TERM_WARN); }
        if (p->dt_c > lim->term_rise_alarm_k) { bits |= BIT(PANO_BIT_THR_TERM_ALM); }
        if (p->dt_c > lim->bus_rise_alarm_k)  { bits |= BIT(PANO_BIT_THR_BUS_ALM); }

        if (p->k_ratio > lim->k_ratio_warn)  { bits |= BIT(PANO_BIT_K_WARN); }
        if (p->k_ratio > lim->k_ratio_alarm) { bits |= BIT(PANO_BIT_K_ALM); }

        /* has_ttl = 0 "tahmin yok" demektir; "sifir saat kaldi" DEGIL. */
        if (p->has_ttl && p->ttl_h < lim->ttl_warn_h) { bits |= BIT(PANO_BIT_TTL_14D); }
    }
    return bits;
}

/* Gruplama cikis bazlidir: DSYA1 sicak, DSYA5 soguk olabilir — farkli fiderler farkli
 * yuk tasir, aralarindaki fark anomali degildir. Notr (phase < 0) disaridadir. */
static unsigned long phase_bits(const pano_limits_t *lim, const pano_sample_t *sample)
{
    if (!phases_similarly_loaded(lim, sample->i_ph)) {
        return 0UL;
    }

    /* GIRIS + DSYA1..7 = 8 grup. Dinamik bellek yok: sabit boyutlu yerel dizi. */
    pano_real_t lowest[8];
    pano_real_t highest[8];
    int seen[8];
    for (int g = 0; g < 8; ++g) { seen[g] = 0; lowest[g] = PANO_REAL_C(0.0); highest[g] = PANO_REAL_C(0.0); }

    for (int i = 0; i < sample->point_count; ++i) {
        const pano_point_t *p = &sample->points[i];
        if (p->phase < 0 || p->group < 0 || p->group >= 8) {
            continue;
        }
        if (!seen[p->group]) {
            seen[p->group] = 1;
            lowest[p->group] = p->dt_c;
            highest[p->group] = p->dt_c;
            continue;
        }
        seen[p->group]++;
        if (p->dt_c < lowest[p->group])  { lowest[p->group] = p->dt_c; }
        if (p->dt_c > highest[p->group]) { highest[p->group] = p->dt_c; }
    }

    for (int g = 0; g < 8; ++g) {
        if (seen[g] >= 2 && (highest[g] - lowest[g]) > lim->phase_diff_alarm_k) {
            return BIT(PANO_BIT_THR_PHASE_DIF);
        }
    }
    return 0UL;
}

static unsigned long electrical_bits(const pano_limits_t *lim, const pano_sample_t *sample)
{
    pano_real_t highest = sample->i_ph[0];
    for (int i = 1; i < 3; ++i) {
        if (sample->i_ph[i] > highest) { highest = sample->i_ph[i]; }
    }
    /* Telemetride elec.i_ph YALNIZCA ana giris akimidir; fider bazli akim yoktur.
     * Merkez de (backend/app/risk.py) main_input anma degerini kullanir. */
    if (highest > lim->current_alarm_ratio * lim->rated_current_a) {
        return BIT(PANO_BIT_I_OVER);
    }
    return 0UL;
}

static unsigned long environment_bits(const pano_limits_t *lim, const pano_sample_t *sample)
{
    unsigned long bits = 0UL;
    if (sample->td_margin_k < lim->dew_margin_warn_k)  { bits |= BIT(PANO_BIT_DEW_WARN); }
    if (sample->td_margin_k < lim->dew_margin_alarm_k) { bits |= BIT(PANO_BIT_DEW_ALM); }
    if (sample->t_up_c > lim->panel_temp_alarm_c)      { bits |= BIT(PANO_BIT_PANEL_TEMP); }
    return bits;
}

static unsigned long protection_bits(const pano_sample_t *sample)
{
    if (!sample->tvoc_present) {
        return 0UL; /* panoda TVOC-2 yok; "koruma arizali" DEMEK DEGIL */
    }
    unsigned long bits = 0UL;
    if (!sample->prot_health_ok || !sample->comm_ok) {
        bits |= BIT(PANO_BIT_PROT_HEALTH);
    }
    /* Trip sayaci sifirlanmaz; "trips > 0" kurali alarmi sonsuza kadar mandallardi.
     * Yeni ark olayi ancak sayac ARTTIGINDA anlasilir. */
    if (sample->has_prev_trips && sample->trips > sample->prev_trips) {
        bits |= BIT(PANO_BIT_ARC_TRIP);
    }
    return bits;
}

unsigned long pano_limits_evaluate(const pano_limits_t *lim, const pano_sample_t *sample)
{
    if (lim == NULL || sample == NULL || sample->points == NULL) {
        return 0UL;
    }
    return point_bits(lim, sample)
         | phase_bits(lim, sample)
         | electrical_bits(lim, sample)
         | environment_bits(lim, sample)
         | protection_bits(sample);
}
