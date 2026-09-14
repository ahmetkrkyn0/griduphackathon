/* Ayrik isil model (TA3, Kisi A).
 * libs/panoalgo/panoalgo/generator.py icindeki _advance_points ile ayni denklem. */
#ifndef PANO_THERMAL_H
#define PANO_THERMAL_H

#include "pano_types.h"

/* a = exp(-Ts/tau) */
pano_real_t pano_thermal_a(pano_real_t ts_s, pano_real_t tau_s);

/* dT[k+1] = a*dT[k] + (1-a)*K*I2[k]
 * I2 BIR ONCEKI ornegin akiminin karesidir (sifirinci derece tutucu, rapor 15.1). */
pano_real_t pano_thermal_step(pano_real_t dt_c, pano_real_t a, pano_real_t k, pano_real_t held_i2);

/* Kararli durum: dT = K*I^2 */
pano_real_t pano_thermal_steady(pano_real_t k, pano_real_t i2);

#endif /* PANO_THERMAL_H */
