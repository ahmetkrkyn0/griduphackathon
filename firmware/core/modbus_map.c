/* Bkz. modbus_map.h — GK6 yazma koruması ve sozlesme kodlamalari. */
#include "modbus_map.h"

#include <math.h>

#define TENTHS_MIN (-32768)
#define TENTHS_MAX (32767)
#define TTL_MAX_U16 65534u   /* 65535 sentinel oldugu icin gercek deger burada doyar */

static int is_read(pano_fc_t fc)
{
    return fc == PANO_FC_READ_COILS || fc == PANO_FC_READ_DISCRETE
        || fc == PANO_FC_READ_HOLDING || fc == PANO_FC_READ_INPUT;
}

static int is_register_write(pano_fc_t fc)
{
    return fc == PANO_FC_WRITE_REGISTER || fc == PANO_FC_WRITE_MULTI_REGS;
}

static int fully_inside_command(unsigned address, unsigned quantity)
{
    if (quantity == 0u) {
        return 0;
    }
    const unsigned last = address + quantity - 1u;
    if (last < address) {          /* tasma */
        return 0;
    }
    return address >= (unsigned)PANO_WRITABLE_START && last <= (unsigned)PANO_WRITABLE_END;
}

/* Istek, sozlesmede ACIKCA salt okunur isaretlenmis ark korumasi aynasina dokunuyor
 * mu? Buraya yazma DENEMESI bile bir guvenlik olayidir ve ayrica sayilir. */
static int touches_arc_mirror(unsigned address, unsigned quantity)
{
    if (quantity == 0u) {
        return 0;
    }
    const unsigned last = address + quantity - 1u;
    const unsigned lo = (unsigned)PANO_BLK_ARC_MIRROR_START;
    const unsigned hi = lo + (unsigned)PANO_BLK_ARC_MIRROR_COUNT - 1u;
    return !(last < lo || address > hi);
}

void pano_gateway_init(pano_gateway_t *gw, unsigned expected_password, unsigned window_s)
{
    if (gw == NULL) {
        return;
    }
    gw->password_opened_at_s = 0ul;
    gw->password_open = 0;
    gw->window_s = window_s;
    gw->expected_password = expected_password;
    gw->denied_writes = 0u;
    gw->protected_writes = 0u;
}

void pano_gateway_offer_password(pano_gateway_t *gw, unsigned value, unsigned long now_s)
{
    if (gw == NULL) {
        return;
    }
    if (value == gw->expected_password) {
        gw->password_open = 1;
        gw->password_opened_at_s = now_s;
    } else {
        gw->password_open = 0;
        gw->denied_writes++;
    }
}

static int window_is_open(const pano_gateway_t *gw, unsigned long now_s)
{
    if (!gw->password_open) {
        return 0;
    }
    return (now_s - gw->password_opened_at_s) <= (unsigned long)gw->window_s;
}

pano_exception_t pano_modbus_check(pano_gateway_t *gw,
                                   pano_fc_t fc,
                                   unsigned address,
                                   unsigned quantity,
                                   unsigned long now_s)
{
    if (gw == NULL) {
        return PANO_EXC_DEVICE_FAILURE;
    }

    /* Okuma her adreste serbesttir: harita FC03 ve FC04'te aynalanir
     * (contracts/modbus-map.yaml mirror_fc03_fc04: true). */
    if (is_read(fc)) {
        return PANO_EXC_NONE;
    }

    /* Coil yazma TAMAMEN kapali. Sozlesme coils icin access tanimlamaz ve
     * "yazma yalnizca command blogunda" kurali coil'leri de kapsar. */
    if (fc == PANO_FC_WRITE_COIL || fc == PANO_FC_WRITE_MULTI_COILS) {
        gw->denied_writes++;
        return PANO_EXC_ILLEGAL_FUNCTION;
    }

    if (!is_register_write(fc)) {
        gw->denied_writes++;
        return PANO_EXC_ILLEGAL_FUNCTION;
    }

    /* Koruma aynasina yazma DENEMESI ayrica sayilir — juriye gosterilecek kanit. */
    if (touches_arc_mirror(address, quantity)) {
        gw->protected_writes++;
        gw->denied_writes++;
        return PANO_EXC_ILLEGAL_ADDRESS;
    }

    /* Aralik command blogunun disina TASIYORSA istek TAMAMEN reddedilir.
     * Kismi kabul edilseydi 890-905 araligini yazan tek bir FC16 istegi alarms
     * blogunu ezebilirdi. */
    if (!fully_inside_command(address, quantity)) {
        gw->denied_writes++;
        return PANO_EXC_ILLEGAL_ADDRESS;
    }

    /* Sifre register'inin KENDISINE yazmak her zaman serbesttir; pencereyi acan
     * sey zaten odur. Cagiran, yazilan degeri offer_password ile verir. */
    if (address == (unsigned)PANO_WRITABLE_START && quantity == 1u) {
        return PANO_EXC_NONE;
    }

    if (!window_is_open(gw, now_s)) {
        gw->denied_writes++;
        return PANO_EXC_DEVICE_FAILURE;
    }
    return PANO_EXC_NONE;
}

int pano_scale_tenths(pano_real_t value)
{
    if (isnan((double)value)) {
        return 0;
    }
    const double raw = (double)value * 10.0;
    /* Doyma: sarmak, 2312 A'lik bir akimi 100 A gibi gostererek alarmi kacirir. */
    if (raw > (double)TENTHS_MAX) { return TENTHS_MAX; }
    if (raw < (double)TENTHS_MIN) { return TENTHS_MIN; }
    return (int)(raw >= 0.0 ? raw + 0.5 : raw - 0.5);
}

int pano_k_ratio_register(pano_real_t k_ratio)
{
    /* Sozlesme: deger = K/K0 * 100, blok olcegi 0.1 => ham = K/K0 * 1000. */
    return pano_scale_tenths(k_ratio * PANO_REAL_C(100.0));
}

unsigned pano_ttl_register(pano_real_t ttl_h, int has_estimate)
{
    if (!has_estimate || isnan((double)ttl_h)) {
        return PANO_UNKNOWN_U16;   /* "tahmin yok"; "0 saat kaldi" DEGIL */
    }
    if (ttl_h <= PANO_REAL_C(0.0)) {
        return 0u;                 /* sinir zaten asildi */
    }
    if ((double)ttl_h >= (double)TTL_MAX_U16) {
        return TTL_MAX_U16;        /* sentinelin uzerine tasma */
    }
    return (unsigned)((double)ttl_h + 0.5);
}
