#include "dewpoint.h"

#include <math.h>

pano_real_t pano_dew_point(pano_real_t t_c, pano_real_t rh_pct)
{
    if (!(rh_pct > PANO_REAL_C(0.0)) || rh_pct > PANO_REAL_C(100.0)) {
        return (pano_real_t)NAN;
    }
    const pano_real_t gamma =
        log(rh_pct / PANO_REAL_C(100.0)) + PANO_MAGNUS_B * t_c / (PANO_MAGNUS_C + t_c);
    return PANO_MAGNUS_C * gamma / (PANO_MAGNUS_B - gamma);
}

pano_real_t pano_dew_point_margin(pano_real_t surface_t_c, pano_real_t air_t_c, pano_real_t rh_pct)
{
    return surface_t_c - pano_dew_point(air_t_c, rh_pct);
}
