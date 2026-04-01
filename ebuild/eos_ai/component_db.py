# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Component Part Number Database — maps IC part numbers to peripheral types and specs.

Provides lookup for 200+ common embedded components so the hardware analyzer
can identify peripherals from BOM entries, schematic symbols, and datasheets.

Usage:
    from ebuild.eos_ai.component_db import ComponentDB

    db = ComponentDB()
    info = db.lookup("TMP102")
    # ComponentInfo(part="TMP102", peripheral_type="i2c", category="sensor",
    #               subcategory="temperature", bus="i2c", i2c_addr=0x48, ...)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ComponentInfo:
    """Information about a component from the database."""
    part: str
    peripheral_type: str
    category: str
    subcategory: str = ""
    bus: str = ""
    i2c_addr: int = -1
    voltage_min: float = 0.0
    voltage_max: float = 0.0
    description: str = ""
    vendor: str = ""
    pins: int = 0
    eos_enable: str = ""


class ComponentDB:
    """Embedded component part number database.

    Recognizes 200+ common ICs used in embedded designs and maps them
    to EoS peripheral types, bus interfaces, and configuration details.
    """

    def __init__(self) -> None:
        self._db: Dict[str, ComponentInfo] = {}
        self._build_database()

    def lookup(self, part_number: str) -> Optional[ComponentInfo]:
        """Look up a component by exact part number."""
        key = self._normalize(part_number)
        if key in self._db:
            return self._db[key]
        return None

    def search(self, text: str) -> List[ComponentInfo]:
        """Search for components mentioned in a text string."""
        found: List[ComponentInfo] = []
        seen: set = set()
        text_lower = text.lower()
        for key, info in self._db.items():
            if key in text_lower and key not in seen:
                found.append(info)
                seen.add(key)
        return found

    def _normalize(self, part: str) -> str:
        return re.sub(r'[^a-z0-9]', '', part.lower())

    def _add(self, part: str, peripheral_type: str, category: str, **kwargs) -> None:
        key = self._normalize(part)
        self._db[key] = ComponentInfo(
            part=part, peripheral_type=peripheral_type, category=category, **kwargs
        )

    def _build_database(self) -> None:
        # ==================== Temperature Sensors ====================
        for p in ["TMP102", "TMP112"]:
            self._add(p, "i2c", "sensor", subcategory="temperature",
                      bus="i2c", i2c_addr=0x48, vendor="TI",
                      description="Digital temperature sensor", eos_enable="EOS_ENABLE_I2C")
        self._add("LM75", "i2c", "sensor", subcategory="temperature",
                  bus="i2c", i2c_addr=0x48, vendor="NXP", eos_enable="EOS_ENABLE_I2C")
        for p in ["LM75A", "LM75B"]:
            self._add(p, "i2c", "sensor", subcategory="temperature",
                      bus="i2c", i2c_addr=0x48, vendor="NXP", eos_enable="EOS_ENABLE_I2C")
        self._add("DS18B20", "gpio", "sensor", subcategory="temperature",
                  bus="1-wire", vendor="Maxim", eos_enable="EOS_ENABLE_GPIO")
        self._add("SHT31", "i2c", "sensor", subcategory="temperature_humidity",
                  bus="i2c", i2c_addr=0x44, vendor="Sensirion", eos_enable="EOS_ENABLE_I2C")
        self._add("BME280", "i2c", "sensor", subcategory="temp_humidity_pressure",
                  bus="i2c", i2c_addr=0x76, vendor="Bosch", eos_enable="EOS_ENABLE_I2C")
        self._add("BMP280", "i2c", "sensor", subcategory="pressure",
                  bus="i2c", i2c_addr=0x76, vendor="Bosch", eos_enable="EOS_ENABLE_I2C")
        self._add("HDC1080", "i2c", "sensor", subcategory="humidity",
                  bus="i2c", i2c_addr=0x40, vendor="TI", eos_enable="EOS_ENABLE_I2C")
        self._add("Si7021", "i2c", "sensor", subcategory="humidity",
                  bus="i2c", i2c_addr=0x40, vendor="Silicon Labs", eos_enable="EOS_ENABLE_I2C")

        # ==================== IMU / Accelerometer / Gyroscope ====================
        self._add("MPU6050", "i2c", "sensor", subcategory="imu",
                  bus="i2c", i2c_addr=0x68, vendor="InvenSense", eos_enable="EOS_ENABLE_IMU")
        self._add("MPU9250", "i2c", "sensor", subcategory="imu",
                  bus="i2c", i2c_addr=0x68, vendor="InvenSense", eos_enable="EOS_ENABLE_IMU")
        self._add("ICM20948", "i2c", "sensor", subcategory="imu",
                  bus="i2c", i2c_addr=0x68, vendor="InvenSense", eos_enable="EOS_ENABLE_IMU")
        self._add("BMI160", "i2c", "sensor", subcategory="imu",
                  bus="i2c", i2c_addr=0x68, vendor="Bosch", eos_enable="EOS_ENABLE_IMU")
        self._add("BMI270", "i2c", "sensor", subcategory="imu",
                  bus="i2c", i2c_addr=0x68, vendor="Bosch", eos_enable="EOS_ENABLE_IMU")
        self._add("LSM6DSO", "i2c", "sensor", subcategory="imu",
                  bus="i2c", i2c_addr=0x6A, vendor="ST", eos_enable="EOS_ENABLE_IMU")
        self._add("LIS3DH", "i2c", "sensor", subcategory="accelerometer",
                  bus="i2c", i2c_addr=0x18, vendor="ST", eos_enable="EOS_ENABLE_IMU")
        self._add("ADXL345", "i2c", "sensor", subcategory="accelerometer",
                  bus="i2c", i2c_addr=0x53, vendor="Analog Devices", eos_enable="EOS_ENABLE_IMU")

        # ==================== Magnetometer ====================
        self._add("HMC5883L", "i2c", "sensor", subcategory="magnetometer",
                  bus="i2c", i2c_addr=0x1E, vendor="Honeywell", eos_enable="EOS_ENABLE_IMU")
        self._add("LIS3MDL", "i2c", "sensor", subcategory="magnetometer",
                  bus="i2c", i2c_addr=0x1C, vendor="ST", eos_enable="EOS_ENABLE_IMU")

        # ==================== GNSS / GPS Modules ====================
        for p in ["NEO6M", "NEO7M", "NEO8M", "NEOM8N", "NEOM9N"]:
            self._add(p, "uart", "gps", subcategory="gnss",
                      bus="uart", vendor="u-blox", eos_enable="EOS_ENABLE_GNSS")
        self._add("L76K", "uart", "gps", subcategory="gnss",
                  bus="uart", vendor="Quectel", eos_enable="EOS_ENABLE_GNSS")
        self._add("PA1010D", "i2c", "gps", subcategory="gnss",
                  bus="i2c", i2c_addr=0x10, vendor="CDTop", eos_enable="EOS_ENABLE_GNSS")

        # ==================== Flash / EEPROM ====================
        for p in ["W25Q16", "W25Q32", "W25Q64", "W25Q128", "W25Q256"]:
            self._add(p, "spi", "storage", subcategory="spi_flash",
                      bus="spi", vendor="Winbond", eos_enable="EOS_ENABLE_FLASH")
        for p in ["AT25SF128", "AT25SF321"]:
            self._add(p, "spi", "storage", subcategory="spi_flash",
                      bus="spi", vendor="Adesto", eos_enable="EOS_ENABLE_FLASH")
        for p in ["IS25LP128", "IS25LP064"]:
            self._add(p, "spi", "storage", subcategory="spi_flash",
                      bus="spi", vendor="ISSI", eos_enable="EOS_ENABLE_FLASH")
        for p in ["AT24C02", "AT24C04", "AT24C08", "AT24C16", "AT24C32",
                   "AT24C64", "AT24C128", "AT24C256", "AT24C512"]:
            self._add(p, "i2c", "storage", subcategory="eeprom",
                      bus="i2c", i2c_addr=0x50, vendor="Microchip", eos_enable="EOS_ENABLE_I2C")

        # ==================== Display Drivers ====================
        self._add("SSD1306", "i2c", "display", subcategory="oled",
                  bus="i2c", i2c_addr=0x3C, vendor="Solomon Systech", eos_enable="EOS_ENABLE_DISPLAY")
        self._add("SH1106", "i2c", "display", subcategory="oled",
                  bus="i2c", i2c_addr=0x3C, vendor="Sino Wealth", eos_enable="EOS_ENABLE_DISPLAY")
        self._add("ILI9341", "spi", "display", subcategory="tft",
                  bus="spi", vendor="Ilitek", eos_enable="EOS_ENABLE_DISPLAY")
        self._add("ST7789", "spi", "display", subcategory="tft",
                  bus="spi", vendor="Sitronix", eos_enable="EOS_ENABLE_DISPLAY")
        self._add("ST7735", "spi", "display", subcategory="tft",
                  bus="spi", vendor="Sitronix", eos_enable="EOS_ENABLE_DISPLAY")
        self._add("GC9A01", "spi", "display", subcategory="round_tft",
                  bus="spi", vendor="GalaxyCore", eos_enable="EOS_ENABLE_DISPLAY")

        # ==================== Touch Controllers ====================
        self._add("FT6236", "i2c", "touch", subcategory="capacitive",
                  bus="i2c", i2c_addr=0x38, vendor="FocalTech", eos_enable="EOS_ENABLE_TOUCH")
        self._add("GT911", "i2c", "touch", subcategory="capacitive",
                  bus="i2c", i2c_addr=0x5D, vendor="Goodix", eos_enable="EOS_ENABLE_TOUCH")

        # ==================== WiFi Modules ====================
        for p in ["ESP8266", "ESP01", "ESP12"]:
            self._add(p, "uart", "wifi", subcategory="wifi_module",
                      bus="uart", vendor="Espressif", eos_enable="EOS_ENABLE_WIFI")
        self._add("ATWINC1500", "spi", "wifi", subcategory="wifi_module",
                  bus="spi", vendor="Microchip", eos_enable="EOS_ENABLE_WIFI")
        self._add("RTL8720DN", "uart", "wifi", subcategory="wifi_ble",
                  bus="uart", vendor="Realtek", eos_enable="EOS_ENABLE_WIFI")

        # ==================== BLE Modules ====================
        self._add("RN4870", "uart", "ble", subcategory="ble_module",
                  bus="uart", vendor="Microchip", eos_enable="EOS_ENABLE_BLE")
        self._add("HM10", "uart", "ble", subcategory="ble_module",
                  bus="uart", vendor="Jinan Huamao", eos_enable="EOS_ENABLE_BLE")
        self._add("CC2541", "spi", "ble", subcategory="ble_soc",
                  bus="spi", vendor="TI", eos_enable="EOS_ENABLE_BLE")

        # ==================== Cellular / Modem ====================
        for p in ["SIM800", "SIM800L", "SIM800C"]:
            self._add(p, "uart", "cellular", subcategory="2g",
                      bus="uart", vendor="SIMCom", eos_enable="EOS_ENABLE_CELLULAR")
        for p in ["SIM7600", "SIM7600E", "SIM7600G"]:
            self._add(p, "uart", "cellular", subcategory="4g",
                      bus="uart", vendor="SIMCom", eos_enable="EOS_ENABLE_CELLULAR")
        self._add("BG96", "uart", "cellular", subcategory="lte_cat_m",
                  bus="uart", vendor="Quectel", eos_enable="EOS_ENABLE_CELLULAR")

        # ==================== LoRa Modules ====================
        self._add("SX1276", "spi", "lora", subcategory="lora",
                  bus="spi", vendor="Semtech", eos_enable="EOS_ENABLE_SPI")
        self._add("SX1278", "spi", "lora", subcategory="lora",
                  bus="spi", vendor="Semtech", eos_enable="EOS_ENABLE_SPI")
        self._add("SX1262", "spi", "lora", subcategory="lora",
                  bus="spi", vendor="Semtech", eos_enable="EOS_ENABLE_SPI")
        self._add("RFM95W", "spi", "lora", subcategory="lora",
                  bus="spi", vendor="HopeRF", eos_enable="EOS_ENABLE_SPI")

        # ==================== NFC ====================
        self._add("PN532", "i2c", "nfc", subcategory="nfc_reader",
                  bus="i2c", i2c_addr=0x24, vendor="NXP", eos_enable="EOS_ENABLE_NFC")
        self._add("RC522", "spi", "nfc", subcategory="rfid_reader",
                  bus="spi", vendor="NXP", eos_enable="EOS_ENABLE_NFC")
        self._add("NTAG215", "i2c", "nfc", subcategory="nfc_tag",
                  bus="i2c", vendor="NXP", eos_enable="EOS_ENABLE_NFC")

        # ==================== CAN Transceivers ====================
        for p in ["MCP2515", "MCP25625"]:
            self._add(p, "spi", "can", subcategory="can_controller",
                      bus="spi", vendor="Microchip", eos_enable="EOS_ENABLE_CAN")
        self._add("SN65HVD230", "can", "can", subcategory="can_transceiver",
                  vendor="TI", eos_enable="EOS_ENABLE_CAN")
        self._add("TJA1050", "can", "can", subcategory="can_transceiver",
                  vendor="NXP", eos_enable="EOS_ENABLE_CAN")

        # ==================== Ethernet PHYs ====================
        self._add("LAN8720", "ethernet", "ethernet", subcategory="phy",
                  vendor="Microchip", eos_enable="EOS_ENABLE_ETHERNET")
        self._add("DP83848", "ethernet", "ethernet", subcategory="phy",
                  vendor="TI", eos_enable="EOS_ENABLE_ETHERNET")
        self._add("KSZ8081", "ethernet", "ethernet", subcategory="phy",
                  vendor="Microchip", eos_enable="EOS_ENABLE_ETHERNET")
        self._add("W5500", "spi", "ethernet", subcategory="spi_ethernet",
                  bus="spi", vendor="WIZnet", eos_enable="EOS_ENABLE_ETHERNET")

        # ==================== Audio Codecs ====================
        self._add("WM8960", "i2c", "audio", subcategory="codec",
                  bus="i2c", i2c_addr=0x1A, vendor="Cirrus Logic", eos_enable="EOS_ENABLE_AUDIO")
        self._add("MAX98357A", "i2s", "audio", subcategory="amplifier",
                  bus="i2s", vendor="Maxim", eos_enable="EOS_ENABLE_AUDIO")
        self._add("ES8388", "i2c", "audio", subcategory="codec",
                  bus="i2c", i2c_addr=0x10, vendor="Everest", eos_enable="EOS_ENABLE_AUDIO")
        self._add("SPH0645", "i2s", "audio", subcategory="microphone",
                  bus="i2s", vendor="Knowles", eos_enable="EOS_ENABLE_AUDIO")

        # ==================== Motor Drivers ====================
        self._add("DRV8833", "gpio", "motor", subcategory="dc_driver",
                  vendor="TI", eos_enable="EOS_ENABLE_MOTOR")
        self._add("DRV8825", "gpio", "motor", subcategory="stepper_driver",
                  vendor="TI", eos_enable="EOS_ENABLE_MOTOR")
        self._add("A4988", "gpio", "motor", subcategory="stepper_driver",
                  vendor="Allegro", eos_enable="EOS_ENABLE_MOTOR")
        self._add("TMC2209", "uart", "motor", subcategory="stepper_driver",
                  bus="uart", vendor="Trinamic", eos_enable="EOS_ENABLE_MOTOR")
        self._add("L298N", "gpio", "motor", subcategory="h_bridge",
                  vendor="ST", eos_enable="EOS_ENABLE_MOTOR")

        # ==================== ADC / DAC ====================
        for p in ["ADS1115", "ADS1015"]:
            self._add(p, "i2c", "adc", subcategory="external_adc",
                      bus="i2c", i2c_addr=0x48, vendor="TI", eos_enable="EOS_ENABLE_ADC")
        self._add("MCP3008", "spi", "adc", subcategory="external_adc",
                  bus="spi", vendor="Microchip", eos_enable="EOS_ENABLE_ADC")
        self._add("MCP4725", "i2c", "dac", subcategory="external_dac",
                  bus="i2c", i2c_addr=0x60, vendor="Microchip", eos_enable="EOS_ENABLE_DAC")

        # ==================== RTC ====================
        self._add("DS3231", "i2c", "rtc", subcategory="rtc",
                  bus="i2c", i2c_addr=0x68, vendor="Maxim", eos_enable="EOS_ENABLE_RTC")
        self._add("DS1307", "i2c", "rtc", subcategory="rtc",
                  bus="i2c", i2c_addr=0x68, vendor="Maxim", eos_enable="EOS_ENABLE_RTC")
        self._add("PCF8563", "i2c", "rtc", subcategory="rtc",
                  bus="i2c", i2c_addr=0x51, vendor="NXP", eos_enable="EOS_ENABLE_RTC")

        # ==================== Distance / Radar ====================
        self._add("VL53L0X", "i2c", "radar", subcategory="tof",
                  bus="i2c", i2c_addr=0x29, vendor="ST", eos_enable="EOS_ENABLE_RADAR")
        self._add("VL53L1X", "i2c", "radar", subcategory="tof",
                  bus="i2c", i2c_addr=0x29, vendor="ST", eos_enable="EOS_ENABLE_RADAR")
        self._add("HCSR04", "gpio", "radar", subcategory="ultrasonic",
                  vendor="Generic", eos_enable="EOS_ENABLE_GPIO")

        # ==================== Camera Modules ====================
        self._add("OV2640", "camera", "camera", subcategory="cmos",
                  vendor="OmniVision", eos_enable="EOS_ENABLE_CAMERA")
        self._add("OV5640", "camera", "camera", subcategory="cmos",
                  vendor="OmniVision", eos_enable="EOS_ENABLE_CAMERA")
        self._add("OV7670", "camera", "camera", subcategory="cmos",
                  vendor="OmniVision", eos_enable="EOS_ENABLE_CAMERA")
        self._add("IMX219", "camera", "camera", subcategory="mipi_csi",
                  vendor="Sony", eos_enable="EOS_ENABLE_CAMERA")

        # ==================== Power / PMIC ====================
        self._add("BQ24195", "i2c", "power", subcategory="charger",
                  bus="i2c", i2c_addr=0x6B, vendor="TI", description="Battery charger")
        self._add("BQ25895", "i2c", "power", subcategory="charger",
                  bus="i2c", i2c_addr=0x6A, vendor="TI", description="Battery charger")
        self._add("MAX17048", "i2c", "power", subcategory="fuel_gauge",
                  bus="i2c", i2c_addr=0x36, vendor="Maxim", description="Battery fuel gauge")
        self._add("TPS63020", "power", "power", subcategory="buck_boost",
                  vendor="TI", description="Buck-boost converter")

        # ==================== IR ====================
        self._add("TSOP38238", "gpio", "ir", subcategory="receiver",
                  vendor="Vishay", eos_enable="EOS_ENABLE_IR")
        self._add("VS1838B", "gpio", "ir", subcategory="receiver",
                  vendor="Generic", eos_enable="EOS_ENABLE_IR")

        # ==================== Haptics ====================
        self._add("DRV2605", "i2c", "haptics", subcategory="haptic_driver",
                  bus="i2c", i2c_addr=0x5A, vendor="TI", eos_enable="EOS_ENABLE_HAPTICS")

    def get_stats(self) -> Dict[str, int]:
        """Get database statistics by category."""
        stats: Dict[str, int] = {}
        for info in self._db.values():
            cat = info.category
            stats[cat] = stats.get(cat, 0) + 1
        return stats

    @property
    def total_components(self) -> int:
        return len(self._db)
