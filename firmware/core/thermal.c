#include "thermal.h"

#include <math.h>

pano_real_t pano_thermal_a(pano_real_t ts_s, pano_real_t tau_s)
{
    return exp(-ts_s / tau_s);
}

pano_real_t pano_thermal_step(pano_real_t dt_c, pano_real_t a, pano_real_t k, pano_real_t held_i2)
{
    return a * dt_c + (PANO_REAL_C(1.0) - a) * k * held_i2;
}

pano_real_t pano_thermal_steady(pano_real_t k, pano_real_t i2)
{
    return k * i2;
}
