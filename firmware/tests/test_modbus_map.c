/* Modbus yazma korumasi ve kodlama testi (TA3, Kisi A).
 *
 * GK6'nin ("koruma devresine yazma yok") yurutulebilir kanitidir. Sozlesme bunu
 * scripts/check_contracts.py ile YAML duzeyinde denetliyor; burada FIRMWARE
 * davranisi denetleniyor — iki ayri katman.
 *
 * Adresler modbus_map_generated.h'ten gelir, o da contracts/modbus-map.yaml'dan
 * uretilir. Bu dosyada elle yazilmis adres YOKTUR.
 */
#include "modbus_map.h"

#include <stdio.h>

#define PASSWORD  0xC0DEu
#define WINDOW_S  30u

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

static pano_gateway_t fresh(void)
{
    pano_gateway_t gw;
    pano_gateway_init(&gw, PASSWORD, WINDOW_S);
    return gw;
}

static pano_gateway_t unlocked(unsigned long now_s)
{
    pano_gateway_t gw = fresh();
    pano_gateway_offer_password(&gw, PASSWORD, now_s);
    return gw;
}

int main(void)
{
    pano_gateway_t gw;

    /* --- okuma her yerde serbest (FC03/FC04 aynali) --- */
    gw = fresh();
    expect(pano_modbus_check(&gw, PANO_FC_READ_HOLDING, PANO_BLK_CONN_TEMP_START, 25, 100)
               == PANO_EXC_NONE, "baglanti sicakliklari FC03 ile okunabilmeli");
    expect(pano_modbus_check(&gw, PANO_FC_READ_INPUT, PANO_BLK_ARC_MIRROR_START, 20, 100)
               == PANO_EXC_NONE, "ark korumasi aynasi FC04 ile OKUNABILMELI");
    expect(pano_modbus_check(&gw, PANO_FC_READ_COILS, 0, 6, 100) == PANO_EXC_NONE,
           "ozet coil'ler okunabilmeli");

    /* --- ARK KORUMASINA YAZMA: GK6'nin kalbi --- */
    gw = unlocked(100);
    expect(pano_modbus_check(&gw, PANO_FC_WRITE_REGISTER, PANO_BLK_ARC_MIRROR_START, 1, 100)
               != PANO_EXC_NONE, "ark korumasi aynasina yazma REDDEDILMELI");
    expect(gw.protected_writes == 1u,
           "koruma aynasina yazma denemesi ayrica sayilmali (juriye kanit)");

    gw = unlocked(100);
    expect(pano_modbus_check(&gw, PANO_FC_WRITE_MULTI_REGS,
                             PANO_BLK_ARC_MIRROR_START + 1, 5, 100) != PANO_EXC_NONE,
           "koruma aynasinin ortasina coklu yazma da reddedilmeli");

    /* --- yazma yalnizca command blogunda --- */
    gw = unlocked(100);
    expect(pano_modbus_check(&gw, PANO_FC_WRITE_REGISTER, PANO_BLK_RISK_START, 1, 100)
               == PANO_EXC_ILLEGAL_ADDRESS, "risk blogu yazilamaz");
    expect(pano_modbus_check(&gw, PANO_FC_WRITE_REGISTER, PANO_BLK_ALARMS_START, 1, 100)
               == PANO_EXC_ILLEGAL_ADDRESS, "alarm bitleri yazilamaz");
    expect(pano_modbus_check(&gw, PANO_FC_WRITE_REGISTER, PANO_BLK_CONN_TEMP_START, 1, 100)
               == PANO_EXC_ILLEGAL_ADDRESS, "olcum register'lari yazilamaz");

    /* --- EN KRITIK: sinira tasan coklu yazma TAMAMEN reddedilir --- */
    gw = unlocked(100);
    expect(pano_modbus_check(&gw, PANO_FC_WRITE_MULTI_REGS,
                             PANO_WRITABLE_START - 10u, 20u, 100) == PANO_EXC_ILLEGAL_ADDRESS,
           "command blogunun disina tasan FC16 TAMAMEN reddedilmeli "
           "(kismi kabul, alarm blogunu ezmeye yol acardi)");
    expect(pano_modbus_check(&gw, PANO_FC_WRITE_MULTI_REGS,
                             PANO_WRITABLE_END - 1u, 5u, 100) == PANO_EXC_ILLEGAL_ADDRESS,
           "command blogunun sonundan tasan yazma da reddedilmeli");

    /* --- coil yazma tamamen kapali --- */
    gw = unlocked(100);
    expect(pano_modbus_check(&gw, PANO_FC_WRITE_COIL, 0, 1, 100) == PANO_EXC_ILLEGAL_FUNCTION,
           "tek coil yazma kapali olmali");
    expect(pano_modbus_check(&gw, PANO_FC_WRITE_MULTI_COILS, 0, 6, 100) == PANO_EXC_ILLEGAL_FUNCTION,
           "coklu coil yazma kapali olmali");

    /* --- sifre penceresi --- */
    gw = fresh();
    expect(pano_modbus_check(&gw, PANO_FC_WRITE_REGISTER, PANO_WRITABLE_START + 1u, 1, 100)
               != PANO_EXC_NONE, "sifre verilmeden komut yazilamaz");

    gw = fresh();
    pano_gateway_offer_password(&gw, 0x1234u, 100);
    expect(pano_modbus_check(&gw, PANO_FC_WRITE_REGISTER, PANO_WRITABLE_START + 1u, 1, 100)
               != PANO_EXC_NONE, "yanlis sifre pencereyi acmamali");
    expect(gw.denied_writes >= 1u, "yanlis sifre denemesi sayilmali");

    gw = unlocked(100);
    expect(pano_modbus_check(&gw, PANO_FC_WRITE_REGISTER, PANO_WRITABLE_START + 1u, 1, 110)
               == PANO_EXC_NONE, "pencere icinde komut yazilabilmeli");
    expect(pano_modbus_check(&gw, PANO_FC_WRITE_REGISTER, PANO_WRITABLE_START + 1u, 1,
                             100 + WINDOW_S + 5u) != PANO_EXC_NONE,
           "pencere dolduktan sonra yazma reddedilmeli");

    /* Sifre register'inin kendisine yazmak her zaman serbest — pencereyi acan odur. */
    gw = fresh();
    expect(pano_modbus_check(&gw, PANO_FC_WRITE_REGISTER, PANO_WRITABLE_START, 1, 100)
               == PANO_EXC_NONE, "sifre register'ina yazmak serbest olmali");

    /* --- sozlesme kodlamalari --- */
    expect(pano_k_ratio_register(PANO_REAL_C(1.6)) == 1600,
           "K/K0 = 1.6 -> ham 1600 (sozlesme ornegi)");
    expect(pano_k_ratio_register(PANO_REAL_C(1.0)) == 1000, "K/K0 = 1.0 -> ham 1000");

    expect(pano_ttl_register(PANO_REAL_C(0.0), 0) == PANO_UNKNOWN_U16,
           "tahmin yoksa 65535 (BILINMIYOR)");
    expect(pano_ttl_register(PANO_REAL_C(0.0), 1) == 0u,
           "sifir saat kaldi, BILINMIYOR ile ayni sey degil");
    expect(pano_ttl_register(PANO_REAL_C(150.5), 1) == 151u, "150.5 saat -> 151 (yuvarlama)");
    expect(pano_ttl_register(PANO_REAL_C(1.0e9), 1) < PANO_UNKNOWN_U16,
           "cok buyuk ttl sentinelin uzerine tasmamali");

    /* Olcek doymasi: sarmak 2312 A'yi kucuk bir sayi gibi gosterip alarmi kacirtirdi. */
    expect(pano_scale_tenths(PANO_REAL_C(2312.0)) == 23120, "2312 A -> ham 23120");
    expect(pano_scale_tenths(PANO_REAL_C(1.0e9)) == 32767, "tasmada doymali, sarmamali");
    expect(pano_scale_tenths(PANO_REAL_C(-1.0e9)) == -32768, "negatif tasmada da doymali");

    if (failures > 0) {
        fprintf(stderr, "%d/%d kontrol basarisiz\n", failures, checks);
        return 1;
    }
    printf("%d kontrol gecti (GK6 yazma korumasi + sozlesme kodlamalari).\n", checks);
    return 0;
}
