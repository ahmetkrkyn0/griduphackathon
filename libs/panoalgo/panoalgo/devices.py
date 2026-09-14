"""Cihaz register modelleri (TA3 Adim 1-2, Kisi A): TVOC-2 ve MPR-53CS.

Iki gercek cihazin Modbus register haritasi, KENDI KILAVUZLARINDAKI adreslerde
taklit edilir. Juri QModMaster ile baglanip okuyacak; adresler tutmazsa iddia coker.

Kaynaklar (repo icindeki orijinal kilavuzlar):
  Hackathon Verileri/1SFC170017M0201_Rev_D_TVOC-2_Modbus_Manual.pdf
  Hackathon Verileri/MPR-53CS_Modbus_Register_Map_EN.pdf
ve HACKATHON_ANALIZ_RAPORU.md 3.5 / 3.6 / 15.1.

NEDEN AYRI MODUL: register mantigi burada, pymodbus sunucusu sim/ altinda. Boylece
harita testlerle kilitlenebilir (sunucu ayaga kaldirmadan) ve ayni model hem TCP hem
RTU sunucusunda kullanilir.

ADRESLEME: her iki kilavuz da PDU (0 tabanli) adres kullanir; register numarasi =
PDU + 1. Bu modul PDU adresi konusur.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

# --------------------------------------------------------------------- TVOC-2

TVOC2_FACTORY_SLAVE_ID = 248     # kilavuz 1.3: "248 = communication is DISABLED"
TVOC2_VALID_ID_MIN = 1
TVOC2_VALID_ID_MAX = 247
TVOC2_DEFAULT_BAUD = 19200
TVOC2_DEFAULT_FRAMING = "8E1"

TVOC2_TRIP_SLOTS = 7             # son 7 trip
TVOC2_TRIP_STRIDE = 7            # 6 okunabilir register + 1 bosluk
TVOC2_TRIP_BASE = 100
TVOC2_TRIP_COUNT_REG = 149
TVOC2_SENSOR_STATUS_X2 = 222
TVOC2_SENSOR_STATUS_X3 = 223
TVOC2_AMBIENT_LIGHT_X2 = 224
TVOC2_AMBIENT_LIGHT_X3 = 225
TVOC2_ERROR_COUNT_REG = 368
TVOC2_SYSTEM_STATE_REG = 1300
TVOC2_DTC_BASE = 1301
TVOC2_RESET_TRIP_REG = 1000
TVOC2_DIAGNOSTICS_REG = 213
TVOC2_SYSTEM_DATE_REG = 1100
TVOC2_SYSTEM_TIME_REG = 1101

# Kilavuz 4.4.1: 7'den az trip olmussa ilgili registerlar 0xFFFF'tir — SIFIR DEGIL.
TVOC2_EMPTY = 0xFFFF

# System state (1300) bit alani, kilavuz 4.4.12.
TVOC2_STATE_ACTIVE_TRIP = 1 << 0
TVOC2_STATE_ACTIVE_ERROR = 1 << 1
TVOC2_STATE_STARTUP = 1 << 2
TVOC2_STATE_DIAGNOSTICS = 1 << 3

UNIX_EPOCH = date(1970, 1, 1)


def days_since_epoch(when: date) -> int:
    """TVOC-2 tarih kodlamasi: 1970-01-01'den beri gun sayisi.

    Kilavuz ornegi: 0x42B6 = 17078 -> 2016-10-04.
    """
    return (when - UNIX_EPOCH).days


def encode_hhmm(hour: int, minute: int) -> int:
    """Saat kodlamasi: MSB saat, LSB dakika — IKILIK, BCD DEGIL.

    Kilavuz ornegi: 0x0922 -> 09:34. 2338 sayisini "23:38" diye okumak YANLISTIR.
    """
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(f"gecersiz saat: {hour:02d}:{minute:02d}")
    return (hour << 8) | minute


def decode_hhmm(value: int) -> tuple[int, int]:
    return (value >> 8) & 0xFF, value & 0xFF


@dataclass
class Tvoc2Trip:
    """Bir trip kaydi (kilavuz 4.4.1)."""

    detector_low: int
    detector_high: int
    relay: int
    when: datetime


class Tvoc2Device:
    """ABB TVOC-2 Arc Guard — salt okunur izleme arayuzu.

    HABERLESME KAPALI DAVRANISI: fabrika ayari slave ID 248'dir ve kilavuz bunu
    "gecerli bir Modbus ID degil, haberlesmenin KAPALI oldugunu gosterir" diye
    tanimlar. Bu durumda cihaz istege ISTISNA BILE DONDURMEZ, tamamen sessiz kalir.
    Demoda once sessizlik, sonra ID 10'a alinca cevap gosterilecek — sahada en sik
    yasanan devreye alma hatasi budur.
    """

    def __init__(self, slave_id: int = TVOC2_FACTORY_SLAVE_ID, firmware: str = "03.00.05") -> None:
        self.slave_id = slave_id
        self.firmware = firmware
        self.trips: list[Tvoc2Trip] = []
        self.error_count = 0
        self.active_error = False
        self.diagnostics_running = False
        self.sensor_status_x2 = 0x0000
        self.sensor_status_x3 = 0x0000
        self.ambient_light_x2 = 0x0000
        self.ambient_light_x3 = 0x0000
        self.write_attempts: list[tuple[int, int]] = []
        self.active_trip = False

    # ---------------------------------------------------------------- durum

    @property
    def communication_enabled(self) -> bool:
        return TVOC2_VALID_ID_MIN <= self.slave_id <= TVOC2_VALID_ID_MAX

    @property
    def system_state(self) -> int:
        state = 0
        if self.trips and self.active_trip:
            state |= TVOC2_STATE_ACTIVE_TRIP
        if self.active_error:
            state |= TVOC2_STATE_ACTIVE_ERROR
        if self.diagnostics_running:
            state |= TVOC2_STATE_DIAGNOSTICS
        return state

    # -------------------------------------------------------------- olaylar

    def record_trip(self, when: datetime, detector_low: int = 0x0002, detector_high: int = 0x0000,
                    relay: int = 0x0001) -> None:
        """Yeni ark tripi: log basa eklenir, sayac artar, 1300 bit0 set edilir."""
        self.trips.insert(0, Tvoc2Trip(detector_low, detector_high, relay, when))
        del self.trips[TVOC2_TRIP_SLOTS:]
        self.active_trip = True

    def reset_trip(self) -> None:
        """PDU 1000'e 1 yazilinca aktif trip temizlenir; LOG SILINMEZ, 149 azalmaz.

        Gercek cihazda bu uzaktan yapilabilir ama bizim ag gecidimiz engeller
        (PLAN.md GK6; alarm-codes.yaml HYP-ARC: "Reset SAHADA yapilir").
        """
        self.active_trip = False

    def raise_sensor_error(self, x2_bits: int = 0xFFFD, x3_bits: int = 0xFFFF) -> None:
        """Sensor arizasi: 222/223 ANCAK aktif hata varken anlamlidir (kilavuz 4.4.2)."""
        self.active_error = True
        self.error_count += 1
        self.sensor_status_x2 = x2_bits
        self.sensor_status_x3 = x3_bits

    def clear_errors(self) -> None:
        self.active_error = False
        self.sensor_status_x2 = 0x0000
        self.sensor_status_x3 = 0x0000
        self.ambient_light_x2 = 0x0000
        self.ambient_light_x3 = 0x0000

    # ------------------------------------------------------------- register

    def read(self, pdu_address: int) -> int | None:
        """Tek register okur. None = ILLEGAL DATA ADDRESS (tanimsiz adres)."""
        if not self.communication_enabled:
            return None

        if TVOC2_TRIP_BASE <= pdu_address < TVOC2_TRIP_BASE + TVOC2_TRIP_SLOTS * TVOC2_TRIP_STRIDE:
            return self._read_trip_log(pdu_address)
        if pdu_address == TVOC2_TRIP_COUNT_REG:
            return len(self.trips)
        if pdu_address == TVOC2_SENSOR_STATUS_X2:
            return self.sensor_status_x2
        if pdu_address == TVOC2_SENSOR_STATUS_X3:
            return self.sensor_status_x3
        if pdu_address == TVOC2_AMBIENT_LIGHT_X2:
            return self.ambient_light_x2
        if pdu_address == TVOC2_AMBIENT_LIGHT_X3:
            return self.ambient_light_x3
        if pdu_address == TVOC2_ERROR_COUNT_REG:
            return self.error_count
        if pdu_address == TVOC2_SYSTEM_STATE_REG:
            return self.system_state
        if TVOC2_DTC_BASE <= pdu_address <= TVOC2_DTC_BASE + 5:
            return 0x0000
        if pdu_address == TVOC2_SYSTEM_DATE_REG:
            return days_since_epoch(datetime.now(timezone.utc).date())
        if pdu_address == TVOC2_SYSTEM_TIME_REG:
            now = datetime.now(timezone.utc)
            return encode_hhmm(now.hour, now.minute)
        return None

    def _read_trip_log(self, pdu_address: int) -> int | None:
        offset = pdu_address - TVOC2_TRIP_BASE
        slot, field_index = divmod(offset, TVOC2_TRIP_STRIDE)
        if field_index == 6:
            return None  # her blogun 7. register'i BOSLUKTUR
        if slot >= len(self.trips):
            return TVOC2_EMPTY  # kilavuz 4.4.1: kayit yoksa 0xFFFF, sifir degil
        trip = self.trips[slot]
        return (
            trip.detector_low,
            trip.detector_high,
            trip.relay,
            days_since_epoch(trip.when.date()),
            encode_hhmm(trip.when.hour, trip.when.minute),
            trip.when.second,
        )[field_index]

    def note_write_attempt(self, pdu_address: int, value: int) -> None:
        """Yazma DENEMESINI kaydeder. Cihaz kabul etse de bizim ag gecidimiz
        engeller; bu kayit demoda GK6'nin kaniti olarak gosterilir."""
        self.write_attempts.append((pdu_address, value))


# ------------------------------------------------------------------ MPR-53CS

MPR_CT_REGISTER = 0x8001     # 32769; 2500/5 AT icin 500
MPR_VT_REGISTER = 0x8000     # 32768
MPR_CURRENT_SCALE = 0.001    # I_primer = ham * 0.001 * CT
MPR_VOLTAGE_SCALE = 0.1
MPR_THD_SCALE = 0.1
MPR_COSPHI_SCALE = 0.001
MPR_FREQ_SCALE = 0.01

# PDU adresleri (kilavuz; her olcum 2 register = 32 bit, word_order high_first).
MPR_ADDR = {
    "u_l1": 0, "u_l2": 2, "u_l3": 4,
    "i_l1": 6, "i_l2": 8, "i_l3": 10, "i_n": 12,
    "u_l1l2": 14, "u_l2l3": 16, "u_l3l1": 18,
    "cosphi_l1": 38, "cosphi_l2": 40, "cosphi_l3": 42,
    "freq": 58,
    "thd_u_l1": 72, "thd_u_l2": 74, "thd_u_l3": 76,
    "thd_i_l1": 78, "thd_i_l2": 80, "thd_i_l3": 82,
}
MPR_DIGITAL_OUT = 84   # TEK register (16-bit) — "her olcum 2 register" kuralinin istisnasi
MPR_DIGITAL_IN = 85


@dataclass
class Mpr53csDevice:
    """ENTES MPR-53CS sebeke analizoru — okunan degerler sozlesme olcegiyle.

    CT/VT DONUSUMU: kilavuzun RANGE kolonu "(0-6000)xCT" yazar ve iki turlu
    okunabilir. Proje sozlesmesi (rapor 15.1, contracts/modbus-map.yaml) ham degerin
    0-6000 araliginda gelip CT ile MASTER tarafinda carpilmasi yorumunu DONDURMUSTUR.
    Bu belirsizlik juriye acikca soylenir — zayiflik degil, olgunluk gostergesidir.
    """

    slave_id: int = 1
    ct_ratio: int = 500          # 2500/5 A akim trafosu
    vt_ratio: int = 10           # 0.1 olcekli register, 1.0 oran = dogrudan olcum
    i_ph: tuple[float, float, float] = (0.0, 0.0, 0.0)
    i_n: float = 0.0
    u_ph: tuple[float, float, float] = (231.0, 231.0, 231.0)
    thd_i: tuple[float, float, float] = (4.0, 4.0, 4.0)
    cosphi: float = 0.95
    frequency: float = 50.0
    comm_ok: bool = True
    write_attempts: list[tuple[int, int]] = field(default_factory=list)

    # ------------------------------------------------------------ donusum

    def current_raw(self, amps: float) -> int:
        """I_primer = ham * 0.001 * CT  =>  ham = I_primer / (0.001 * CT).

        Dogrulama (rapor 15.1): 2309 A, CT 500 -> ham 4618.
        """
        if self.ct_ratio <= 0:
            raise ValueError(f"CT orani pozitif olmali: {self.ct_ratio}")
        return int(round(amps / (MPR_CURRENT_SCALE * self.ct_ratio)))

    def current_from_raw(self, raw: int) -> float:
        return raw * MPR_CURRENT_SCALE * self.ct_ratio

    @staticmethod
    def voltage_raw(volts: float) -> int:
        return int(round(volts / MPR_VOLTAGE_SCALE))

    @staticmethod
    def thd_raw(percent: float) -> int:
        return int(round(percent / MPR_THD_SCALE))

    @staticmethod
    def cosphi_raw(value: float) -> int:
        return int(round(value / MPR_COSPHI_SCALE))

    @staticmethod
    def frequency_raw(hz: float) -> int:
        return int(round(hz / MPR_FREQ_SCALE))

    # ------------------------------------------------------------ register

    def registers(self) -> dict[int, int]:
        """PDU adresi -> 16-bit register degeri (32-bit olcumler iki register)."""
        values: dict[int, int] = {}

        def put32(address: int, value: int) -> None:
            # word_order high_first: yuksek word once.
            unsigned = value & 0xFFFFFFFF
            values[address] = (unsigned >> 16) & 0xFFFF
            values[address + 1] = unsigned & 0xFFFF

        for index, name in enumerate(("u_l1", "u_l2", "u_l3")):
            put32(MPR_ADDR[name], self.voltage_raw(self.u_ph[index]))
        for index, name in enumerate(("i_l1", "i_l2", "i_l3")):
            put32(MPR_ADDR[name], self.current_raw(self.i_ph[index]))
        put32(MPR_ADDR["i_n"], self.current_raw(self.i_n))
        for index, name in enumerate(("thd_i_l1", "thd_i_l2", "thd_i_l3")):
            put32(MPR_ADDR[name], self.thd_raw(self.thd_i[index]))
        for name in ("cosphi_l1", "cosphi_l2", "cosphi_l3"):
            put32(MPR_ADDR[name], self.cosphi_raw(self.cosphi))
        put32(MPR_ADDR["freq"], self.frequency_raw(self.frequency))

        values[MPR_DIGITAL_OUT] = 0x0000
        values[MPR_DIGITAL_IN] = 0x0000
        values[MPR_CT_REGISTER] = self.ct_ratio
        values[MPR_VT_REGISTER] = self.vt_ratio
        return values

    def note_write_attempt(self, pdu_address: int, value: int) -> None:
        self.write_attempts.append((pdu_address, value))
