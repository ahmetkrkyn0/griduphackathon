/* L0/L1 esik karari (TA3, Kisi A).
 *
 * libs/panoalgo/panoalgo/limits.py'nin C karsiligi. Iki tasarim karari Python
 * tarafindan aynen tasindi:
 *
 *   1. ESIK DEGERLERI BURADA YAZILI DEGILDIR. Cagiran (host veya devreye alma
 *      konfigurasyonu) contracts/alarm-codes.yaml'dan okur ve pano_limits_t icinde
 *      verir. Gomulu hedefte sozlesme dosyasi okunamaz, ama esikler yine de TEK
 *      kaynaktan gelir — derleme zamaninda degil, konfigurasyonla (PLAN.md kural 10).
 *
 *   2. KARSILASTIRMA KESIN BUYUKTUR / KESIN KUCUKTUR. backend/app/risk.py `value > limit`
 *      kullanir ve tam esikteki degerin alarm URETMEDIGINI kilitler. `>=` kullanilsaydi
 *      alarm konsolu kirmizi acarken dijital ikizde ayni nokta yesil kalirdi.
 *
 * Cikti, contracts/alarm-codes.yaml alarms[].bit numaralarina gore bir bit alanidir;
 * merkez tarafi ayni numaralarla geri cozer.
 */
#ifndef PANO_LIMITS_H
#define PANO_LIMITS_H

#include "pano_types.h"

/* Bit numaralari contracts/alarm-codes.yaml alarms[].bit ile AYNIDIR. */
typedef enum {
    PANO_BIT_THR_TERM_WARN   = 0,
    PANO_BIT_THR_TERM_ALM    = 1,
    PANO_BIT_THR_BUS_ALM     = 2,
    PANO_BIT_THR_PHASE_DIF   = 3,
    PANO_BIT_K_WARN          = 4,
    PANO_BIT_K_ALM           = 5,
    PANO_BIT_TTL_14D         = 6,
    PANO_BIT_DEW_WARN        = 7,
    PANO_BIT_DEW_ALM         = 8,
    PANO_BIT_I_OVER          = 9,
    PANO_BIT_ARC_TRIP        = 11,
    PANO_BIT_PROT_HEALTH     = 12,
    PANO_BIT_PANEL_TEMP      = 21
} pano_alarm_bit_t;

/* Sozlesmeden okunan esikler. ttl SAAT cinsindendir: sozlesme gun verir
 * (ttl_warn_days), cagiran 24 ile carparak doldurur. */
typedef struct {
    pano_real_t term_rise_warn_k;
    pano_real_t term_rise_alarm_k;
    pano_real_t bus_rise_alarm_k;
    pano_real_t phase_diff_alarm_k;
    pano_real_t k_ratio_warn;
    pano_real_t k_ratio_alarm;
    pano_real_t ttl_warn_h;
    pano_real_t dew_margin_warn_k;
    pano_real_t dew_margin_alarm_k;
    pano_real_t panel_temp_alarm_c;
    pano_real_t current_alarm_ratio;
    pano_real_t rated_current_a;
    pano_real_t similar_load_max_ratio;
} pano_limits_t;

/* Tek bir olcum noktasi. Nokta ADI tasinmaz (gomulu tarafta string yok);
 * grup ve faz sayisal olarak verilir — faz karsilastirmasi bunlari kullanir. */
typedef struct {
    pano_real_t dt_c;
    pano_real_t k_ratio;
    pano_real_t ttl_h;
    int has_ttl;      /* 0 = tahmin yok (sema: ttl_h null); "sifir saat" DEGIL */
    int group;        /* 0 = GIRIS, 1..7 = DSYA1..DSYA7 */
    int phase;        /* 0,1,2 = L1,L2,L3 ; -1 = notr (faz karsilastirmasina girmez) */
} pano_point_t;

typedef struct {
    const pano_point_t *points;
    int point_count;

    pano_real_t i_ph[3];
    pano_real_t td_margin_k;
    pano_real_t t_up_c;

    int tvoc_present;     /* 0 = panoda TVOC-2 yok; "koruma arizali" DEMEK DEGIL */
    int prot_health_ok;
    int comm_ok;
    int trips;
    int prev_trips;
    int has_prev_trips;   /* 0 = ilk ornek, gecis karari verilemez */
} pano_sample_t;

/* O AN gecerli alarm bitlerini doner. MANDALLAMAZ: her cagri yalnizca anlik durumu
 * yansitir, temizlemeyi merkezdeki histerezis yonetir. */
unsigned long pano_limits_evaluate(const pano_limits_t *lim, const pano_sample_t *sample);

#endif /* PANO_LIMITS_H */
