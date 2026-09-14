/* Bkz. rls.h — Python KIndexEstimator'un C karsiligi. */
#include "rls.h"

#include <math.h>

static pano_real_t clamp_a(const pano_rls_t *self, pano_real_t a)
{
    if (a < self->a_min) {
        return self->a_min;
    }
    if (a > self->a_max) {
        return self->a_max;
    }
    return a;
}

static pano_real_t window_mean(const pano_rls_t *self)
{
    pano_real_t total = PANO_REAL_C(0.0);
    for (int i = 0; i < self->window_count; ++i) {
        total += self->window[i];
    }
    return total / (pano_real_t)self->window_count;
}

static pano_real_t window_variance(const pano_rls_t *self, pano_real_t mean)
{
    pano_real_t total = PANO_REAL_C(0.0);
    for (int i = 0; i < self->window_count; ++i) {
        const pano_real_t diff = self->window[i] - mean;
        total += diff * diff;
    }
    return total / (pano_real_t)self->window_count;
}

/* Yeterli yuk degisimi var mi? Iki olcut: sozlesmedeki MUTLAK var(I^2) esigi veya
 * olcege bagimsiz GORELI esik. Goreli olcut olmadan notr nokta (faz akiminin ~1/6'si,
 * var(I^2) ~1000 kat kucuk) hicbir zaman uyarilmis sayilmaz. */
static int has_excitation(const pano_rls_t *self)
{
    if (self->window_count < 3) {
        return 0;
    }
    const pano_real_t mean = window_mean(self);
    const pano_real_t variance = window_variance(self, mean);
    if (variance >= self->min_var_i2) {
        return 1;
    }
    if (mean <= PANO_REAL_C(0.0)) {
        return 0;
    }
    return (sqrt(variance) / mean) >= self->min_cv_i2;
}

static void push_i2(pano_rls_t *self, pano_real_t i2)
{
    /* Halka tampon: en eski deger uzerine yazilir, kaydirma yok. */
    self->window[self->window_head] = i2;
    self->window_head = (self->window_head + 1) % PANO_EXCITATION_WINDOW;
    if (self->window_count < PANO_EXCITATION_WINDOW) {
        self->window_count++;
    }
}

/* Unutma faktorlu RLS'in tek adimi. 2x2 oldugu icin matris cebri elle acildi —
 * Python tarafi da ayni sekilde yazildi ki iki uygulama satir satir eslesebilsin. */
static void rls_step(pano_rls_t *self, pano_real_t f0, pano_real_t f1, pano_real_t target)
{
    const pano_real_t pf0 = self->p[0][0] * f0 + self->p[0][1] * f1;
    const pano_real_t pf1 = self->p[1][0] * f0 + self->p[1][1] * f1;

    const pano_real_t denom = self->lam + f0 * pf0 + f1 * pf1;
    if (denom <= PANO_REAL_C(0.0)) {
        return; /* sayisal olarak imkansiza yakin; kestirimi bozmaktansa atla */
    }

    const pano_real_t g0 = pf0 / denom;
    const pano_real_t g1 = pf1 / denom;
    const pano_real_t error = target - (self->theta[0] * f0 + self->theta[1] * f1);

    self->theta[0] += g0 * error;
    self->theta[1] += g1 * error;

    const pano_real_t p00 = (self->p[0][0] - g0 * pf0) / self->lam;
    const pano_real_t p01 = (self->p[0][1] - g0 * pf1) / self->lam;
    const pano_real_t p10 = (self->p[1][0] - g1 * pf0) / self->lam;
    const pano_real_t p11 = (self->p[1][1] - g1 * pf1) / self->lam;

    /* KOVARYANS SIFIRLAMA: P pozitif tanimli kalmali. Unutma faktoru her adimda
     * P'yi buyuttugu icin zayif uyarimda kosegen negatife dusebilir; o noktadan
     * sonra kestirim anlamsizdir. Parametreler korunur, yalnizca guven sifirlanir. */
    if (p00 <= PANO_REAL_C(0.0) || p11 <= PANO_REAL_C(0.0)) {
        self->p[0][0] = PANO_RLS_P0;
        self->p[0][1] = PANO_REAL_C(0.0);
        self->p[1][0] = PANO_REAL_C(0.0);
        self->p[1][1] = PANO_RLS_P0;
        return;
    }

    self->p[0][0] = p00;
    self->p[0][1] = p01;
    self->p[1][0] = p10;
    self->p[1][1] = p11;
}

pano_real_t pano_rls_lambda_for_period(pano_real_t ts_s,
                                       pano_real_t reference_lam,
                                       pano_real_t reference_ts_s)
{
    if (!(reference_lam > PANO_REAL_C(0.0)) || reference_lam >= PANO_REAL_C(1.0)) {
        return reference_lam;
    }
    const pano_real_t memory_s = -reference_ts_s / log(reference_lam);
    const pano_real_t derived = exp(-ts_s / memory_s);
    const pano_real_t floor_lam =
        PANO_REAL_C(1.0) - PANO_REAL_C(1.0) / (pano_real_t)PANO_RLS_MIN_MEMORY_SAMPLES;

    pano_real_t lam = (derived > floor_lam) ? derived : floor_lam;
    return (lam < reference_lam) ? lam : reference_lam;
}

pano_status_t pano_rls_init(pano_rls_t *self,
                            pano_real_t ts_s,
                            pano_real_t lam,
                            pano_real_t tau_init_s,
                            pano_real_t min_var_i2,
                            pano_real_t min_cv_i2)
{
    if (self == NULL || ts_s <= PANO_REAL_C(0.0) || tau_init_s <= PANO_REAL_C(0.0)) {
        return PANO_ERR_ARG;
    }
    if (lam <= PANO_REAL_C(0.0) || lam > PANO_REAL_C(1.0)) {
        return PANO_ERR_ARG;
    }

    self->ts = ts_s;
    self->lam = lam;
    self->min_var_i2 = min_var_i2;
    self->min_cv_i2 = min_cv_i2;
    self->a_min = exp(-ts_s / PANO_TAU_MIN_S);
    self->a_max = exp(-ts_s / PANO_TAU_MAX_S);

    self->theta[0] = exp(-ts_s / tau_init_s);
    self->theta[1] = PANO_REAL_C(0.0);
    self->p[0][0] = PANO_RLS_P0;
    self->p[0][1] = PANO_REAL_C(0.0);
    self->p[1][0] = PANO_REAL_C(0.0);
    self->p[1][1] = PANO_RLS_P0;

    self->prev_dt = PANO_REAL_C(0.0);
    self->prev_i2 = PANO_REAL_C(0.0);
    self->has_prev = 0;
    self->window_count = 0;
    self->window_head = 0;
    self->k0 = PANO_REAL_C(0.0);
    self->excited = 0;
    return PANO_OK;
}

void pano_rls_update(pano_rls_t *self, pano_real_t i_a, pano_real_t dt_c)
{
    const pano_real_t i2 = i_a * i_a;

    push_i2(self, i2);
    self->excited = has_excitation(self);

    if (self->has_prev && self->excited) {
        rls_step(self, self->prev_dt, self->prev_i2 / PANO_RLS_I2_SCALE, dt_c);
    }

    self->prev_dt = dt_c;
    self->prev_i2 = i2;
    self->has_prev = 1;
}

pano_real_t pano_rls_k(const pano_rls_t *self)
{
    const pano_real_t a = clamp_a(self, self->theta[0]);
    const pano_real_t beta = self->theta[1] / PANO_RLS_I2_SCALE;
    const pano_real_t k = beta / (PANO_REAL_C(1.0) - a);
    return (k > PANO_REAL_C(0.0)) ? k : PANO_REAL_C(0.0);
}

pano_real_t pano_rls_tau_s(const pano_rls_t *self)
{
    const pano_real_t a = clamp_a(self, self->theta[0]);
    return -self->ts / log(a);
}

pano_real_t pano_rls_k_ratio(const pano_rls_t *self)
{
    /* Taban dondurulmadan oran ANLAMSIZDIR; 1.0 donmek devreye alma gununde
     * sahte alarm yagmurunu onler (Python tarafi da boyle davranir). */
    if (self->k0 <= PANO_REAL_C(0.0)) {
        return PANO_REAL_C(1.0);
    }
    return pano_rls_k(self) / self->k0;
}

int pano_rls_excited(const pano_rls_t *self)
{
    return self->excited;
}

void pano_rls_freeze_baseline(pano_rls_t *self, pano_real_t k0)
{
    self->k0 = k0;
}
