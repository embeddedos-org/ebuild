# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Unit tests for ebuild EoS AI module.

Tests the hardware analyzer, config generator, validator, and boot integrator
without any external dependencies (no yaml, no pip install).
Runs standalone: python -m pytest tests/ or python tests/test_eos_ai.py
"""

import sys
import tempfile
import shutil
from pathlib import Path

import pytest

# pythonpath in pytest.ini handles this for pytest; keep for standalone mode.
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ebuild.eos_ai.eos_hw_analyzer import (
    EosHardwareAnalyzer, HardwareProfile, PeripheralInfo
)


@pytest.mark.ebuild
class TestHardwareAnalyzer:
    """Tests for EosHardwareAnalyzer."""

    def setup_method(self):
        self.analyzer = EosHardwareAnalyzer()

    def test_detect_stm32h7(self):
        profile = self.analyzer.interpret_text("STM32H7 board with UART and SPI")
        assert profile.mcu == "STM32H7"
        assert profile.arch == "arm"
        assert profile.core == "cortex-m7"
        assert profile.vendor == "ST"
        assert profile.confidence == 0.8

    def test_detect_nrf52(self):
        profile = self.analyzer.interpret_text("nRF52 module with BLE")
        assert profile.mcu == "NRF52"
        assert profile.arch == "arm"
        assert profile.core == "cortex-m4f"
        assert profile.vendor == "Nordic"

    def test_detect_esp32(self):
        profile = self.analyzer.interpret_text("ESP32 with WiFi and BLE")
        assert profile.mcu == "ESP32"
        assert profile.arch == "xtensa"
        assert profile.vendor == "Espressif"

    def test_detect_imx8m(self):
        profile = self.analyzer.interpret_text("imx8m SoC running Linux")
        assert profile.mcu == "IMX8M"
        assert profile.arch == "arm64"
        assert profile.core == "cortex-a53"

    def test_detect_rp2040(self):
        profile = self.analyzer.interpret_text("RP2040 Pico board")
        assert profile.mcu == "RP2040"
        assert profile.core == "cortex-m0+"

    def test_detect_peripherals(self):
        profile = self.analyzer.interpret_text(
            "Board with UART, SPI, I2C, CAN, USB, ADC, PWM, GPIO, Ethernet"
        )
        types = {p.peripheral_type for p in profile.peripherals}
        assert "uart" in types
        assert "spi" in types
        assert "i2c" in types
        assert "can" in types
        assert "usb" in types
        assert "adc" in types
        assert "pwm" in types
        assert "gpio" in types
        assert "ethernet" in types

    def test_detect_wireless(self):
        profile = self.analyzer.interpret_text("Device with WiFi, BLE, and NFC")
        types = {p.peripheral_type for p in profile.peripherals}
        assert "wifi" in types
        assert "ble" in types
        assert "nfc" in types

    def test_detect_sensors(self):
        profile = self.analyzer.interpret_text("Board with IMU, GPS, camera")
        types = {p.peripheral_type for p in profile.peripherals}
        assert "imu" in types
        assert "gps" in types
        assert "camera" in types

    def test_detect_flash_mb(self):
        profile = self.analyzer.interpret_text("MCU with 2MB flash")
        assert profile.flash_size == 2 * 1024 * 1024

    def test_detect_ram_kb(self):
        profile = self.analyzer.interpret_text("MCU with 256kb ram")
        assert profile.ram_size == 256 * 1024

    def test_detect_clock(self):
        profile = self.analyzer.interpret_text("System clock 480 MHz")
        assert profile.clock_hz == 480_000_000

    def test_no_mcu_detected(self):
        profile = self.analyzer.interpret_text("Some generic board description")
        assert profile.mcu == ""
        assert profile.confidence == 0.6

    def test_duplicate_peripherals_not_added(self):
        profile = self.analyzer.interpret_text("UART USART serial port")
        uart_count = sum(1 for p in profile.peripherals if p.peripheral_type == "uart")
        assert uart_count == 1

    def test_keyword_aliases(self):
        profile = self.analyzer.interpret_text("RMII ethernet, WLAN wifi, IIC i2c")
        types = {p.peripheral_type for p in profile.peripherals}
        assert "ethernet" in types
        assert "wifi" in types
        assert "i2c" in types

    def test_bom_parsing(self):
        bom = "U1, STM32H7, Microcontroller\nU2, LAN8742A, Ethernet PHY\nU3, BME280, Sensor I2C"
        profile = self.analyzer.interpret_bom(bom)
        assert profile.mcu == "STM32H7"
        assert "bom" in profile.source_files

    def test_generate_prompt(self):
        profile = HardwareProfile(mcu="STM32H7", arch="arm", core="cortex-m7",
                                  vendor="ST", flash_size=2097152, ram_size=1048576)
        profile.peripherals.append(PeripheralInfo(name="UART", peripheral_type="uart"))
        prompt = self.analyzer.generate_prompt(profile)
        assert "STM32H7" in prompt
        assert "cortex-m7" in prompt
        assert "uart" in prompt


@pytest.mark.ebuild
class TestHardwareProfile:
    """Tests for HardwareProfile dataclass."""

    def test_has_peripheral(self):
        profile = HardwareProfile()
        profile.peripherals.append(PeripheralInfo(name="U1", peripheral_type="uart"))
        assert profile.has_peripheral("uart") is True
        assert profile.has_peripheral("UART") is True
        assert profile.has_peripheral("spi") is False

    def test_get_eos_enables(self):
        profile = HardwareProfile()
        profile.peripherals.append(PeripheralInfo(name="U", peripheral_type="uart"))
        profile.peripherals.append(PeripheralInfo(name="S", peripheral_type="spi"))
        profile.peripherals.append(PeripheralInfo(name="B", peripheral_type="ble"))
        enables = profile.get_eos_enables()
        assert enables["EOS_ENABLE_UART"] is True
        assert enables["EOS_ENABLE_SPI"] is True
        assert enables["EOS_ENABLE_BLE"] is True
        assert "EOS_ENABLE_CAN" not in enables

    def test_to_dict(self):
        profile = HardwareProfile(mcu="STM32F4", arch="arm", core="cortex-m4")
        d = profile.to_dict()
        assert d["mcu"] == "STM32F4"
        assert d["arch"] == "arm"
        assert isinstance(d["peripherals"], list)
        assert isinstance(d["eos_enables"], dict)

    def test_empty_profile(self):
        profile = HardwareProfile()
        assert profile.mcu == ""
        assert profile.flash_size == 0
        assert len(profile.peripherals) == 0
        assert profile.confidence == 0.0


@pytest.mark.ebuild
@pytest.mark.integration
class TestEosAIIntegration:
    """Integration tests for the full EoS AI pipeline."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ebuild_test_")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_stm32h7_full_pipeline(self):
        """Full pipeline: text -> analyze -> profile -> enables."""
        analyzer = EosHardwareAnalyzer()
        profile = analyzer.interpret_text(
            "STM32H7 with 2MB flash, 1MB SRAM, 480 MHz, "
            "UART SPI I2C CAN USB Ethernet WiFi BLE PWM ADC watchdog RTC DMA"
        )
        assert profile.mcu == "STM32H7"
        assert profile.flash_size == 2 * 1024 * 1024
        assert profile.clock_hz == 480_000_000
        assert len(profile.peripherals) >= 10
        enables = profile.get_eos_enables()
        assert len(enables) >= 10
        assert "EOS_ENABLE_UART" in enables
        assert "EOS_ENABLE_ETHERNET" in enables

    def test_nrf52_ble_device(self):
        """Minimal BLE device detection."""
        analyzer = EosHardwareAnalyzer()
        profile = analyzer.interpret_text("nRF52 BLE sensor with I2C, 512KB flash, 64 MHz")
        assert profile.mcu == "NRF52"
        assert profile.has_peripheral("ble")
        assert profile.has_peripheral("i2c")
        assert profile.flash_size == 512 * 1024

    def test_unknown_mcu_still_detects_peripherals(self):
        """Even without MCU match, peripherals should be detected."""
        analyzer = EosHardwareAnalyzer()
        profile = analyzer.interpret_text("Custom board with UART, SPI, watchdog")
        assert profile.mcu == ""
        assert profile.has_peripheral("uart")
        assert profile.has_peripheral("spi")
        assert profile.has_peripheral("watchdog")


# Allow running standalone without pytest
if __name__ == "__main__":
    import traceback
    tests = [TestHardwareAnalyzer, TestHardwareProfile, TestEosAIIntegration]
    total = 0
    passed = 0
    failed = 0

    for TestClass in tests:
        instance = TestClass()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                total += 1
                if hasattr(instance, "setup_method"):
                    instance.setup_method()
                try:
                    getattr(instance, method_name)()
                    passed += 1
                    print(f"  PASS: {TestClass.__name__}.{method_name}")
                except Exception as e:
                    failed += 1
                    print(f"  FAIL: {TestClass.__name__}.{method_name} -- {e}")
                    traceback.print_exc()
                finally:
                    if hasattr(instance, "teardown_method"):
                        instance.teardown_method()

    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    print(f"{'='*50}")
    sys.exit(0 if failed == 0 else 1)