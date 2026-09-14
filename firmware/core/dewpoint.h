/* Ciy noktasi ve yogusma marji (TA3, Kisi A).
 * libs/panoalgo/panoalgo/physics.py ile AYNI formul ve AYNI sabitler. */
#ifndef PANO_DEWPOINT_H
#define PANO_DEWPOINT_H

#include "pano_types.h"

#define PANO_MAGNUS_B PANO_REAL_C(17.62)
#define PANO_MAGNUS_C PANO_REAL_C(243.12)

/* Magnus formuluyle ciy noktasi (degC).
 * rh_pct (0,100] araliginda olmali; disinda NAN doner (C'de istisna yok, bu yuzden
 * cagiran isnan() ile denetlemeli). */
pano_real_t pano_dew_point(pano_real_t t_c, pano_real_t rh_pct);

/* Yuzey sicakligi ile ciy noktasi arasindaki marj (K). Negatif = yogusma. */
pano_real_t pano_dew_point_margin(pano_real_t surface_t_c, pano_real_t air_t_c, pano_real_t rh_pct);

#endif /* PANO_DEWPOINT_H */
