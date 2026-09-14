/* URETILMIS DOSYA — ELLE DUZENLEMEYIN.
 *
 * Kaynak : contracts/modbus-map.yaml (surum 1)
 * Ureten : python -m panoalgo.genmap --out firmware/core/modbus_map_generated.h
 *
 * PLAN.md kural 10: Modbus adresleri sozlesmeden okunur, koda gomulmez. Gomulu
 * tarafta calisma aninda YAML okunamadigi icin adresler DERLEME ZAMANINDA buraya
 * uretilir. Sozlesme degisirse bu dosyayi yeniden uretin; elle duzeltmeyin.
 */
#ifndef PANO_MODBUS_MAP_GENERATED_H
#define PANO_MODBUS_MAP_GENERATED_H


#define PANO_MAP_VERSION 1
#define PANO_MAP_WORD_ORDER_HIGH_FIRST 1

/* --- Blok baslangiclari ve uzunluklari ------------------------------------ */
#define PANO_BLK_DEVICE_INFO_START 0
#define PANO_BLK_DEVICE_INFO_COUNT 20
#define PANO_BLK_HEALTH_START 20
#define PANO_BLK_HEALTH_COUNT 20
#define PANO_BLK_CONN_TEMP_START 100
#define PANO_BLK_CONN_TEMP_COUNT 50
#define PANO_BLK_CONN_DT_START 150
#define PANO_BLK_CONN_DT_COUNT 50
#define PANO_BLK_K_INDEX_START 200
#define PANO_BLK_K_INDEX_COUNT 100
#define PANO_BLK_ENVIRONMENT_START 300
#define PANO_BLK_ENVIRONMENT_COUNT 20
#define PANO_BLK_ELECTRICAL_MIRROR_START 400
#define PANO_BLK_ELECTRICAL_MIRROR_COUNT 50
#define PANO_BLK_ARC_MIRROR_START 500
#define PANO_BLK_ARC_MIRROR_COUNT 20
#define PANO_BLK_PD_START 600
#define PANO_BLK_PD_COUNT 20
#define PANO_BLK_RISK_START 700
#define PANO_BLK_RISK_COUNT 20
#define PANO_BLK_ALARMS_START 800
#define PANO_BLK_ALARMS_COUNT 30
#define PANO_BLK_EVENT_START 830
#define PANO_BLK_EVENT_COUNT 20
#define PANO_BLK_COMMAND_START 900
#define PANO_BLK_COMMAND_COUNT 10

/* --- Blok ici oge ofsetleri ----------------------------------------------- */
#define PANO_REG_DEVICE_INFO_MAP_VERSION (0 + 0)
#define PANO_REG_DEVICE_INFO_FW_VERSION (0 + 1)
#define PANO_REG_DEVICE_INFO_SERIAL_HI (0 + 2)
#define PANO_REG_DEVICE_INFO_SERIAL_LO (0 + 3)
#define PANO_REG_DEVICE_INFO_PANO_TYPE (0 + 4)
#define PANO_REG_DEVICE_INFO_POINT_COUNT (0 + 5)
#define PANO_REG_HEALTH_UPTIME_H (20 + 0)
#define PANO_REG_HEALTH_LAST_SYNC_M (20 + 1)
#define PANO_REG_HEALTH_SUPPLY_STATE (20 + 2)
#define PANO_REG_HEALTH_BACKUP_PCT (20 + 3)
#define PANO_REG_HEALTH_RSSI_DBM_NEG (20 + 4)
#define PANO_REG_HEALTH_NODES_OK (20 + 5)
#define PANO_REG_HEALTH_NODES_TOTAL (20 + 6)
#define PANO_REG_HEALTH_HEARTBEAT (20 + 7)
#define PANO_REG_HEALTH_BUFFERED_MSGS (20 + 8)
#define PANO_REG_HEALTH_BASELINE_DAY (20 + 9)
#define PANO_REG_ENVIRONMENT_T_LOW_C (300 + 0)
#define PANO_REG_ENVIRONMENT_RH_LOW_PCT (300 + 1)
#define PANO_REG_ENVIRONMENT_TD_LOW_C (300 + 2)
#define PANO_REG_ENVIRONMENT_TD_MARGIN_K (300 + 3)
#define PANO_REG_ENVIRONMENT_T_UP_C (300 + 4)
#define PANO_REG_ENVIRONMENT_RH_UP_PCT (300 + 5)
#define PANO_REG_ENVIRONMENT_DT_AIR_K (300 + 6)
#define PANO_REG_ENVIRONMENT_VOC_IDX (300 + 7)
#define PANO_REG_ELECTRICAL_MIRROR_I_L1_A (400 + 0)
#define PANO_REG_ELECTRICAL_MIRROR_I_L2_A (400 + 1)
#define PANO_REG_ELECTRICAL_MIRROR_I_L3_A (400 + 2)
#define PANO_REG_ELECTRICAL_MIRROR_I_N_A (400 + 3)
#define PANO_REG_ELECTRICAL_MIRROR_U_L1_V (400 + 4)
#define PANO_REG_ELECTRICAL_MIRROR_U_L2_V (400 + 5)
#define PANO_REG_ELECTRICAL_MIRROR_U_L3_V (400 + 6)
#define PANO_REG_ELECTRICAL_MIRROR_THD_I_L1_PCT (400 + 7)
#define PANO_REG_ELECTRICAL_MIRROR_THD_I_L2_PCT (400 + 8)
#define PANO_REG_ELECTRICAL_MIRROR_THD_I_L3_PCT (400 + 9)
#define PANO_REG_ELECTRICAL_MIRROR_COSPHI (400 + 10)
#define PANO_REG_ELECTRICAL_MIRROR_UNBAL_PCT (400 + 11)
#define PANO_REG_ELECTRICAL_MIRROR_MPR_COMM_OK (400 + 12)
#define PANO_REG_ARC_MIRROR_SYSTEM_STATE (500 + 0)
#define PANO_REG_ARC_MIRROR_TRIP_COUNT (500 + 1)
#define PANO_REG_ARC_MIRROR_LAST_DET_LOW (500 + 2)
#define PANO_REG_ARC_MIRROR_LAST_DET_HIGH (500 + 3)
#define PANO_REG_ARC_MIRROR_LAST_TRIP_RELAY (500 + 4)
#define PANO_REG_ARC_MIRROR_LAST_TRIP_DATE (500 + 5)
#define PANO_REG_ARC_MIRROR_LAST_TRIP_HHMM (500 + 6)
#define PANO_REG_ARC_MIRROR_LAST_TRIP_SEC (500 + 7)
#define PANO_REG_ARC_MIRROR_SENSOR_STATUS_X2 (500 + 8)
#define PANO_REG_ARC_MIRROR_SENSOR_STATUS_X3 (500 + 9)
#define PANO_REG_ARC_MIRROR_AMB_LIGHT_X2 (500 + 10)
#define PANO_REG_ARC_MIRROR_AMB_LIGHT_X3 (500 + 11)
#define PANO_REG_ARC_MIRROR_ACTIVE_DTC_1 (500 + 12)
#define PANO_REG_ARC_MIRROR_PROT_HEALTH_OK (500 + 13)
#define PANO_REG_ARC_MIRROR_TVOC_COMM_OK (500 + 14)
#define PANO_REG_PD_PULSES_PER_S (600 + 0)
#define PANO_REG_PD_AMP_DBMV (600 + 1)
#define PANO_REG_PD_TREND_SLOPE (600 + 2)
#define PANO_REG_PD_PHASE_CLUSTER (600 + 3)
#define PANO_REG_RISK_RISK_SCORE (700 + 0)
#define PANO_REG_RISK_FAULT_MODE (700 + 1)
#define PANO_REG_RISK_TTL_HOURS (700 + 2)
#define PANO_REG_RISK_WORST_POINT (700 + 3)
#define PANO_REG_ALARMS_ALARM_BITS_0_15 (800 + 0)
#define PANO_REG_ALARMS_ALARM_BITS_16_31 (800 + 1)
#define PANO_REG_ALARMS_LATCHED_BITS_0_15 (800 + 10)
#define PANO_REG_ALARMS_LATCHED_BITS_16_31 (800 + 11)
#define PANO_REG_ALARMS_ACTIVE_ALARM_COUNT (800 + 20)
#define PANO_REG_ALARMS_HIGHEST_PRIO (800 + 21)
#define PANO_REG_EVENT_EVENT_COUNT (830 + 0)
#define PANO_REG_EVENT_LAST_CODE (830 + 1)
#define PANO_REG_EVENT_TS_HI (830 + 2)
#define PANO_REG_EVENT_TS_LO (830 + 3)
#define PANO_REG_COMMAND_PASSWORD (900 + 0)
#define PANO_REG_COMMAND_ACK_ALARM (900 + 1)
#define PANO_REG_COMMAND_RESET_LATCH (900 + 2)
#define PANO_REG_COMMAND_MAINT_MODE (900 + 3)
#define PANO_REG_COMMAND_TEST_ALARM (900 + 4)

/* --- Olcum noktalari (conn_temp.points sirasi; conn_dt ve k_index ayni sira) -- */
#define PANO_POINT_COUNT 25
#define PANO_PT_GIRIS_L1 0
#define PANO_PT_GIRIS_L2 1
#define PANO_PT_GIRIS_L3 2
#define PANO_PT_GIRIS_N 3
#define PANO_PT_DSYA1_L1 4
#define PANO_PT_DSYA1_L2 5
#define PANO_PT_DSYA1_L3 6
#define PANO_PT_DSYA2_L1 7
#define PANO_PT_DSYA2_L2 8
#define PANO_PT_DSYA2_L3 9
#define PANO_PT_DSYA3_L1 10
#define PANO_PT_DSYA3_L2 11
#define PANO_PT_DSYA3_L3 12
#define PANO_PT_DSYA4_L1 13
#define PANO_PT_DSYA4_L2 14
#define PANO_PT_DSYA4_L3 15
#define PANO_PT_DSYA5_L1 16
#define PANO_PT_DSYA5_L2 17
#define PANO_PT_DSYA5_L3 18
#define PANO_PT_DSYA6_L1 19
#define PANO_PT_DSYA6_L2 20
#define PANO_PT_DSYA6_L3 21
#define PANO_PT_DSYA7_L1 22
#define PANO_PT_DSYA7_L2 23
#define PANO_PT_DSYA7_L3 24

/* Nokta adlari, tanilama ciktisi ve test icin. Gomulu tarafta string tasimak
 * zorunlu degildir; bu tablo yalnizca host ikilisinde kullanilir. */
#define PANO_POINT_NAMES { \
    "GIRIS_L1", \
    "GIRIS_L2", \
    "GIRIS_L3", \
    "GIRIS_N", \
    "DSYA1_L1", \
    "DSYA1_L2", \
    "DSYA1_L3", \
    "DSYA2_L1", \
    "DSYA2_L2", \
    "DSYA2_L3", \
    "DSYA3_L1", \
    "DSYA3_L2", \
    "DSYA3_L3", \
    "DSYA4_L1", \
    "DSYA4_L2", \
    "DSYA4_L3", \
    "DSYA5_L1", \
    "DSYA5_L2", \
    "DSYA5_L3", \
    "DSYA6_L1", \
    "DSYA6_L2", \
    "DSYA6_L3", \
    "DSYA7_L1", \
    "DSYA7_L2", \
    "DSYA7_L3", \
}

/* --- Yazilabilir alan (GK6: yazma YALNIZCA command blogunda) -------------- */
#define PANO_WRITABLE_START 900
#define PANO_WRITABLE_END   (900 + 10 - 1)

/* Sozlesmede ACIKCA salt okunur isaretlenmis bloklar (ark korumasi aynasi). */
#define PANO_READ_ONLY_ARC_MIRROR 1

/* --- Sentineller ---------------------------------------------------------- */
/* 65535 = 'bilinmiyor'. '0 saat kaldi' ile AYNI SEY DEGILDIR. */
#define PANO_UNKNOWN_U16 65535u

#endif /* PANO_MODBUS_MAP_GENERATED_H */
