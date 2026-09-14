/* Modbus harita erisimi ve YAZMA KORUMASI (TA3, Kisi A).
 *
 * Adresler modbus_map_generated.h icinde ve o dosya contracts/modbus-map.yaml'dan
 * URETILIR (PLAN.md kural 10). Bu dosyada tek bir adres sabiti yazili degildir.
 *
 * GK6 — "Koruma devresine yazma yok":
 *   Rapor 6.6d bunun neden bilincli bir guvenlik karari oldugunu soyluyor: izleme
 *   sisteminin yanlis bir acma karari binlerce aboneyi kesintiye ugratir. Bu yuzden
 *   430 register'in yalnizca 10'u (command blogu, %2,3) yazilabilir ve o da sifre
 *   ister. Ark korumasi aynasi (arc_mirror) sozlesmede ACIKCA read_only isaretlidir.
 *
 * Filtre iki yerde bagimsiz calisir — kenarda bu dosya, merkezde Kisi B'nin ag
 * gecidi (PLAN.md TB3 Adim 2). Savunma derinligi: birinin atlanmasi digerini
 * gecersiz kilmaz.
 */
#ifndef PANO_MODBUS_MAP_H
#define PANO_MODBUS_MAP_H

#include "modbus_map_generated.h"
#include "pano_types.h"

/* Modbus fonksiyon kodlari (yalnizca kullandiklarimiz). */
typedef enum {
    PANO_FC_READ_COILS          = 1,
    PANO_FC_READ_DISCRETE       = 2,
    PANO_FC_READ_HOLDING        = 3,
    PANO_FC_READ_INPUT          = 4,
    PANO_FC_WRITE_COIL          = 5,
    PANO_FC_WRITE_REGISTER      = 6,
    PANO_FC_WRITE_MULTI_COILS   = 15,
    PANO_FC_WRITE_MULTI_REGS    = 16
} pano_fc_t;

/* Modbus istisna kodlari. 0 = istisna yok (istek kabul edildi). */
typedef enum {
    PANO_EXC_NONE               = 0,
    PANO_EXC_ILLEGAL_FUNCTION   = 1,
    PANO_EXC_ILLEGAL_ADDRESS    = 2,
    PANO_EXC_ILLEGAL_VALUE      = 3,
    PANO_EXC_DEVICE_FAILURE     = 4
} pano_exception_t;

/* Ag gecidi durumu: acilmis sifre penceresi ve guvenlik olayi sayaci. */
typedef struct {
    unsigned long password_opened_at_s;  /* pencerenin acildigi an (cihaz saati)  */
    int           password_open;         /* 0 = kapali                            */
    unsigned      window_s;              /* pencere suresi                        */
    unsigned      expected_password;
    unsigned      denied_writes;         /* reddedilen yazma sayisi               */
    unsigned      protected_writes;      /* KORUMA aynasina yazma DENEMESI        */
} pano_gateway_t;

void pano_gateway_init(pano_gateway_t *gw, unsigned expected_password, unsigned window_s);

/* Sifre register'ina yazilan degeri isler; dogruysa yazma penceresini acar. */
void pano_gateway_offer_password(pano_gateway_t *gw, unsigned value, unsigned long now_s);

/* Bir istegin kabul edilip edilmeyecegine karar verir.
 *
 * Onemli kural: FC16 ile gelen aralik command blogunun DISINA TASIYORSA istek
 * TAMAMEN reddedilir. Aksi halde 890-905 araligini yazan tek bir istek alarms
 * blogunu ezebilirdi.
 */
pano_exception_t pano_modbus_check(pano_gateway_t *gw,
                                   pano_fc_t fc,
                                   unsigned address,
                                   unsigned quantity,
                                   unsigned long now_s);

/* Olcek ve sentinel yardimcilari (sozlesmedeki kodlamalar). */

/* 0.1 olcekli int16 alan; tasma sarmaz, DOYAR. Giris akimi 2312 A -> ham 23120. */
int pano_scale_tenths(pano_real_t value);

/* K/K0 -> k_index register'i. Sozlesme: deger = K/K0 * 100, olcek 0.1
 * => ham = K/K0 * 1000. Ornek: 1.6 -> 1600. */
int pano_k_ratio_register(pano_real_t k_ratio);

/* ttl_h -> risk.ttl_hours. 65535 = BILINMIYOR; "0 saat kaldi" ayri seydir. */
unsigned pano_ttl_register(pano_real_t ttl_h, int has_estimate);

#endif /* PANO_MODBUS_MAP_H */
