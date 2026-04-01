# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""EoS Project Generator — generates stripped-down eos/eboot codebases.

Takes a HardwareProfile (from ebuild analyze) and prunes the full eos and
eboot repositories to only the modules required for the target hardware.
Supports two output modes:
  - copy: standalone directory with just the needed files
  - branch: git branch in the existing repos with only required files

Can auto-clone eos/eboot from GitHub when local repos are not provided.

No LLM required — uses a deterministic rule engine to map EOS_ENABLE flags,
architecture, and product profile to the required source files.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ebuild.eos_ai.eos_hw_analyzer import HardwareProfile

# Default GitHub URLs for eos and eboot repositories
DEFAULT_EOS_REPO_URL = "https://github.com/spatchava/eos.git"
DEFAULT_EBOOT_REPO_URL = "https://github.com/spatchava/eboot.git"


@dataclass
class ProjectManifest:
    """Describes which files/dirs from eos and eboot are required."""
    eos_dirs: List[str] = field(default_factory=list)
    eos_files: List[str] = field(default_factory=list)
    eboot_dirs: List[str] = field(default_factory=list)
    eboot_files: List[str] = field(default_factory=list)
    eos_enables: Dict[str, bool] = field(default_factory=dict)
    eboot_board: str = ""
    eos_product: str = ""
    eos_platform: str = "rtos"
    # Additional components
    eos_toolchain: str = ""
    eos_examples: List[str] = field(default_factory=list)
    eos_extras: List[str] = field(default_factory=list)
    eboot_extras: List[str] = field(default_factory=list)


class EosProjectGenerator:
    """Generates stripped-down eos/eboot codebases tailored to specific hardware.

    Workflow:
        1. Accept a HardwareProfile (from ``ebuild analyze``)
        2. Map EOS_ENABLE flags → required eos source directories
        3. Map board/arch → required eboot files
        4. Copy only needed files (copy mode) or create git branch (branch mode)
        5. Generate tailored CMakeLists.txt for each stripped codebase
    """

    # ------------------------------------------------------------------
    # eos service directories keyed by the EOS_ENABLE flag that requires them
    # ------------------------------------------------------------------
    EOS_SERVICE_MAP: Dict[str, List[str]] = {
        "EOS_ENABLE_MOTOR": ["services/motor"],
        "EOS_ENABLE_CAMERA": ["services/sensor"],
        "EOS_ENABLE_DISPLAY": ["services/sensor"],
        "EOS_ENABLE_IMU": ["services/sensor"],
        "EOS_ENABLE_ETHERNET": ["net"],
        "EOS_ENABLE_WIFI": ["net"],
        "EOS_ENABLE_BLE": ["net"],
    }

    # Services that are always included regardless of enables
    EOS_CORE_DIRS: List[str] = [
        "hal",
        "kernel",
        "core",
        "drivers",
        "include",
        "services/crypto",
        "services/security",
        "services/os",
        "services/ota",
    ]

    # eos dirs included only when specific conditions are met
    EOS_OPTIONAL_DIRS: Dict[str, List[str]] = {
        "power": ["power"],
        "filesystem": ["services/filesystem"],
        "datacenter": ["services/datacenter"],
        "linux": ["services/linux"],
        "rtos": ["services/rtos"],
        "sensor": ["services/sensor"],
    }

    # Map MCU family → matching eboot board directory name
    MCU_TO_EBOOT_BOARD: Dict[str, str] = {
        # ARM Cortex-M/A (modern)
        "stm32f4": "stm32f4",
        "stm32h7": "stm32h7",
        "stm32h743": "stm32h7",
        "stm32mp1": "stm32mp1",
        "nrf52": "nrf52",
        "nrf52840": "nrf52",
        "rpi4": "rpi4",
        "rpi": "rpi4",
        "raspberrypi": "rpi4",
        "bcm2711": "rpi4",
        "riscv64_virt": "riscv64_virt",
        "esp32": "esp32",
        "x86_64_efi": "x86_64_efi",
        "imx8m": "imx8m",
        "am64x": "am64x",
        "am6442": "am64x",
        "samd51": "samd51",
        "sifive_u": "sifive_u",
        "sifive": "sifive_u",
        "fu740": "sifive_u",
        "qemu_arm64": "qemu_arm64",
        "qemuarm64": "qemu_arm64",
        "tms570": "cortex_r5",
        "rm57": "cortex_r5",
        "rm46": "cortex_r5",
        # Intel StrongARM
        "sa110": "strongarm",
        "sa1100": "strongarm",
        "sa1110": "strongarm",
        # Intel XScale
        "pxa250": "xscale",
        "pxa255": "xscale",
        "pxa270": "xscale",
        "ixp420": "xscale",
        "ixp425": "xscale",
        "ixp465": "xscale",
        # Fujitsu FR-V
        "fr400": "frv",
        "fr450": "frv",
        "fr500": "frv",
        "fr550": "frv",
        "mb93091": "frv",
        "mb93493": "frv",
        # Hitachi/Renesas SuperH
        "sh7604": "sh4",
        "sh7091": "sh4",
        "sh7750": "sh4",
        "sh7751": "sh4",
        "sh7709": "sh4",
        "sh7710": "sh4",
        "sh7203": "sh4",
        "sh7206": "sh4",
        # Hitachi/Renesas H8/300H
        "h8300h": "h8300",
        "h8s2148": "h8300",
        "h8s2368": "h8300",
        "h83048": "h8300",
        "h83069": "h8300",
        # Intel x86
        "i386": "x86",
        "i486": "x86",
        "pentium": "x86",
        "atom": "x86",
        "quark": "x86",
        # MIPS
        "mips32": "mips",
        "mips64": "mips",
        "mips24k": "mips",
        "mips34k": "mips",
        "pic32": "mips",
        "jz4740": "mips",
        "ar9331": "mips",
        # Matsushita/Panasonic AM3x
        "mn1030": "mn103",
        "mn103s": "mn103",
        "am33": "mn103",
        "am34": "mn103",
        # Motorola/NXP PowerPC
        "mpc8xx": "powerpc",
        "mpc5200": "powerpc",
        "mpc5554": "powerpc",
        "mpc8260": "powerpc",
        "mpc8540": "powerpc",
        "p1020": "powerpc",
        "p2020": "powerpc",
        "t1040": "powerpc",
        "ppc440": "powerpc",
        "ppc405": "powerpc",
        # Motorola 68k / ColdFire
        "mc68000": "m68k",
        "mc68020": "m68k",
        "mc68030": "m68k",
        "mc68040": "m68k",
        "mc68060": "m68k",
        "mcf5206": "m68k",
        "mcf5272": "m68k",
        "mcf5307": "m68k",
        "mcf5407": "m68k",
        "mcf5475": "m68k",
        "mcf5282": "m68k",
        "mcf52235": "m68k",
        "mcf54418": "m68k",
        # NEC/Renesas V850
        "v850": "v850",
        "v850e": "v850",
        "v850e2": "v850",
        "v850es": "v850",
        "upd70f3002": "v850",
        "rh850": "v850",
        # Sun/Oracle SPARC
        "sparc": "sparc",
        "leon3": "sparc",
        "leon4": "sparc",
        "ut699": "sparc",
        "gr712rc": "sparc",
        "erc32": "sparc",
        "ultrasparc": "sparc",
    }

    # eboot core files that are always needed
    EBOOT_CORE_ALWAYS: List[str] = [
        "core/bootctl.c",
        "core/image_verify.c",
        "core/slot_manager.c",
        "core/boot_policy.c",
        "core/recovery.c",
        "core/fw_services.c",
        "core/fw_update.c",
        "core/crypto_boot.c",
        "core/board_config.c",
        "core/storage.c",
        "core/clock_init.c",
        "core/power_init.c",
        "core/mpu_boot.c",
        "core/boot_menu.c",
        "core/device_table.c",
        "core/runtime_services.c",
    ]

    # eboot core files that are conditional on hardware features
    EBOOT_CORE_CONDITIONAL: Dict[str, Dict[str, Any]] = {
        "core/dram_init.c": {"needs_dram": True},
        "core/pci_enum.c": {"needs_pci": True},
        "core/bmc_handoff.c": {"needs_bmc": True},
        "core/ecc_scrub.c": {"needs_ecc": True},
        "core/multicore.c": {"needs_multicore": True},
        "core/rtos_boot.c": {"needs_rtos": True},
        "core/rtos_params.c": {"needs_rtos": True},
        "core/fw_transport_uart.c": {"needs_uart": True},
    }

    # Architectures that typically have external DRAM
    DRAM_ARCHS = {"arm64", "x86_64", "riscv64", "mips64", "sparc64", "powerpc"}
    # Architectures that may have PCIe
    PCI_ARCHS = {"arm64", "x86_64", "riscv64", "mips64", "sparc64", "powerpc"}
    # Architectures that may have BMC
    BMC_ARCHS = {"x86_64", "arm64", "powerpc", "sparc64"}
    # MCU families that have multicore
    MULTICORE_MCUS = {"stm32mp1", "stm32h7", "am64x", "rp2040", "t1040", "p2020",
                      "esp32", "nrf52840", "sifive_u", "fu740", "imx8m", "bcm2711", "rpi4"}

    # Map features/peripheral combos → product profile
    PRODUCT_MAP: Dict[str, List[str]] = {
        "iot": ["ble", "i2c", "spi", "gpio"],
        "gateway": ["ethernet", "wifi", "ble", "uart"],
        "robot": ["motor", "imu", "uart", "spi", "camera"],
        "drone": ["motor", "imu", "gps", "uart", "camera"],
        "wearable": ["ble", "display", "imu"],
        "watch": ["ble", "display", "imu", "adc"],
        "medical": ["ble", "adc", "i2c", "display"],
        "diagnostic": ["adc", "camera", "ethernet", "display"],
        "telemedicine": ["camera", "audio", "wifi", "ble"],
        "industrial": ["can", "uart", "spi", "adc"],
        "plc": ["can", "adc", "uart", "motor"],
        "automotive": ["can", "ethernet", "uart", "display"],
        "autonomous": ["camera", "imu", "gps", "ethernet"],
        "cockpit": ["display", "can", "imu", "gps", "audio"],
        "infotainment": ["display", "audio", "wifi", "ble"],
        "ev": ["can", "motor", "adc", "ethernet"],
        "smart_home": ["wifi", "ble", "gpio", "i2c"],
        "voice": ["audio", "wifi", "ble"],
        "fitness": ["ble", "imu", "adc"],
        "thermostat": ["wifi", "i2c", "display", "gpio"],
        "security_cam": ["camera", "wifi", "ethernet"],
        "smart_tv": ["display", "wifi", "audio", "ble"],
        "gaming": ["display", "audio", "usb", "wifi"],
        "xr_headset": ["display", "imu", "camera", "audio"],
        "computer": ["display", "usb", "ethernet", "wifi"],
        "mobile": ["display", "camera", "ble", "wifi", "audio"],
        "server": ["ethernet", "usb", "display"],
        "ai_edge": ["camera", "ethernet", "usb"],
        "router": ["ethernet", "wifi", "usb"],
        "adapter": ["usb", "ethernet", "wifi"],
        "telecom": ["ethernet", "usb"],
        "aerospace": ["can", "imu", "gps", "uart"],
        "satellite": ["adc", "imu", "gps", "uart"],
        "ground_control": ["display", "ethernet", "gps"],
        "space_comm": ["uart", "adc"],
        "pos": ["display", "ble", "wifi"],
        "banking": ["display", "ethernet", "usb"],
        "crypto_hw": ["ethernet", "usb"],
        "hmi": ["display", "ethernet", "can", "audio"],
        "printer": ["motor", "uart", "usb"],
        "vacuum": ["motor", "ble", "adc"],
    }

    # eos board definitions keyed by MCU family prefix
    EOS_BOARD_MAP: Dict[str, str] = {
        "stm32f4": "stm32f4.yaml",
        "stm32h7": "stm32h743.yaml",
        "stm32h743": "stm32h743.yaml",
        "stm32mp1": "stm32mp1.yaml",
        "nrf52": "nrf52840.yaml",
        "nrf52840": "nrf52840.yaml",
        "rpi": "raspberrypi4.yaml",
        "rpi4": "raspberrypi4.yaml",
        "bcm2711": "raspberrypi4.yaml",
        "esp32": "esp32.yaml",
        "riscv": "generic-riscv64.yaml",
        "sifive": "sifive_u.yaml",
        "fu740": "sifive_u.yaml",
        "x86": "generic-x86_64.yaml",
        "x86_64": "generic-x86_64.yaml",
        "imx8": "imx8m.yaml",
        "am64": "am64x.yaml",
        "samd51": "samd51.yaml",
        # Classic architectures
        "sa1": "generic-strongarm.yaml",
        "sa110": "generic-strongarm.yaml",
        "pxa": "generic-xscale.yaml",
        "ixp": "generic-xscale.yaml",
        "fr": "generic-frv.yaml",
        "mb93": "generic-frv.yaml",
        "sh7": "generic-sh.yaml",
        "sh2": "generic-sh.yaml",
        "h8": "generic-h8300.yaml",
        "i386": "generic-x86.yaml",
        "i486": "generic-x86.yaml",
        "pentium": "generic-x86.yaml",
        "atom": "generic-x86.yaml",
        "quark": "generic-x86.yaml",
        "mips": "generic-mips.yaml",
        "pic32": "generic-mips.yaml",
        "jz": "generic-mips.yaml",
        "ar9": "generic-mips.yaml",
        "mn10": "generic-mn103.yaml",
        "am3": "generic-mn103.yaml",
        "mpc": "generic-powerpc.yaml",
        "p10": "generic-powerpc.yaml",
        "p20": "generic-powerpc.yaml",
        "t10": "generic-powerpc.yaml",
        "ppc": "generic-powerpc.yaml",
        "mc68": "generic-m68k.yaml",
        "mcf5": "generic-m68k.yaml",
        "v850": "generic-v850.yaml",
        "rh850": "generic-v850.yaml",
        "upd70": "generic-v850.yaml",
        "sparc": "generic-sparc.yaml",
        "leon": "generic-sparc.yaml",
        "ut699": "generic-sparc.yaml",
        "gr712": "generic-sparc.yaml",
        "erc32": "generic-sparc.yaml",
    }

    # Map architecture → eos toolchain YAML filename
    # NOTE: Longer prefixes must come before shorter ones because
    # resolve_manifest uses str.startswith() to match.
    ARCH_TO_TOOLCHAIN: Dict[str, str] = {
        "arm-cortex-r": "arm-none-eabi-r5.yaml",
        "arm64": "aarch64-linux-gnu.yaml",
        "arm": "arm-none-eabi.yaml",
        "riscv32": "riscv64-linux-gnu.yaml",
        "riscv64": "riscv64-linux-gnu.yaml",
        "x86": "x86_64-linux-gnu.yaml",
        "x86_64": "x86_64-linux-gnu.yaml",
        "mips": "mips-linux-gnu.yaml",
        "mips64": "mips64-linux-gnu.yaml",
        "powerpc": "powerpc-linux-gnu.yaml",
        "m68k": "m68k-elf.yaml",
        "sh": "sh-elf.yaml",
        "h8300": "h8300-elf.yaml",
        "v850": "v850-elf.yaml",
        "sparc": "sparc-elf.yaml",
        "sparc64": "sparc64-linux-gnu.yaml",
        "frv": "frv-elf.yaml",
        "mn103": "mn10300-elf.yaml",
        "xtensa": "xtensa-esp32-elf.yaml",
    }

    # Map product/peripheral combos → relevant eos examples
    EXAMPLE_MAP: Dict[str, List[str]] = {
        "motor": ["motor-controller"],
        "industrial": ["industrial-gateway"],
        "gateway": ["industrial-gateway"],
        "linux": ["demo-linux"],
    }

    def __init__(
        self,
        eos_repo: Optional[str] = None,
        eboot_repo: Optional[str] = None,
        eos_url: Optional[str] = None,
        eboot_url: Optional[str] = None,
    ):
        self.eos_repo = Path(eos_repo) if eos_repo else None
        self.eboot_repo = Path(eboot_repo) if eboot_repo else None
        self.eos_url = eos_url or DEFAULT_EOS_REPO_URL
        self.eboot_url = eboot_url or DEFAULT_EBOOT_REPO_URL
        self._temp_dirs: List[Path] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ensure_repos(
        self,
        need_eos: bool = True,
        need_eboot: bool = True,
        clone_dir: Optional[str] = None,
        shallow: bool = True,
    ) -> None:
        """Clone eos/eboot from GitHub if local repo paths were not provided.

        Args:
            need_eos: Whether the eos repo is needed.
            need_eboot: Whether the eboot repo is needed.
            clone_dir: Directory to clone into. Uses a temp dir if *None*.
            shallow: Use ``--depth 1`` for faster clones (default *True*).
        """
        if need_eos and self.eos_repo is None:
            self.eos_repo = self._clone_repo(
                self.eos_url, "eos", clone_dir, shallow
            )
        if need_eboot and self.eboot_repo is None:
            self.eboot_repo = self._clone_repo(
                self.eboot_url, "eboot", clone_dir, shallow
            )

    def cleanup(self) -> None:
        """Remove any temporary directories created by :meth:`ensure_repos`."""
        for d in self._temp_dirs:
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
        self._temp_dirs.clear()

    def resolve_manifest(self, profile: HardwareProfile) -> ProjectManifest:
        """Determine which eos/eboot modules are needed for *profile*."""
        manifest = ProjectManifest()
        enables = profile.get_eos_enables()
        manifest.eos_enables = enables

        # --- eos directories ---
        included_dirs: Set[str] = set(self.EOS_CORE_DIRS)

        # Platform-specific services
        platform = self._resolve_platform(profile)
        manifest.eos_platform = platform
        if platform == "linux":
            included_dirs.add("services/linux")
        else:
            included_dirs.add("services/rtos")

        # Enable-driven services
        for flag, dirs in self.EOS_SERVICE_MAP.items():
            if enables.get(flag):
                included_dirs.update(dirs)

        # Power management — include if any power-related peripherals
        power_flags = {"EOS_ENABLE_ADC", "EOS_ENABLE_DAC", "EOS_ENABLE_PWM"}
        if power_flags & set(enables.keys()):
            included_dirs.add("power")

        # Networking
        net_flags = {"EOS_ENABLE_ETHERNET", "EOS_ENABLE_WIFI", "EOS_ENABLE_BLE"}
        if net_flags & set(enables.keys()):
            included_dirs.add("net")

        # Filesystem — include if flash storage is significant
        if profile.flash_size > 256 * 1024:
            included_dirs.add("services/filesystem")

        # Sensor service — include if any sensor-type peripherals
        sensor_flags = {"EOS_ENABLE_ADC", "EOS_ENABLE_IMU", "EOS_ENABLE_CAMERA"}
        if sensor_flags & set(enables.keys()):
            included_dirs.add("services/sensor")

        manifest.eos_dirs = sorted(included_dirs)

        # --- eos product profile ---
        manifest.eos_product = self._resolve_product(profile)

        # --- eos board definition ---
        board_file = self._resolve_eos_board(profile)
        if board_file:
            manifest.eos_files.append(f"boards/{board_file}")

        # --- eboot board ---
        eboot_board = self._resolve_eboot_board(profile)
        manifest.eboot_board = eboot_board

        # --- eboot directories (always included) ---
        manifest.eboot_dirs = ["hal", "include", "stage0", "stage1"]
        if eboot_board:
            manifest.eboot_dirs.append(f"boards/{eboot_board}")

        # --- eboot core files ---
        eboot_files: List[str] = list(self.EBOOT_CORE_ALWAYS)

        arch = (profile.arch or "").lower()
        mcu = (profile.mcu or "").lower()
        needs_rtos = manifest.eos_platform == "rtos"
        needs_uart = enables.get("EOS_ENABLE_UART", False)
        needs_dram = arch in self.DRAM_ARCHS
        needs_pci = arch in self.PCI_ARCHS
        needs_bmc = arch in self.BMC_ARCHS
        needs_ecc = needs_dram
        needs_multicore = mcu in self.MULTICORE_MCUS

        cond_checks = {
            "needs_dram": needs_dram,
            "needs_pci": needs_pci,
            "needs_bmc": needs_bmc,
            "needs_ecc": needs_ecc,
            "needs_multicore": needs_multicore,
            "needs_rtos": needs_rtos,
            "needs_uart": needs_uart,
        }

        for core_file, requirements in self.EBOOT_CORE_CONDITIONAL.items():
            for req_key, _req_val in requirements.items():
                if cond_checks.get(req_key, False):
                    eboot_files.append(core_file)
                    break

        manifest.eboot_files = sorted(set(eboot_files))

        # --- eos toolchain ---
        # Use core to distinguish Cortex-R from generic ARM
        arch = (profile.arch or "").lower()
        core = (profile.core or "").lower()
        tc_arch = arch
        if arch == "arm" and "cortex-r" in core:
            tc_arch = "arm-cortex-r"
        for arch_prefix, tc_file in self.ARCH_TO_TOOLCHAIN.items():
            if tc_arch.startswith(arch_prefix):
                manifest.eos_toolchain = tc_file
                break

        # --- eos examples ---
        examples: List[str] = []
        if manifest.eos_platform == "linux":
            examples.append("demo-linux")
        peripheral_types = {
            p.peripheral_type.lower() for p in profile.peripherals
        }
        if "motor" in peripheral_types:
            examples.append("motor-controller")
        if any(t in peripheral_types for t in ("can", "ethernet")):
            examples.append("industrial-gateway")
        manifest.eos_examples = sorted(set(examples))

        # --- eos extras (always include schemas, docs, toolchains dir) ---
        manifest.eos_extras = ["schemas", "docs"]

        # --- eboot extras (always include configs, tools, scripts, docs) ---
        manifest.eboot_extras = ["configs", "tools", "scripts", "docs"]

        return manifest

    def generate(
        self,
        profile: HardwareProfile,
        output: str,
        mode: str = "copy",
        branch: Optional[str] = None,
    ) -> Dict[str, Path]:
        """Generate a stripped eos/eboot project.

        Args:
            profile: Hardware profile from ``ebuild analyze``.
            output: Output directory (copy mode) or ignored (branch mode).
            mode: ``"copy"`` for standalone dir, ``"branch"`` for git branch.
            branch: Git branch name (branch mode only).

        Returns:
            Dict mapping output name to path.
        """
        manifest = self.resolve_manifest(profile)
        outputs: Dict[str, Path] = {}

        if mode == "branch":
            if self.eos_repo:
                outputs["eos_branch"] = self._create_branch(
                    self.eos_repo, manifest, branch or "customer/generated", "eos"
                )
            if self.eboot_repo:
                outputs["eboot_branch"] = self._create_branch(
                    self.eboot_repo, manifest, branch or "customer/generated", "eboot"
                )
        else:
            output_path = Path(output)
            if self.eos_repo:
                eos_out = output_path / "eos"
                self._copy_eos(manifest, eos_out)
                cmake = self._generate_eos_cmake(manifest, profile)
                (eos_out / "CMakeLists.txt").write_text(cmake)
                config_h = self._generate_eos_config_h(manifest, profile)
                config_dir = eos_out / "include" / "eos"
                config_dir.mkdir(parents=True, exist_ok=True)
                (config_dir / "eos_config.h").write_text(config_h)
                readme = self._generate_eos_readme(manifest, profile)
                (eos_out / "README.md").write_text(readme)
                outputs["eos"] = eos_out

            if self.eboot_repo:
                eboot_out = output_path / "eboot"
                self._copy_eboot(manifest, eboot_out)
                cmake = self._generate_eboot_cmake(manifest, profile)
                (eboot_out / "CMakeLists.txt").write_text(cmake)
                readme = self._generate_eboot_readme(manifest, profile)
                (eboot_out / "README.md").write_text(readme)
                outputs["eboot"] = eboot_out

            # Top-level project README
            output_path.mkdir(parents=True, exist_ok=True)
            top_readme = self._generate_project_readme(manifest, profile, output)
            (output_path / "README.md").write_text(top_readme)
            outputs["readme"] = output_path / "README.md"

        return outputs

    # ------------------------------------------------------------------
    # Resolution helpers
    # ------------------------------------------------------------------

    def _resolve_platform(self, profile: HardwareProfile) -> str:
        """Determine if this is a linux or rtos target."""
        arch = (profile.arch or "").lower()
        # Only full application-class architectures default to linux
        if arch in ("arm64", "x86_64", "riscv64", "mips64", "sparc64", "powerpc"):
            return "linux"
        return "rtos"

    def _resolve_eboot_board(self, profile: HardwareProfile) -> str:
        """Map MCU → eboot board directory name."""
        mcu = (profile.mcu or "").lower()
        for prefix, board in self.MCU_TO_EBOOT_BOARD.items():
            if mcu.startswith(prefix):
                return board
        return ""

    def _resolve_eos_board(self, profile: HardwareProfile) -> str:
        """Map MCU family → eos board YAML filename."""
        mcu = (profile.mcu or "").lower()
        for prefix, filename in self.EOS_BOARD_MAP.items():
            if mcu.startswith(prefix):
                return filename
        return ""

    def _resolve_product(self, profile: HardwareProfile) -> str:
        """Pick the best-matching product profile based on peripheral set."""
        peripheral_types = {
            p.peripheral_type.lower() for p in profile.peripherals
        }
        best_product = "iot"
        best_score = 0
        for product, required in self.PRODUCT_MAP.items():
            score = sum(1 for r in required if r in peripheral_types)
            if score > best_score:
                best_score = score
                best_product = product
        return best_product

    # ------------------------------------------------------------------
    # Git clone helpers
    # ------------------------------------------------------------------

    def _clone_repo(
        self,
        url: str,
        name: str,
        clone_dir: Optional[str],
        shallow: bool,
    ) -> Path:
        """Clone a git repo and return the local path."""
        if clone_dir:
            base = Path(clone_dir)
            base.mkdir(parents=True, exist_ok=True)
        else:
            base = Path(tempfile.mkdtemp(prefix="ebuild_"))
            self._temp_dirs.append(base)

        dest = base / name
        if dest.exists():
            return dest

        cmd = ["git", "clone"]
        if shallow:
            cmd.extend(["--depth", "1"])
        cmd.extend([url, str(dest)])

        result = subprocess.run(
            cmd, capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to clone {url}: {result.stderr.strip()}"
            )
        return dest

    # ------------------------------------------------------------------
    # Copy mode
    # ------------------------------------------------------------------

    def _copy_eos(self, manifest: ProjectManifest, dest: Path) -> None:
        """Copy required eos files to *dest*."""
        dest.mkdir(parents=True, exist_ok=True)
        assert self.eos_repo is not None

        for d in manifest.eos_dirs:
            src = self.eos_repo / d
            if src.exists():
                dst = dest / d
                shutil.copytree(src, dst, dirs_exist_ok=True)

        for f in manifest.eos_files:
            src = self.eos_repo / f
            if src.exists():
                dst = dest / f
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        # Copy the matching product profile
        if manifest.eos_product:
            src = self.eos_repo / "products" / f"{manifest.eos_product}.h"
            if src.exists():
                dst = dest / "products" / f"{manifest.eos_product}.h"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        # Copy matching toolchain
        if manifest.eos_toolchain:
            src = self.eos_repo / "toolchains" / manifest.eos_toolchain
            if src.exists():
                dst = dest / "toolchains" / manifest.eos_toolchain
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            # Also copy toolchain source + header (always useful)
            for tc_file in ["src/toolchain.c", "include/eos/toolchain.h",
                            "CMakeLists.txt"]:
                src = self.eos_repo / "toolchains" / tc_file
                if src.exists():
                    dst = dest / "toolchains" / tc_file
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)

        # Copy matching examples
        for example in manifest.eos_examples:
            src = self.eos_repo / "examples" / example
            if src.exists():
                dst = dest / "examples" / example
                shutil.copytree(src, dst, dirs_exist_ok=True)

        # Copy extras (schemas, docs)
        for extra in manifest.eos_extras:
            src = self.eos_repo / extra
            if src.exists():
                dst = dest / extra
                shutil.copytree(src, dst, dirs_exist_ok=True)

    def _copy_eboot(self, manifest: ProjectManifest, dest: Path) -> None:
        """Copy required eboot files to *dest*."""
        dest.mkdir(parents=True, exist_ok=True)
        assert self.eboot_repo is not None

        for d in manifest.eboot_dirs:
            src = self.eboot_repo / d
            if src.exists():
                dst = dest / d
                shutil.copytree(src, dst, dirs_exist_ok=True)

        for f in manifest.eboot_files:
            src = self.eboot_repo / f
            if src.exists():
                dst = dest / f
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        # Copy extras (configs, tools, scripts, docs)
        for extra in manifest.eboot_extras:
            src = self.eboot_repo / extra
            if src.exists():
                dst = dest / extra
                shutil.copytree(src, dst, dirs_exist_ok=True)

    # ------------------------------------------------------------------
    # Branch mode
    # ------------------------------------------------------------------

    def _create_branch(
        self,
        repo: Path,
        manifest: ProjectManifest,
        branch_name: str,
        repo_type: str,
    ) -> Path:
        """Create a git branch in *repo* containing only required files."""
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=str(repo),
            check=True,
            capture_output=True,
        )

        if repo_type == "eos":
            keep_dirs = set(manifest.eos_dirs)
            keep_files = set(manifest.eos_files)
            if manifest.eos_product:
                keep_files.add(f"products/{manifest.eos_product}.h")
        else:
            keep_dirs = set(manifest.eboot_dirs)
            keep_files = set(manifest.eboot_files)

        # Always keep root-level build files
        keep_files.update(["CMakeLists.txt", "README.md"])

        # Walk repo and remove files not in the keep set
        for item in sorted(repo.rglob("*")):
            if item.name == ".git" or ".git" in item.parts:
                continue

            rel = item.relative_to(repo).as_posix()

            if item.is_file():
                if rel in keep_files:
                    continue
                if any(rel.startswith(d + "/") or rel == d for d in keep_dirs):
                    continue
                item.unlink()

        # Remove empty directories
        for item in sorted(repo.rglob("*"), reverse=True):
            if item.name == ".git" or ".git" in item.parts:
                continue
            if item.is_dir() and not any(item.iterdir()):
                item.rmdir()

        # Stage + commit
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(repo), check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m",
             f"ebuild: generate stripped {repo_type} for {branch_name}"],
            cwd=str(repo), check=True, capture_output=True,
        )

        return repo

    # ------------------------------------------------------------------
    # CMakeLists.txt generation
    # ------------------------------------------------------------------

    def _generate_eos_cmake(
        self, manifest: ProjectManifest, profile: HardwareProfile
    ) -> str:
        """Generate a tailored CMakeLists.txt for the stripped eos tree."""
        mcu = profile.mcu or "custom"
        enables = manifest.eos_enables
        product = manifest.eos_product
        platform = manifest.eos_platform

        # Determine HAL sources
        hal_sources = ["hal/src/hal_common.c", "hal/src/hal_extended_stubs.c"]
        if platform == "linux":
            hal_sources.append("hal/src/hal_linux.c")
        else:
            hal_sources.append("hal/src/hal_rtos.c")
        hal_src_block = "\n    ".join(hal_sources)

        # Kernel sources
        kernel_sources = [
            "kernel/src/task.c",
            "kernel/src/sync.c",
            "kernel/src/ipc.c",
        ]
        if "kernel" in manifest.eos_dirs:
            kernel_sources.append("kernel/src/multicore.c")
        kernel_src_block = "\n    ".join(kernel_sources)

        # Enable defines
        enable_lines = []
        for flag in sorted(enables.keys()):
            enable_lines.append(f"add_compile_definitions({flag}=1)")
        enable_block = "\n".join(enable_lines)

        # Service subdirectories
        service_subdirs = []
        service_dir_names = [
            d for d in manifest.eos_dirs if d.startswith("services/")
        ]
        for sd in sorted(service_dir_names):
            service_subdirs.append(f"add_subdirectory({sd})")
        service_block = "\n".join(service_subdirs)

        # Optional top-level modules
        optional_blocks = []
        if "net" in manifest.eos_dirs:
            optional_blocks.append(_EOS_CMAKE_NET)
        if "power" in manifest.eos_dirs:
            optional_blocks.append(_EOS_CMAKE_POWER)
        optional_block = "\n".join(optional_blocks)

        product_line = ""
        if product:
            product_upper = product.upper()
            product_line = f'add_compile_definitions(EOS_PRODUCT_{product_upper})'

        return f"""\
cmake_minimum_required(VERSION 3.16)
project({mcu.lower()}_eos
    VERSION 0.1.0
    DESCRIPTION "Stripped EoS build for {mcu}"
    LANGUAGES C
)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

if(MSVC)
    add_compile_definitions(_CRT_SECURE_NO_WARNINGS)
    add_compile_options(/W3)
elseif(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-Wall -Wextra)
endif()

set(EOS_PLATFORM "{platform}" CACHE STRING "Target platform")
{product_line}

include_directories(
    ${{CMAKE_CURRENT_SOURCE_DIR}}/include
    ${{CMAKE_CURRENT_SOURCE_DIR}}
)

# Enable flags for this hardware target
{enable_block}

# ==== HAL ====
add_library(eos_hal STATIC
    {hal_src_block}
)
target_include_directories(eos_hal PUBLIC
    ${{CMAKE_CURRENT_SOURCE_DIR}}/hal/include
    ${{CMAKE_CURRENT_SOURCE_DIR}}/include
)

# ==== Kernel ====
add_library(eos_kernel STATIC
    {kernel_src_block}
)
target_include_directories(eos_kernel PUBLIC
    ${{CMAKE_CURRENT_SOURCE_DIR}}/kernel/include
    ${{CMAKE_CURRENT_SOURCE_DIR}}/include
)
target_link_libraries(eos_kernel PUBLIC eos_hal)

# ==== Driver Framework ====
add_library(eos_drivers STATIC
    drivers/src/driver_framework.c
)
target_include_directories(eos_drivers PUBLIC
    ${{CMAKE_CURRENT_SOURCE_DIR}}/drivers/include
)
target_link_libraries(eos_drivers PUBLIC eos_hal)

# ==== Core ====
add_subdirectory(core)

# ==== Services ====
{service_block}

{optional_block}
"""

    def _generate_eboot_cmake(
        self, manifest: ProjectManifest, profile: HardwareProfile
    ) -> str:
        """Generate a tailored CMakeLists.txt for the stripped eboot tree."""
        board = manifest.eboot_board or "none"
        mcu = profile.mcu or "custom"

        core_sources = "\n    ".join(manifest.eboot_files)

        board_block = ""
        if board != "none" and board:
            board_block = f"""\
# ==== Board Port: {board} ====
add_library(board_{board} STATIC
    boards/{board}/board_{board}.c
)
target_include_directories(board_{board} PUBLIC
    ${{EBLDR_INCLUDE_DIR}}
    ${{CMAKE_CURRENT_SOURCE_DIR}}/boards/{board}
)
target_link_libraries(board_{board} PUBLIC eboot_hal)
"""

        return f"""\
cmake_minimum_required(VERSION 3.15)
project({mcu.lower()}_eboot
    VERSION 0.1.0
    LANGUAGES C
    DESCRIPTION "Stripped eboot for {mcu}"
)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

set(EBLDR_BOARD "{board}" CACHE STRING "Target board")
set(EBLDR_INCLUDE_DIR ${{CMAKE_CURRENT_SOURCE_DIR}}/include)

if(CMAKE_CROSSCOMPILING)
    add_compile_options(-Wall -Wextra -Os -ffunction-sections -fdata-sections -fno-common)
    add_link_options(-Wl,--gc-sections)
elseif(MSVC)
    add_compile_options(/W3)
elseif(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-Wall -Wextra)
endif()

# ==== HAL ====
add_library(eboot_hal STATIC
    hal/hal_core.c
    hal/board_registry.c
)
target_include_directories(eboot_hal PUBLIC ${{EBLDR_INCLUDE_DIR}})

# ==== Core ====
add_library(eboot_core STATIC
    {core_sources}
)
target_include_directories(eboot_core PUBLIC ${{EBLDR_INCLUDE_DIR}})
target_link_libraries(eboot_core PUBLIC eboot_hal)

# ==== Stage-1 ====
add_library(eboot_stage1 STATIC
    stage1/main.c
    stage1/boot_scan.c
    stage1/boot_select.c
    stage1/boot_log.c
    stage1/jump_app.c
)
target_include_directories(eboot_stage1 PUBLIC ${{EBLDR_INCLUDE_DIR}})
target_link_libraries(eboot_stage1 PUBLIC eboot_core)

{board_block}
"""

    def _generate_eos_config_h(
        self, manifest: ProjectManifest, profile: HardwareProfile
    ) -> str:
        """Generate a tailored eos_config.h with only needed EOS_ENABLE flags."""
        lines = [
            f"/* Auto-generated EoS config for {profile.mcu or 'custom'} */",
            "#ifndef EOS_CONFIG_H",
            "#define EOS_CONFIG_H",
            "",
            f'#define EOS_PRODUCT_NAME    "{profile.mcu.lower() if profile.mcu else "custom"}"',
            f'#define EOS_ARCH            "{profile.arch or "unknown"}"',
            f'#define EOS_CORE            "{profile.core or "unknown"}"',
            f"#define EOS_CLOCK_HZ         {profile.clock_hz}",
            f"#define EOS_FLASH_SIZE       {profile.flash_size}",
            f"#define EOS_RAM_SIZE         {profile.ram_size}",
            "",
        ]

        for flag in sorted(manifest.eos_enables.keys()):
            lines.append(f"#define {flag:<28s} 1")

        # Explicitly disable flags not in the enable set
        all_possible = {
            "EOS_ENABLE_UART", "EOS_ENABLE_SPI", "EOS_ENABLE_I2C",
            "EOS_ENABLE_GPIO", "EOS_ENABLE_CAN", "EOS_ENABLE_USB",
            "EOS_ENABLE_ADC", "EOS_ENABLE_DAC", "EOS_ENABLE_PWM",
            "EOS_ENABLE_TIMER", "EOS_ENABLE_ETHERNET", "EOS_ENABLE_WIFI",
            "EOS_ENABLE_BLE", "EOS_ENABLE_CAMERA", "EOS_ENABLE_DISPLAY",
            "EOS_ENABLE_MOTOR", "EOS_ENABLE_WDT", "EOS_ENABLE_RTC",
            "EOS_ENABLE_DMA", "EOS_ENABLE_FLASH", "EOS_ENABLE_NFC",
            "EOS_ENABLE_GNSS", "EOS_ENABLE_IMU", "EOS_ENABLE_AUDIO",
        }
        disabled = sorted(all_possible - set(manifest.eos_enables.keys()))
        if disabled:
            lines.append("")
            for flag in disabled:
                lines.append(f"#define {flag:<28s} 0")

        lines.extend(["", "#endif /* EOS_CONFIG_H */", ""])
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # README generation
    # ------------------------------------------------------------------

    def _generate_project_readme(
        self, manifest: ProjectManifest, profile: HardwareProfile, output: str
    ) -> str:
        """Generate a top-level README.md for the stripped project."""
        mcu = profile.mcu or "Custom"
        arch = profile.arch or "unknown"
        core = profile.core or "unknown"
        product = manifest.eos_product or "generic"
        platform = manifest.eos_platform
        peripherals = ", ".join(
            p.peripheral_type.upper() for p in profile.peripherals
        ) or "none detected"

        enables_list = "\n".join(
            f"  - `{flag}`" for flag in sorted(manifest.eos_enables.keys())
        ) or "  - (none)"

        eos_dirs_list = "\n".join(
            f"  - `{d}/`" for d in manifest.eos_dirs
        )
        eboot_dirs_list = "\n".join(
            f"  - `{d}/`" for d in manifest.eboot_dirs
        )
        eboot_core_list = "\n".join(
            f"  - `{f}`" for f in manifest.eboot_files
        )

        # Extras
        toolchain_line = (
            f"  - `toolchains/{manifest.eos_toolchain}` — cross-compilation config"
            if manifest.eos_toolchain else "  - (no toolchain — native build)"
        )
        examples_list = "\n".join(
            f"  - `examples/{e}/`" for e in manifest.eos_examples
        ) or "  - (no examples matched)"
        eos_extras_list = "\n".join(
            f"  - `{e}/`" for e in manifest.eos_extras
        )
        eboot_extras_list = "\n".join(
            f"  - `{e}/`" for e in manifest.eboot_extras
        )

        flash_str = _format_size(profile.flash_size)
        ram_str = _format_size(profile.ram_size)

        return f"""\
# {mcu} Firmware Project

> Auto-generated by `ebuild generate-project` — stripped from the full eos/eboot repositories
> to include only the modules required for this hardware target.

## Hardware Target

| Property | Value |
|----------|-------|
| MCU | {mcu} |
| Architecture | {arch} |
| Core | {core} |
| Vendor | {profile.vendor or "—"} |
| Flash | {flash_str} |
| RAM | {ram_str} |
| Clock | {profile.clock_hz // 1_000_000 if profile.clock_hz else 0} MHz |
| Peripherals | {peripherals} |
| Product Profile | {product} |
| Platform | {platform} |

## EOS_ENABLE Flags

{enables_list}

## Project Structure

```
{output}/
├── README.md              ← this file
├── eos/                   ← stripped EoS (embedded OS)
│   ├── CMakeLists.txt     ← standalone build file
│   ├── README.md          ← eos-specific docs
│   ├── hal/               ← hardware abstraction
│   ├── kernel/            ← RTOS kernel
│   ├── services/          ← enabled service modules
│   ├── toolchains/        ← cross-compilation configs
│   ├── schemas/           ← hardware/board schemas
│   ├── examples/          ← reference examples
│   ├── docs/              ← architecture & getting started
│   └── ...
└── eboot/                 ← stripped eboot (bootloader)
    ├── CMakeLists.txt     ← standalone build file
    ├── README.md          ← eboot-specific docs
    ├── stage0/            ← first-stage boot
    ├── stage1/            ← second-stage boot
    ├── configs/           ← boot config schemas
    ├── tools/             ← image packing & signing tools
    ├── scripts/           ← config generation scripts
    ├── docs/              ← bootloader documentation
    └── ...
```

### eos modules included

{eos_dirs_list}

### eos toolchain

{toolchain_line}

### eos examples

{examples_list}

### eos extras (schemas, docs)

{eos_extras_list}

### eboot modules included

Directories:
{eboot_dirs_list}

Core files:
{eboot_core_list}

### eboot extras (configs, tools, scripts, docs)

{eboot_extras_list}

## Building

### Prerequisites

- CMake ≥ 3.16
- ARM cross-compiler toolchain (e.g. `arm-none-eabi-gcc`) for RTOS targets
- Native GCC/Clang for host builds

### Build eos

```bash
cd eos
cmake -B build -DEOS_PLATFORM={platform}
cmake --build build
```

### Build eboot

```bash
cd eboot
cmake -B build -DEBLDR_BOARD={manifest.eboot_board or "none"}
cmake --build build
```

### Cross-compile (example: ARM)

```bash
# eos
cd eos
cmake -B build -DCMAKE_TOOLCHAIN_FILE=<path-to-arm-toolchain.cmake> \\
    -DEOS_PLATFORM=rtos
cmake --build build

# eboot
cd ../eboot
cmake -B build -DEBLDR_BOARD={manifest.eboot_board or "none"} \\
    -DCMAKE_TOOLCHAIN_FILE=<path-to-arm-toolchain.cmake>
cmake --build build
```

## Regenerating

To regenerate this project with different hardware or updated upstream sources:

```bash
ebuild generate-project --text "<hardware description>" --output {output}
```

Or from a previously generated `board.yaml`:

```bash
ebuild generate-project --config _generated/board.yaml --output {output}
```

## Upstream Tracking

This project was stripped from the full eos and eboot repositories.
To pull in upstream bug fixes or security patches, re-run `ebuild generate-project`
against the latest upstream repos.

---
*Generated by ebuild EoS AI Project Generator*
"""

    def _generate_eos_readme(
        self, manifest: ProjectManifest, profile: HardwareProfile
    ) -> str:
        """Generate an eos-specific README.md."""
        mcu = profile.mcu or "Custom"
        platform = manifest.eos_platform
        product = manifest.eos_product or "generic"

        enables_table = "\n".join(
            f"| `{flag}` | ✅ Enabled |"
            for flag in sorted(manifest.eos_enables.keys())
        ) or "| (none) | — |"

        dirs_detail = []
        dir_descriptions = {
            "hal": "Hardware Abstraction Layer — platform-independent HAL API",
            "kernel": "Lightweight RTOS kernel — tasks, sync primitives, IPC",
            "core": "OS core — config, logging, scheduler, layers",
            "drivers": "Driver framework — unified device driver model",
            "include": "Global headers — eos_config.h and common types",
            "services/crypto": "Cryptography — SHA-256, CRC, AES (required for OTA)",
            "services/security": "Security — keystore, ACL, secure boot verification",
            "services/os": "OS services — watchdog, storage, system management",
            "services/ota": "Over-the-air updates — firmware download and apply",
            "services/motor": "Motor control — stepper, DC, servo motor drivers",
            "services/sensor": "Sensor framework — calibration, filtering, multi-sensor",
            "services/filesystem": "Filesystem — flash-based file storage",
            "services/rtos": "RTOS security — task isolation, MPU configuration",
            "services/linux": "Linux security — namespace, seccomp, capability management",
            "services/datacenter": "Datacenter services — BMC, rack management",
            "net": "Networking — TCP/IP, BLE, WiFi abstraction",
            "power": "Power management — sleep modes, voltage regulation",
        }
        for d in manifest.eos_dirs:
            desc = dir_descriptions.get(d, "")
            dirs_detail.append(f"| `{d}/` | {desc} |")
        dirs_table = "\n".join(dirs_detail)

        return f"""\
# EoS — Stripped Build for {mcu}

This is a stripped-down version of the EoS embedded operating system,
tailored for the **{mcu}** ({profile.arch}/{profile.core}) target.

Only the modules required for this hardware are included.

## Configuration

| Setting | Value |
|---------|-------|
| Platform | {platform} |
| Product Profile | {product} |
| MCU | {mcu} |
| Architecture | {profile.arch or "—"} |

## Enabled Features

| Flag | Status |
|------|--------|
{enables_table}

## Included Modules

| Directory | Description |
|-----------|-------------|
{dirs_table}

## Building

```bash
# Host build (Linux/macOS/Windows)
cmake -B build -DEOS_PLATFORM={platform}
cmake --build build

# Cross-compile for ARM target
cmake -B build \\
    -DCMAKE_TOOLCHAIN_FILE=<path-to-arm-toolchain.cmake> \\
    -DEOS_PLATFORM=rtos
cmake --build build
```

## Key Files

- `CMakeLists.txt` — standalone build (does not depend on full eos repo)
- `include/eos/eos_config.h` — all EOS_ENABLE flags for this target
- `products/{product}.h` — product profile header

## Architecture

```
eos/
├── CMakeLists.txt
├── include/eos/eos_config.h
├── hal/           → HAL (platform layer)
├── kernel/        → RTOS kernel
├── core/          → OS core services
├── drivers/       → Device driver framework
├── services/      → Enabled service modules
│   ├── crypto/    → Always included (OTA)
│   ├── security/  → Always included
│   ├── os/        → Always included
│   ├── ota/       → Always included
│   └── ...        → Hardware-specific services
├── products/      → Product profile header
├── toolchains/    → Cross-compilation config
├── schemas/       → Hardware & board schemas
├── examples/      → Reference project examples
└── docs/          → Architecture & getting started
```

---
*Auto-generated by ebuild — do not edit manually*
"""

    def _generate_eboot_readme(
        self, manifest: ProjectManifest, profile: HardwareProfile
    ) -> str:
        """Generate an eboot-specific README.md."""
        mcu = profile.mcu or "Custom"
        board = manifest.eboot_board or "none"

        core_files_table = "\n".join(
            f"| `{f}` | ✅ |" for f in manifest.eboot_files
        )

        # Determine which conditional files were excluded
        all_conditional = set(self.EBOOT_CORE_CONDITIONAL.keys())
        included_conditional = set(manifest.eboot_files) & all_conditional
        excluded_conditional = all_conditional - included_conditional
        excluded_table = "\n".join(
            f"| `{f}` | ❌ Not needed for {mcu} |"
            for f in sorted(excluded_conditional)
        ) or "| (none excluded) | — |"

        return f"""\
# eboot — Stripped Bootloader for {mcu}

This is a stripped-down version of the eboot multi-stage bootloader,
tailored for the **{mcu}** target with the **{board}** board port.

## Board Port

| Setting | Value |
|---------|-------|
| MCU | {mcu} |
| Board | {board} |
| Architecture | {profile.arch or "—"} |

## Included Core Files

| File | Status |
|------|--------|
{core_files_table}

## Excluded (not needed for this hardware)

| File | Reason |
|------|--------|
{excluded_table}

## Boot Stages

eboot uses a two-stage boot process:

1. **Stage 0** (`stage0/`) — minimal hardware init, watchdog, jump to stage 1
2. **Stage 1** (`stage1/`) — image selection, verification, jump to application

Both stages are always included regardless of target hardware.

## Building

```bash
# Host build (core libraries only — for testing)
cmake -B build
cmake --build build

# Cross-compile with board port
cmake -B build \\
    -DEBLDR_BOARD={board} \\
    -DCMAKE_TOOLCHAIN_FILE=<path-to-arm-toolchain.cmake>
cmake --build build
```

## Architecture

```
eboot/
├── CMakeLists.txt
├── include/       → Boot headers (bootctl, image, crypto, fw_update)
├── hal/           → HAL dispatch + board registry
├── core/          → Core boot logic (only files needed for {mcu})
├── stage0/        → Stage 0 — reset entry, HW init, watchdog
├── stage1/        → Stage 1 — boot scan, select, jump to app
├── boards/{board}/  → {mcu} board port
├── configs/       → Boot config schemas (flash layout, image format)
├── tools/         → Image packing, signing, UART recovery tools
├── scripts/       → Config generation scripts
└── docs/          → Architecture, security, update flow docs
```

## Included Tools

| Tool | Purpose |
|------|---------|
| `tools/imgpack.py` | Pack firmware into bootable image format |
| `tools/sign_image.py` | Sign firmware images for secure boot |
| `tools/uart_recovery.py` | Recover bricked devices via UART |
| `scripts/generate_config.py` | Generate boot config from templates |

## Documentation

| Doc | Contents |
|-----|----------|
| `docs/architecture.md` | eboot architecture and boot flow |
| `docs/installation_usage.md` | Setup and usage guide |
| `docs/memory-map.md` | Flash memory layout reference |
| `docs/security.md` | Secure boot and chain of trust |
| `docs/update-flow.md` | Firmware update process |

---
*Auto-generated by ebuild — do not edit manually*
"""


# ------------------------------------------------------------------
# Utility helpers
# ------------------------------------------------------------------


def _format_size(size_bytes: int) -> str:
    """Format a byte count as a human-readable string (e.g. 512 KB, 2 MB)."""
    if size_bytes == 0:
        return "—"
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes // (1024 * 1024)} MB"
    if size_bytes >= 1024:
        return f"{size_bytes // 1024} KB"
    return f"{size_bytes} B"


# ------------------------------------------------------------------
# CMake template fragments
# ------------------------------------------------------------------

_EOS_CMAKE_NET = """\
# ==== Networking ====
add_library(eos_net STATIC
    net/src/net.c
)
target_include_directories(eos_net PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/net/include
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)
target_link_libraries(eos_net PUBLIC eos_hal)
"""

_EOS_CMAKE_POWER = """\
# ==== Power Management ====
add_library(eos_power STATIC
    power/src/power.c
)
target_include_directories(eos_power PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/power/include
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)
target_link_libraries(eos_power PUBLIC eos_hal)
"""
