# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""EoS Hardware Analyzer — reads schematics, BOMs, datasheets.

Extracts hardware metadata (MCU, peripherals, buses, memory, pins)
from design documents and produces a structured EosHardwareProfile that
downstream modules use to generate build configs.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PinMapping:
    """A single pin assignment from schematic analysis."""
    pin_id: str
    function: str
    port: str = ""
    af: int = 0
    direction: str = "io"


@dataclass
class MemoryRegion:
    """A memory region extracted from MCU datasheet or linker spec."""
    name: str
    base_addr: int
    size: int
    mem_type: str = "flash"
    permissions: str = "rx"


@dataclass
class PeripheralInfo:
    """A peripheral identified from the hardware design."""
    name: str
    peripheral_type: str
    bus: str = ""
    irq: int = -1
    pins: List[PinMapping] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HardwareProfile:
    """Complete hardware profile extracted from design documents."""
    mcu: str = ""
    mcu_family: str = ""
    arch: str = ""
    core: str = ""
    clock_hz: int = 0
    flash_size: int = 0
    ram_size: int = 0
    vendor: str = ""
    package: str = ""
    supply_voltage: float = 3.3

    peripherals: List[PeripheralInfo] = field(default_factory=list)
    memory_regions: List[MemoryRegion] = field(default_factory=list)
    pin_mappings: List[PinMapping] = field(default_factory=list)
    buses: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)

    source_files: List[str] = field(default_factory=list)
    confidence: float = 0.0

    def has_peripheral(self, name: str) -> bool:
        return any(p.peripheral_type.lower() == name.lower() for p in self.peripherals)

    def get_eos_enables(self) -> Dict[str, bool]:
        """Map detected peripherals to EoS EOS_ENABLE_* flags."""
        mapping = {
            "uart": "EOS_ENABLE_UART", "spi": "EOS_ENABLE_SPI",
            "i2c": "EOS_ENABLE_I2C", "gpio": "EOS_ENABLE_GPIO",
            "can": "EOS_ENABLE_CAN", "usb": "EOS_ENABLE_USB",
            "adc": "EOS_ENABLE_ADC", "dac": "EOS_ENABLE_DAC",
            "pwm": "EOS_ENABLE_PWM", "timer": "EOS_ENABLE_TIMER",
            "ethernet": "EOS_ENABLE_ETHERNET", "wifi": "EOS_ENABLE_WIFI",
            "ble": "EOS_ENABLE_BLE", "camera": "EOS_ENABLE_CAMERA",
            "display": "EOS_ENABLE_DISPLAY", "motor": "EOS_ENABLE_MOTOR",
            "watchdog": "EOS_ENABLE_WDT", "rtc": "EOS_ENABLE_RTC",
            "dma": "EOS_ENABLE_DMA", "flash": "EOS_ENABLE_FLASH",
            "nfc": "EOS_ENABLE_NFC", "gps": "EOS_ENABLE_GNSS",
            "imu": "EOS_ENABLE_IMU", "audio": "EOS_ENABLE_AUDIO",
        }
        enables = {}
        for p in self.peripherals:
            key = p.peripheral_type.lower()
            if key in mapping:
                enables[mapping[key]] = True
        return enables

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mcu": self.mcu, "mcu_family": self.mcu_family,
            "arch": self.arch, "core": self.core,
            "clock_hz": self.clock_hz,
            "flash_size": self.flash_size, "ram_size": self.ram_size,
            "vendor": self.vendor, "supply_voltage": self.supply_voltage,
            "peripherals": [
                {"name": p.name, "type": p.peripheral_type, "bus": p.bus}
                for p in self.peripherals
            ],
            "memory_regions": [
                {"name": m.name, "base": hex(m.base_addr), "size": m.size, "type": m.mem_type}
                for m in self.memory_regions
            ],
            "buses": self.buses, "features": self.features,
            "eos_enables": self.get_eos_enables(),
            "confidence": self.confidence,
        }


class EosHardwareAnalyzer:
    """Analyzes hardware design documents and extracts a HardwareProfile.

    Supports:
    - Text descriptions of hardware designs
    - KiCad schematic files (.kicad_sch)
    - BOM CSV/text files
    - MCU datasheet summaries
    - Pin assignment tables

    Works offline with built-in rule engine.
    Optional LLM backend for advanced schematic analysis.
    """

    # Known MCU families and their properties
    MCU_DATABASE = {
        # --- ARM Cortex-M (modern) ---
        "stm32f4": {"arch": "arm", "core": "cortex-m4", "vendor": "ST", "family": "STM32F4"},
        "stm32h7": {"arch": "arm", "core": "cortex-m7", "vendor": "ST", "family": "STM32H7"},
        "stm32mp1": {"arch": "arm", "core": "cortex-a7+m4", "vendor": "ST", "family": "STM32MP1"},
        "nrf52": {"arch": "arm", "core": "cortex-m4f", "vendor": "Nordic", "family": "nRF52"},
        "nrf52840": {"arch": "arm", "core": "cortex-m4f", "vendor": "Nordic", "family": "nRF52"},
        "samd51": {"arch": "arm", "core": "cortex-m4f", "vendor": "Microchip", "family": "SAMD51"},
        "rp2040": {"arch": "arm", "core": "cortex-m0+", "vendor": "Raspberry Pi", "family": "RP2040"},
        # --- ARM Cortex-A (application) ---
        "imx8m": {"arch": "arm64", "core": "cortex-a53", "vendor": "NXP", "family": "i.MX8M"},
        "am64x": {"arch": "arm", "core": "cortex-a53+r5f", "vendor": "TI", "family": "AM64x"},
        # --- ARM Cortex-R (real-time / safety) ---
        "tms570": {"arch": "arm", "core": "cortex-r5f", "vendor": "TI", "family": "TMS570"},
        "tms570lc": {"arch": "arm", "core": "cortex-r5f", "vendor": "TI", "family": "TMS570"},
        "rm57": {"arch": "arm", "core": "cortex-r5f", "vendor": "TI", "family": "RM57"},
        "rm46": {"arch": "arm", "core": "cortex-r4f", "vendor": "TI", "family": "RM46"},
        "rz_t1": {"arch": "arm", "core": "cortex-r4f", "vendor": "Renesas", "family": "RZ/T"},
        # --- Intel StrongARM ---
        "sa110": {"arch": "arm", "core": "strongarm-110", "vendor": "Intel", "family": "StrongARM"},
        "sa1100": {"arch": "arm", "core": "strongarm-1100", "vendor": "Intel", "family": "StrongARM"},
        "sa1110": {"arch": "arm", "core": "strongarm-1110", "vendor": "Intel", "family": "StrongARM"},
        # --- Intel XScale ---
        "pxa250": {"arch": "arm", "core": "xscale", "vendor": "Intel", "family": "XScale"},
        "pxa255": {"arch": "arm", "core": "xscale", "vendor": "Intel", "family": "XScale"},
        "pxa270": {"arch": "arm", "core": "xscale", "vendor": "Intel", "family": "XScale"},
        "ixp420": {"arch": "arm", "core": "xscale", "vendor": "Intel", "family": "XScale"},
        "ixp425": {"arch": "arm", "core": "xscale", "vendor": "Intel", "family": "XScale"},
        "ixp465": {"arch": "arm", "core": "xscale", "vendor": "Intel", "family": "XScale"},
        # --- Fujitsu FR-V (VLIW) ---
        "fr400": {"arch": "frv", "core": "fr400", "vendor": "Fujitsu", "family": "FR-V"},
        "fr450": {"arch": "frv", "core": "fr450", "vendor": "Fujitsu", "family": "FR-V"},
        "fr500": {"arch": "frv", "core": "fr500", "vendor": "Fujitsu", "family": "FR-V"},
        "fr550": {"arch": "frv", "core": "fr550", "vendor": "Fujitsu", "family": "FR-V"},
        "mb93091": {"arch": "frv", "core": "fr400", "vendor": "Fujitsu", "family": "FR-V"},
        "mb93493": {"arch": "frv", "core": "fr400", "vendor": "Fujitsu", "family": "FR-V"},
        # --- Hitachi/Renesas SuperH (SH2/SH3/SH4) ---
        "sh7604": {"arch": "sh", "core": "sh2", "vendor": "Renesas", "family": "SH2"},
        "sh7091": {"arch": "sh", "core": "sh4", "vendor": "Renesas", "family": "SH4"},
        "sh7750": {"arch": "sh", "core": "sh4", "vendor": "Renesas", "family": "SH4"},
        "sh7751": {"arch": "sh", "core": "sh4", "vendor": "Renesas", "family": "SH4"},
        "sh7709": {"arch": "sh", "core": "sh3", "vendor": "Renesas", "family": "SH3"},
        "sh7710": {"arch": "sh", "core": "sh3", "vendor": "Renesas", "family": "SH3"},
        "sh7203": {"arch": "sh", "core": "sh2a", "vendor": "Renesas", "family": "SH2A"},
        "sh7206": {"arch": "sh", "core": "sh2a", "vendor": "Renesas", "family": "SH2A"},
        # --- Hitachi/Renesas H8/300H ---
        "h8300h": {"arch": "h8300", "core": "h8/300h", "vendor": "Renesas", "family": "H8/300H"},
        "h8s2148": {"arch": "h8300", "core": "h8s", "vendor": "Renesas", "family": "H8S"},
        "h8s2368": {"arch": "h8300", "core": "h8s", "vendor": "Renesas", "family": "H8S"},
        "h83048": {"arch": "h8300", "core": "h8/300h", "vendor": "Renesas", "family": "H8/300H"},
        "h83069": {"arch": "h8300", "core": "h8/300h", "vendor": "Renesas", "family": "H8/300H"},
        # --- Intel x86 ---
        "i386": {"arch": "x86", "core": "i386", "vendor": "Intel", "family": "x86"},
        "i486": {"arch": "x86", "core": "i486", "vendor": "Intel", "family": "x86"},
        "pentium": {"arch": "x86", "core": "pentium", "vendor": "Intel", "family": "x86"},
        "x86_64": {"arch": "x86_64", "core": "x86_64", "vendor": "Intel", "family": "x86_64"},
        "atom": {"arch": "x86", "core": "atom", "vendor": "Intel", "family": "x86"},
        "quark": {"arch": "x86", "core": "quark", "vendor": "Intel", "family": "x86"},
        # --- MIPS ---
        "mips32": {"arch": "mips", "core": "mips32", "vendor": "MIPS", "family": "MIPS32"},
        "mips64": {"arch": "mips64", "core": "mips64", "vendor": "MIPS", "family": "MIPS64"},
        "mips24k": {"arch": "mips", "core": "mips32r2", "vendor": "MIPS", "family": "MIPS32"},
        "mips34k": {"arch": "mips", "core": "mips32r2", "vendor": "MIPS", "family": "MIPS32"},
        "pic32": {"arch": "mips", "core": "mips32r2", "vendor": "Microchip", "family": "PIC32"},
        "jz4740": {"arch": "mips", "core": "mips32", "vendor": "Ingenic", "family": "XBurst"},
        "ar9331": {"arch": "mips", "core": "mips24k", "vendor": "Qualcomm", "family": "MIPS32"},
        # --- Matsushita/Panasonic AM3x (MN103) ---
        "mn1030": {"arch": "mn103", "core": "am30", "vendor": "Panasonic", "family": "AM30"},
        "mn103s": {"arch": "mn103", "core": "am33", "vendor": "Panasonic", "family": "AM33"},
        "am33": {"arch": "mn103", "core": "am33", "vendor": "Panasonic", "family": "AM33"},
        "am34": {"arch": "mn103", "core": "am34", "vendor": "Panasonic", "family": "AM34"},
        # --- Motorola/Freescale/NXP PowerPC ---
        "mpc8xx": {"arch": "powerpc", "core": "ppc", "vendor": "NXP", "family": "MPC8xx"},
        "mpc5200": {"arch": "powerpc", "core": "ppc", "vendor": "NXP", "family": "MPC5xxx"},
        "mpc5554": {"arch": "powerpc", "core": "e200", "vendor": "NXP", "family": "MPC55xx"},
        "mpc8260": {"arch": "powerpc", "core": "ppc", "vendor": "NXP", "family": "MPC8xxx"},
        "mpc8540": {"arch": "powerpc", "core": "e500", "vendor": "NXP", "family": "MPC85xx"},
        "p1020": {"arch": "powerpc", "core": "e500v2", "vendor": "NXP", "family": "QorIQ"},
        "p2020": {"arch": "powerpc", "core": "e500v2", "vendor": "NXP", "family": "QorIQ"},
        "t1040": {"arch": "powerpc", "core": "e5500", "vendor": "NXP", "family": "QorIQ"},
        "ppc440": {"arch": "powerpc", "core": "ppc440", "vendor": "IBM", "family": "PPC4xx"},
        "ppc405": {"arch": "powerpc", "core": "ppc405", "vendor": "IBM", "family": "PPC4xx"},
        # --- Motorola 68k / ColdFire ---
        "mc68000": {"arch": "m68k", "core": "68000", "vendor": "Motorola", "family": "68k"},
        "mc68020": {"arch": "m68k", "core": "68020", "vendor": "Motorola", "family": "68k"},
        "mc68030": {"arch": "m68k", "core": "68030", "vendor": "Motorola", "family": "68k"},
        "mc68040": {"arch": "m68k", "core": "68040", "vendor": "Motorola", "family": "68k"},
        "mc68060": {"arch": "m68k", "core": "68060", "vendor": "Motorola", "family": "68k"},
        "mcf5206": {"arch": "m68k", "core": "coldfire-v2", "vendor": "NXP", "family": "ColdFire"},
        "mcf5272": {"arch": "m68k", "core": "coldfire-v2", "vendor": "NXP", "family": "ColdFire"},
        "mcf5307": {"arch": "m68k", "core": "coldfire-v3", "vendor": "NXP", "family": "ColdFire"},
        "mcf5407": {"arch": "m68k", "core": "coldfire-v4", "vendor": "NXP", "family": "ColdFire"},
        "mcf5475": {"arch": "m68k", "core": "coldfire-v4e", "vendor": "NXP", "family": "ColdFire"},
        "mcf5282": {"arch": "m68k", "core": "coldfire-v2", "vendor": "NXP", "family": "ColdFire"},
        "mcf52235": {"arch": "m68k", "core": "coldfire-v2", "vendor": "NXP", "family": "ColdFire"},
        "mcf54418": {"arch": "m68k", "core": "coldfire-v4", "vendor": "NXP", "family": "ColdFire"},
        # --- NEC/Renesas V850 ---
        "v850": {"arch": "v850", "core": "v850", "vendor": "Renesas", "family": "V850"},
        "v850e": {"arch": "v850", "core": "v850e", "vendor": "Renesas", "family": "V850E"},
        "v850e2": {"arch": "v850", "core": "v850e2", "vendor": "Renesas", "family": "V850E2"},
        "v850es": {"arch": "v850", "core": "v850es", "vendor": "Renesas", "family": "V850ES"},
        "upd70f3002": {"arch": "v850", "core": "v850e", "vendor": "Renesas", "family": "V850E"},
        "rh850": {"arch": "v850", "core": "rh850", "vendor": "Renesas", "family": "RH850"},
        # --- Sun/Oracle SPARC ---
        "sparc": {"arch": "sparc", "core": "sparc-v8", "vendor": "Sun", "family": "SPARC"},
        "leon3": {"arch": "sparc", "core": "leon3", "vendor": "Gaisler", "family": "LEON"},
        "leon4": {"arch": "sparc", "core": "leon4", "vendor": "Gaisler", "family": "LEON"},
        "ut699": {"arch": "sparc", "core": "leon3ft", "vendor": "Cobham", "family": "LEON"},
        "gr712rc": {"arch": "sparc", "core": "leon3ft", "vendor": "Gaisler", "family": "LEON"},
        "erc32": {"arch": "sparc", "core": "sparc-v7", "vendor": "ESA", "family": "ERC32"},
        "ultrasparc": {"arch": "sparc64", "core": "sparc-v9", "vendor": "Sun", "family": "UltraSPARC"},
        # --- Espressif Xtensa ---
        "esp32": {"arch": "xtensa", "core": "lx6", "vendor": "Espressif", "family": "ESP32"},
        # --- RISC-V ---
        "sifive_e": {"arch": "riscv32", "core": "rv32imac", "vendor": "SiFive", "family": "E-Series"},
        "sifive_u": {"arch": "riscv64", "core": "rv64gc", "vendor": "SiFive", "family": "U-Series"},
        "gd32vf103": {"arch": "riscv32", "core": "rv32imac", "vendor": "GigaDevice", "family": "GD32VF"},
    }

    PERIPHERAL_KEYWORDS = {
        "uart": "uart", "usart": "uart", "serial": "uart",
        "spi": "spi", "i2c": "i2c", "iic": "i2c",
        "can": "can", "canfd": "can",
        "usb": "usb", "otg": "usb",
        "adc": "adc", "dac": "dac",
        "pwm": "pwm", "timer": "timer",
        "gpio": "gpio",
        "ethernet": "ethernet", "eth": "ethernet", "rmii": "ethernet", "mdio": "ethernet",
        "wifi": "wifi", "wlan": "wifi",
        "bluetooth": "ble", "ble": "ble",
        "camera": "camera", "csi": "camera", "dcmi": "camera",
        "display": "display", "lcd": "display", "ltdc": "display",
        "sdio": "sdio", "sdmmc": "sdio",
        "watchdog": "watchdog", "iwdg": "watchdog", "wwdg": "watchdog",
        "rtc": "rtc",
        "dma": "dma",
        "motor": "motor",
        "nfc": "nfc",
        "gps": "gps", "gnss": "gps",
        "imu": "imu", "accelerometer": "imu", "gyroscope": "imu",
        "audio": "audio", "i2s": "audio", "sai": "audio",
    }

    def __init__(self, eos_schemas_path: Optional[str] = None):
        self.eos_schemas_path = Path(eos_schemas_path) if eos_schemas_path else None
        self._component_db = None
        self._kicad_parser = None
        self._eagle_parser = None
        self._llm_client = None

    @property
    def component_db(self):
        if self._component_db is None:
            from ebuild.eos_ai.component_db import ComponentDB
            self._component_db = ComponentDB()
        return self._component_db

    @property
    def kicad_parser(self):
        if self._kicad_parser is None:
            from ebuild.eos_ai.kicad_parser import KiCadParser
            self._kicad_parser = KiCadParser()
        return self._kicad_parser

    @property
    def eagle_parser(self):
        if self._eagle_parser is None:
            from ebuild.eos_ai.eagle_parser import EagleParser
            self._eagle_parser = EagleParser()
        return self._eagle_parser

    @property
    def llm_client(self):
        if self._llm_client is None:
            from ebuild.eos_ai.llm_integration import LLMClient
            self._llm_client = LLMClient.auto()
        return self._llm_client

    def interpret_text(self, description: str) -> HardwareProfile:
        """Interpret a text description of a hardware design."""
        profile = HardwareProfile()
        profile.confidence = 0.6
        text = description.lower()

        # Detect MCU
        for mcu_key, props in self.MCU_DATABASE.items():
            if mcu_key in text:
                profile.mcu = mcu_key.upper()
                profile.mcu_family = props["family"]
                profile.arch = props["arch"]
                profile.core = props["core"]
                profile.vendor = props["vendor"]
                profile.confidence = 0.8
                break

        # Detect peripherals
        seen = set()
        for keyword, ptype in self.PERIPHERAL_KEYWORDS.items():
            if keyword in text and ptype not in seen:
                profile.peripherals.append(PeripheralInfo(
                    name=ptype.upper(), peripheral_type=ptype
                ))
                seen.add(ptype)

        # Detect memory sizes
        flash_match = re.search(r'(\d+)\s*[mk]b?\s*flash', text)
        if flash_match:
            val = int(flash_match.group(1))
            profile.flash_size = val * 1024 if 'k' in text[flash_match.start():flash_match.end()] else val * 1024 * 1024

        ram_match = re.search(r'(\d+)\s*[mk]b?\s*(?:sr)?ram', text)
        if ram_match:
            val = int(ram_match.group(1))
            profile.ram_size = val * 1024 if 'k' in text[ram_match.start():ram_match.end()] else val * 1024 * 1024

        # Detect clock
        clock_match = re.search(r'(\d+)\s*mhz', text)
        if clock_match:
            profile.clock_hz = int(clock_match.group(1)) * 1_000_000

        return profile

    def interpret_bom(self, bom_text: str) -> HardwareProfile:
        """Interpret a Bill of Materials with component database lookup."""
        profile = self.interpret_text(bom_text)
        profile.source_files.append("bom")

        for line in bom_text.strip().split('\n'):
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 2:
                continue

            ref = parts[0]
            value = parts[1] if len(parts) > 1 else ""
            desc = parts[2] if len(parts) > 2 else ""
            combined = f"{ref} {value} {desc}"

            # Component DB lookup — identifies part numbers like TMP102, W25Q128, etc.
            db_results = self.component_db.search(combined)
            for comp_info in db_results:
                ptype = comp_info.peripheral_type
                if not any(p.peripheral_type == ptype for p in profile.peripherals):
                    config: Dict[str, Any] = {}
                    if comp_info.i2c_addr >= 0:
                        config["i2c_addr"] = hex(comp_info.i2c_addr)
                    if comp_info.vendor:
                        config["vendor"] = comp_info.vendor
                    profile.peripherals.append(PeripheralInfo(
                        name=comp_info.part,
                        peripheral_type=ptype,
                        bus=comp_info.bus,
                        config=config,
                    ))

            # Fallback to keyword matching for unrecognized parts
            if not db_results:
                combined_lower = combined.lower()
                for keyword, ptype in self.PERIPHERAL_KEYWORDS.items():
                    if keyword in combined_lower:
                        if not any(p.peripheral_type == ptype for p in profile.peripherals):
                            profile.peripherals.append(PeripheralInfo(
                                name=f"{ref}_{ptype}", peripheral_type=ptype
                            ))

        profile.confidence = max(profile.confidence, 0.75)
        return profile

    def interpret_kicad(self, filepath: str) -> HardwareProfile:
        """Parse a KiCad schematic file (.kicad_sch) with proper S-expression parsing."""
        profile = HardwareProfile()
        profile.source_files.append(filepath)

        path = Path(filepath)
        if not path.exists():
            return profile

        # Use proper KiCad parser for structured extraction
        result = self.kicad_parser.parse(filepath)

        if result.errors:
            # Fallback to text-based extraction on parse errors
            content = path.read_text(encoding="utf-8", errors="replace")
            return self.interpret_text(content)

        # Extract MCU from parsed components
        mcu_comp = result.find_mcu()
        if mcu_comp:
            text_profile = self.interpret_text(mcu_comp.value)
            profile.mcu = text_profile.mcu
            profile.mcu_family = text_profile.mcu_family
            profile.arch = text_profile.arch
            profile.core = text_profile.core
            profile.vendor = text_profile.vendor

        # Identify peripherals from components using component database
        seen_types: set = set()
        for comp in result.components:
            db_results = self.component_db.search(comp.value)
            for comp_info in db_results:
                ptype = comp_info.peripheral_type
                if ptype not in seen_types:
                    config: Dict[str, Any] = {}
                    if comp_info.i2c_addr >= 0:
                        config["i2c_addr"] = hex(comp_info.i2c_addr)
                    profile.peripherals.append(PeripheralInfo(
                        name=comp_info.part,
                        peripheral_type=ptype,
                        bus=comp_info.bus,
                        config=config,
                    ))
                    seen_types.add(ptype)

            # Fallback: keyword match on component value/lib_id
            combined = f"{comp.value} {comp.lib_id} {comp.footprint}".lower()
            for keyword, ptype in self.PERIPHERAL_KEYWORDS.items():
                if keyword in combined and ptype not in seen_types:
                    profile.peripherals.append(PeripheralInfo(
                        name=f"{comp.reference}_{ptype}", peripheral_type=ptype
                    ))
                    seen_types.add(ptype)

        # Extract net-based peripheral connections (SDA, MOSI, UART_TX, etc.)
        connections = self.kicad_parser.infer_peripheral_connections(result)
        for bus_name, pins in connections.items():
            bus_type = bus_name.split("_")[0].lower()
            if bus_type == "i2c" and "i2c" not in seen_types:
                profile.peripherals.append(PeripheralInfo(
                    name="I2C", peripheral_type="i2c", bus="i2c"
                ))
                seen_types.add("i2c")
            elif bus_type == "spi" and "spi" not in seen_types:
                profile.peripherals.append(PeripheralInfo(
                    name="SPI", peripheral_type="spi", bus="spi"
                ))
                seen_types.add("spi")
            elif bus_type == "uart" and "uart" not in seen_types:
                profile.peripherals.append(PeripheralInfo(
                    name="UART", peripheral_type="uart", bus="uart"
                ))
                seen_types.add("uart")
            elif bus_type == "can" and "can" not in seen_types:
                profile.peripherals.append(PeripheralInfo(
                    name="CAN", peripheral_type="can", bus="can"
                ))
                seen_types.add("can")

        profile.confidence = 0.85
        return profile

    def interpret_eagle(self, filepath: str) -> HardwareProfile:
        """Parse an Eagle schematic file (.sch XML) for components and nets."""
        profile = HardwareProfile()
        profile.source_files.append(filepath)

        path = Path(filepath)
        if not path.exists():
            return profile

        result = self.eagle_parser.parse(filepath)

        if result.errors:
            content = path.read_text(encoding="utf-8", errors="replace")
            return self.interpret_text(content)

        # Extract MCU
        mcu_comp = result.find_mcu()
        if mcu_comp:
            text_profile = self.interpret_text(mcu_comp.value)
            profile.mcu = text_profile.mcu
            profile.mcu_family = text_profile.mcu_family
            profile.arch = text_profile.arch
            profile.core = text_profile.core
            profile.vendor = text_profile.vendor

        # Identify peripherals from Eagle components
        seen_types: set = set()
        for comp in result.components:
            db_results = self.component_db.search(comp.value)
            for comp_info in db_results:
                ptype = comp_info.peripheral_type
                if ptype not in seen_types:
                    config: Dict[str, Any] = {}
                    if comp_info.i2c_addr >= 0:
                        config["i2c_addr"] = hex(comp_info.i2c_addr)
                    profile.peripherals.append(PeripheralInfo(
                        name=comp_info.part,
                        peripheral_type=ptype,
                        bus=comp_info.bus,
                        config=config,
                    ))
                    seen_types.add(ptype)

            combined = f"{comp.value} {comp.deviceset} {comp.library}".lower()
            for keyword, ptype in self.PERIPHERAL_KEYWORDS.items():
                if keyword in combined and ptype not in seen_types:
                    profile.peripherals.append(PeripheralInfo(
                        name=f"{comp.name}_{ptype}", peripheral_type=ptype
                    ))
                    seen_types.add(ptype)

        # Extract peripherals from net names (SDA, SCL, MOSI, etc.)
        for net in result.nets:
            net_lower = net.name.lower()
            for keyword, ptype in self.PERIPHERAL_KEYWORDS.items():
                if keyword in net_lower and ptype not in seen_types:
                    profile.peripherals.append(PeripheralInfo(
                        name=net.name, peripheral_type=ptype
                    ))
                    seen_types.add(ptype)

        profile.confidence = 0.80
        return profile

    def analyze_with_llm(self, profile: HardwareProfile) -> HardwareProfile:
        """Enhance a hardware profile using an LLM for deeper analysis.

        Sends the hardware profile to the configured LLM (Ollama local,
        OpenAI, or custom endpoint) and merges recommendations back.

        This is optional — the analyzer works without any LLM.
        Returns the original profile unchanged if no LLM is available.
        """
        if not self.llm_client.is_available():
            return profile

        prompt = self.generate_prompt(profile)
        response = self.llm_client.analyze(prompt)

        if not response.success:
            return profile

        # Parse LLM response for additional peripheral recommendations
        response_lower = response.text.lower()
        seen_types = {p.peripheral_type for p in profile.peripherals}

        for keyword, ptype in self.PERIPHERAL_KEYWORDS.items():
            if keyword in response_lower and ptype not in seen_types:
                profile.peripherals.append(PeripheralInfo(
                    name=f"llm_{ptype}", peripheral_type=ptype
                ))
                seen_types.add(ptype)

        profile.features.append(f"llm_analyzed:{self.llm_client.provider}")
        profile.confidence = min(profile.confidence + 0.1, 1.0)
        return profile

    def interpret_file(self, filepath: str) -> HardwareProfile:
        """Auto-detect file format and parse accordingly.

        Supported formats:
        - .kicad_sch → KiCad S-expression parser
        - .sch       → Eagle XML parser (if XML) or KiCad (if S-expr)
        - .csv       → BOM parser with component database
        - .yaml/.yml → Read as text, keyword extraction
        - .txt/.md   → Read as text, keyword extraction
        - any other  → Read as text, keyword extraction
        """
        path = Path(filepath)
        if not path.exists():
            return HardwareProfile()

        suffix = path.suffix.lower()

        if suffix == ".kicad_sch":
            return self.interpret_kicad(filepath)

        if suffix in (".sch", ".eagle"):
            # Detect if XML (Eagle) or S-expression (KiCad legacy)
            content = path.read_text(encoding="utf-8", errors="replace")
            if content.strip().startswith("<?xml") or content.strip().startswith("<eagle"):
                return self.interpret_eagle(filepath)
            return self.interpret_kicad(filepath)

        if suffix == ".csv":
            content = path.read_text(encoding="utf-8", errors="replace")
            return self.interpret_bom(content)

        # Default: read as text
        content = path.read_text(encoding="utf-8", errors="replace")
        profile = self.interpret_text(content)

        # Also run component DB search over the full text
        db_results = self.component_db.search(content)
        seen_types = {p.peripheral_type for p in profile.peripherals}
        for comp_info in db_results:
            ptype = comp_info.peripheral_type
            if ptype not in seen_types:
                config: Dict[str, Any] = {}
                if comp_info.i2c_addr >= 0:
                    config["i2c_addr"] = hex(comp_info.i2c_addr)
                profile.peripherals.append(PeripheralInfo(
                    name=comp_info.part,
                    peripheral_type=ptype,
                    bus=comp_info.bus,
                    config=config,
                ))
                seen_types.add(ptype)

        profile.source_files.append(filepath)
        return profile

    def generate_prompt(self, profile: HardwareProfile) -> str:
        """Generate an LLM prompt from a hardware profile for deeper analysis."""
        peripherals_str = ", ".join(p.peripheral_type for p in profile.peripherals)
        return f"""Analyze this embedded hardware design and suggest optimal configuration:

MCU: {profile.mcu} ({profile.core})
Architecture: {profile.arch}
Vendor: {profile.vendor}
Flash: {profile.flash_size} bytes
RAM: {profile.ram_size} bytes
Clock: {profile.clock_hz} Hz
Detected peripherals: {peripherals_str}

Please provide:
1. Recommended EoS product profile
2. Boot configuration for eboot (flash layout, slot sizes)
3. Memory map with MPU regions
4. Pin assignments for detected peripherals
5. Recommended RTOS (FreeRTOS/Zephyr/NuttX) and why

Output as YAML."""
