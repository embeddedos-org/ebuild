# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Integration tests for Cortex-R5 cross-compile pipeline.

Validates the complete Cortex-R5 support across all three repos:
  - eboot: toolchain, board port, linker scripts, CMake, MPU, CI
  - eos:   toolchain YAML/cmake, board YAML, toolchain.c detection, HAL comments
  - ebuild: MCU database, CLI board_map, predefined toolchains, project generator

Runs standalone: python -m pytest tests/test_cortex_r5_integration.py -v
             or: python tests/test_cortex_r5_integration.py
"""

import re
import sys
import tempfile
import shutil
from pathlib import Path

import pytest

# pythonpath in pytest.ini handles this for pytest; keep for standalone mode.
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Repo root discovery ──────────────────────────────────────────────
_THIS_DIR = Path(__file__).resolve().parent          # tests/ebuild/
_EBUILD_ROOT = _THIS_DIR.parent.parent               # repo root
_EOS_ROOT = _EBUILD_ROOT.parent / "eos"              # sibling repo
_EBOOT_ROOT = _EBUILD_ROOT.parent / "eboot"          # sibling repo

_HAS_EBOOT = _EBOOT_ROOT.is_dir()
_HAS_EOS = _EOS_ROOT.is_dir()

_skip_no_eboot = pytest.mark.skipif(not _HAS_EBOOT, reason="eboot sibling repo not found")
_skip_no_eos = pytest.mark.skipif(not _HAS_EOS, reason="eos sibling repo not found")
_skip_no_sibling = pytest.mark.skipif(
    not (_HAS_EBOOT and _HAS_EOS), reason="eboot and/or eos sibling repo not found"
)


# =====================================================================
# Phase 1 — eboot: Cortex-R5 Board Port + Toolchain + MPU + CI
# =====================================================================

@_skip_no_eboot
@pytest.mark.eboot
class TestEbootToolchain:
    """1.1 — eboot/toolchains/arm-none-eabi-r5.cmake"""

    TOOLCHAIN = _EBOOT_ROOT / "toolchains" / "arm-none-eabi-r5.cmake"

    def test_toolchain_file_exists(self):
        assert self.TOOLCHAIN.exists(), "arm-none-eabi-r5.cmake missing"

    def test_system_name_generic(self):
        content = self.TOOLCHAIN.read_text()
        assert "set(CMAKE_SYSTEM_NAME Generic)" in content

    def test_system_processor_arm(self):
        content = self.TOOLCHAIN.read_text()
        assert "set(CMAKE_SYSTEM_PROCESSOR arm)" in content

    def test_cortex_r5_cpu_flag(self):
        content = self.TOOLCHAIN.read_text()
        assert "-mcpu=cortex-r5" in content

    def test_hard_float(self):
        content = self.TOOLCHAIN.read_text()
        assert "-mfloat-abi=hard" in content
        assert "-mfpu=vfpv3-d16" in content

    def test_no_thumb_flag(self):
        """Cortex-R runs in ARM mode — C_FLAGS_INIT must NOT have -mthumb."""
        content = self.TOOLCHAIN.read_text()
        # Extract the CMAKE_C_FLAGS_INIT line (comments may mention -mthumb)
        flags_match = re.search(r'CMAKE_C_FLAGS_INIT\s+"([^"]+)"', content)
        assert flags_match is not None
        assert "-mthumb" not in flags_match.group(1)

    def test_nosys_specs(self):
        content = self.TOOLCHAIN.read_text()
        assert "--specs=nosys.specs" in content

    def test_static_library_try_compile(self):
        content = self.TOOLCHAIN.read_text()
        assert "set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)" in content

    def test_find_root_path_modes(self):
        content = self.TOOLCHAIN.read_text()
        assert "CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER" in content
        assert "CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY" in content
        assert "CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY" in content

    def test_compiler_binaries(self):
        content = self.TOOLCHAIN.read_text()
        assert "arm-none-eabi-gcc" in content
        assert "arm-none-eabi-g++" in content
        assert "arm-none-eabi-objcopy" in content
        assert "arm-none-eabi-ar" in content


@_skip_no_eboot
@pytest.mark.eboot
class TestEbootBoardHeader:
    """1.2 — eboot/boards/cortex_r5/board_cortex_r5.h"""

    HEADER = _EBOOT_ROOT / "boards" / "cortex_r5" / "board_cortex_r5.h"

    def test_header_exists(self):
        assert self.HEADER.exists()

    def test_include_guard(self):
        content = self.HEADER.read_text()
        assert "#ifndef BOARD_CORTEX_R5_H" in content
        assert "#define BOARD_CORTEX_R5_H" in content
        assert "#endif" in content

    def test_includes_eos_hal(self):
        content = self.HEADER.read_text()
        assert '#include "eos_hal.h"' in content

    def test_atcm_region(self):
        content = self.HEADER.read_text()
        assert "R5_ATCM_BASE" in content
        assert "0x00000000" in content
        assert "(64 * 1024)" in content

    def test_btcm_region(self):
        content = self.HEADER.read_text()
        assert "R5_BTCM_BASE" in content
        assert "0x00080000" in content

    def test_flash_region(self):
        content = self.HEADER.read_text()
        assert "R5_FLASH_BASE" in content
        assert "0x00200000" in content
        assert "(2 * 1024 * 1024)" in content

    def test_ram_region(self):
        content = self.HEADER.read_text()
        assert "R5_RAM_BASE" in content
        assert "0x08000000" in content
        assert "(256 * 1024)" in content

    def test_flash_layout_slots(self):
        content = self.HEADER.read_text()
        for symbol in [
            "R5_STAGE0_ADDR", "R5_STAGE1_ADDR",
            "R5_SLOT_A_ADDR", "R5_SLOT_B_ADDR",
            "R5_RECOVERY_ADDR",
            "R5_BOOTCTL_ADDR", "R5_BOOTCTL_BACKUP_ADDR",
            "R5_LOG_ADDR",
        ]:
            assert symbol in content, f"{symbol} not found in header"

    def test_platform_enum(self):
        content = self.HEADER.read_text()
        assert "EOS_PLATFORM_ARM_R5F" in content

    def test_board_entry_points(self):
        content = self.HEADER.read_text()
        assert "void board_early_init(void);" in content
        assert "const eos_board_ops_t *board_get_ops(void);" in content

    def test_sci_uart_base(self):
        content = self.HEADER.read_text()
        assert "R5_SCI_BASE" in content
        assert "0xFFF7E400" in content

    def test_rti_timer_base(self):
        content = self.HEADER.read_text()
        assert "R5_RTI_BASE" in content


@_skip_no_eboot
@pytest.mark.eboot
class TestEbootBoardPort:
    """1.3 — eboot/boards/cortex_r5/board_cortex_r5.c"""

    SOURCE = _EBOOT_ROOT / "boards" / "cortex_r5" / "board_cortex_r5.c"

    def test_source_exists(self):
        assert self.SOURCE.exists()

    def test_includes_header(self):
        content = self.SOURCE.read_text()
        assert '#include "board_cortex_r5.h"' in content

    def test_cpsid_if_for_interrupt_disable(self):
        """Cortex-R disables both IRQ+FIQ with 'cpsid if'."""
        content = self.SOURCE.read_text()
        assert "cpsid if" in content

    def test_cpsie_if_for_interrupt_enable(self):
        content = self.SOURCE.read_text()
        assert "cpsie if" in content

    def test_no_msp_load_in_jump(self):
        """Cortex-R jump uses direct branch, not MSP load from vector table."""
        content = self.SOURCE.read_text()
        # Ensure the jump function does NOT load MSP (Cortex-M pattern)
        assert "MSR MSP" not in content

    def test_direct_branch_jump(self):
        content = self.SOURCE.read_text()
        assert "entry_fn" in content or "app()" in content

    def test_rti_watchdog_registers(self):
        content = self.SOURCE.read_text()
        assert "RTI_DWDCTRL" in content
        assert "RTI_DWDPRLD" in content
        assert "RTI_WDKEY" in content

    def test_watchdog_key_sequence(self):
        content = self.SOURCE.read_text()
        assert "0xE51A" in content
        assert "0xA35C" in content

    def test_sci_uart_registers(self):
        content = self.SOURCE.read_text()
        assert "SCI_GCR0" in content
        assert "SCI_GCR1" in content
        assert "SCI_TD" in content
        assert "SCI_RD" in content
        assert "SCI_FLR" in content

    def test_board_ops_struct_complete(self):
        """All eos_board_ops_t fields must be populated."""
        content = self.SOURCE.read_text()
        required_fields = [
            ".flash_base", ".flash_size",
            ".slot_a_addr", ".slot_a_size",
            ".slot_b_addr", ".slot_b_size",
            ".recovery_addr", ".recovery_size",
            ".bootctl_addr", ".bootctl_backup_addr",
            ".log_addr", ".app_vector_offset",
            ".flash_read", ".flash_write", ".flash_erase",
            ".watchdog_init", ".watchdog_feed",
            ".get_reset_reason", ".system_reset",
            ".recovery_pin_asserted",
            ".jump",
            ".uart_init", ".uart_send", ".uart_recv",
            ".get_tick_ms",
            ".disable_interrupts", ".enable_interrupts",
            ".deinit_peripherals",
        ]
        for field in required_fields:
            assert field in content, f"Missing board ops field: {field}"

    def test_board_early_init_defined(self):
        content = self.SOURCE.read_text()
        assert re.search(r"void\s+board_early_init\s*\(\s*void\s*\)", content)

    def test_board_get_ops_defined(self):
        content = self.SOURCE.read_text()
        assert re.search(
            r"const\s+eos_board_ops_t\s*\*\s*board_get_ops\s*\(\s*void\s*\)", content
        )


@_skip_no_eboot
@pytest.mark.eboot
class TestEbootLinkerScripts:
    """1.4 & 1.5 — Cortex-R5 linker scripts."""

    STAGE0 = _EBOOT_ROOT / "boards" / "cortex_r5" / "cortex_r5_stage0.ld"
    STAGE1 = _EBOOT_ROOT / "boards" / "cortex_r5" / "cortex_r5_stage1.ld"

    def test_stage0_exists(self):
        assert self.STAGE0.exists()

    def test_stage1_exists(self):
        assert self.STAGE1.exists()

    def test_stage0_atcm_memory(self):
        content = self.STAGE0.read_text()
        assert "ATCM" in content
        assert "0x00000000" in content

    def test_stage0_btcm_memory(self):
        content = self.STAGE0.read_text()
        assert "BTCM" in content
        assert "0x00080000" in content

    def test_stage0_vectors_section(self):
        content = self.STAGE0.read_text()
        assert ".vectors" in content

    def test_stage0_standard_sections(self):
        content = self.STAGE0.read_text()
        assert ".text" in content
        assert ".data" in content
        assert ".bss" in content

    def test_stage1_flash_origin(self):
        content = self.STAGE1.read_text()
        assert "FLASH" in content
        assert "0x00204000" in content

    def test_stage1_ram_region(self):
        content = self.STAGE1.read_text()
        assert "RAM" in content
        assert "0x08000000" in content

    def test_stage1_standard_sections(self):
        content = self.STAGE1.read_text()
        assert ".text" in content
        assert ".data" in content
        assert ".bss" in content


@_skip_no_eboot
@pytest.mark.eboot
class TestEbootCMakeLists:
    """1.6 — eboot/CMakeLists.txt cortex_r5 integration."""

    CMAKE = _EBOOT_ROOT / "CMakeLists.txt"

    def test_cmake_exists(self):
        assert self.CMAKE.exists()

    def test_cortex_r5_in_board_option(self):
        content = self.CMAKE.read_text()
        assert "cortex_r5" in content

    def test_cortex_r5_elseif_block(self):
        content = self.CMAKE.read_text()
        assert 'EBLDR_BOARD STREQUAL "cortex_r5"' in content

    def test_cortex_r5_add_board_call(self):
        content = self.CMAKE.read_text()
        assert "eboot_add_board(cortex_r5" in content

    def test_cortex_r5_board_source_path(self):
        content = self.CMAKE.read_text()
        assert "boards/cortex_r5/board_cortex_r5.c" in content

    def test_cortex_r5_in_error_message(self):
        content = self.CMAKE.read_text()
        # Extract the FATAL_ERROR message block (may span lines with \)
        fatal_block = re.search(r'message\(FATAL_ERROR[^)]+\)', content, re.DOTALL)
        assert fatal_block is not None, "No FATAL_ERROR message found"
        assert "cortex_r5" in fatal_block.group(0), "cortex_r5 not in FATAL_ERROR board list"


@_skip_no_eboot
@pytest.mark.eboot
class TestEbootMPU:
    """1.7 — eboot/core/mpu_boot.c Cortex-R PMSAv7 support."""

    MPU = _EBOOT_ROOT / "core" / "mpu_boot.c"

    def test_mpu_file_exists(self):
        assert self.MPU.exists()

    def test_arm_arch_7r_guard(self):
        content = self.MPU.read_text()
        assert "__ARM_ARCH_7R__" in content

    def test_cp15_region_select(self):
        """RGNR — CP15 c6, c2, 0 for region selection."""
        content = self.MPU.read_text()
        assert "c6, c2, 0" in content

    def test_cp15_drbar(self):
        """DRBAR — CP15 c6, c1, 0 for base address."""
        content = self.MPU.read_text()
        assert "c6, c1, 0" in content

    def test_cp15_drsr(self):
        """DRSR — CP15 c6, c1, 2 for size/enable."""
        content = self.MPU.read_text()
        assert "c6, c1, 2" in content

    def test_cp15_dracr(self):
        """DRACR — CP15 c6, c1, 4 for access control."""
        content = self.MPU.read_text()
        assert "c6, c1, 4" in content

    def test_sctlr_read_write(self):
        """SCTLR — CP15 c1, c0, 0 for MPU enable/disable."""
        content = self.MPU.read_text()
        assert "c1, c0, 0" in content

    def test_isb_after_mpu_operations(self):
        content = self.MPU.read_text()
        assert "isb" in content

    def test_mpu_disable_has_r5_guard(self):
        content = self.MPU.read_text()
        # eos_mpu_disable function body should contain __ARM_ARCH_7R__
        idx = content.index("eos_mpu_disable")
        disable_body = content[idx:idx + 500]
        assert "__ARM_ARCH_7R__" in disable_body

    def test_cortex_m_guard_excludes_r5(self):
        """Cortex-M MPU block must not apply to Cortex-R."""
        content = self.MPU.read_text()
        # The Cortex-M guard in eos_mpu_disable should exclude __ARM_ARCH_7R__
        assert "!defined(__ARM_ARCH_7R__)" in content


@_skip_no_eboot
@pytest.mark.eboot
class TestEbootReleaseCI:
    """4.1 — eboot/.github/workflows/release.yml Cortex-R5 matrix entry."""

    RELEASE = _EBOOT_ROOT / ".github" / "workflows" / "release.yml"

    def test_release_yml_exists(self):
        assert self.RELEASE.exists()

    def test_arm_cortex_r5_arch(self):
        content = self.RELEASE.read_text()
        assert "arm-cortex-r5" in content

    def test_r5_toolchain_reference(self):
        content = self.RELEASE.read_text()
        assert "toolchains/arm-none-eabi-r5.cmake" in content

    def test_r5_packages(self):
        content = self.RELEASE.read_text()
        # Cortex-R5 uses the same GCC package as Cortex-M
        assert "gcc-arm-none-eabi" in content

    def test_r5_artifact_suffix(self):
        content = self.RELEASE.read_text()
        assert "artifact_suffix: arm-cortex-r5" in content

    def test_r5_in_release_body_table(self):
        content = self.RELEASE.read_text()
        assert "arm-cortex-r5.tar.gz" in content


# =====================================================================
# Phase 2 — eos: Cortex-R5 Toolchain + Board + HAL
# =====================================================================

@_skip_no_eos
@pytest.mark.eos
class TestEosToolchainYAML:
    """2.1 — eos/toolchains/arm-none-eabi-r5.yaml"""

    YAML = _EOS_ROOT / "toolchains" / "arm-none-eabi-r5.yaml"

    def test_yaml_exists(self):
        assert self.YAML.exists()

    def test_name_field(self):
        content = self.YAML.read_text()
        assert "name: arm-none-eabi-r5" in content

    def test_target_field(self):
        content = self.YAML.read_text()
        assert "target: arm-none-eabi" in content

    def test_cortex_r5_cflags(self):
        content = self.YAML.read_text()
        assert "-mcpu=cortex-r5" in content
        assert "-mfloat-abi=hard" in content
        assert "-mfpu=vfpv3-d16" in content

    def test_no_thumb_in_cflags(self):
        content = self.YAML.read_text()
        cflags_match = re.search(r'cflags:.*', content)
        assert cflags_match is not None
        assert "-mthumb" not in cflags_match.group(0)

    def test_nosys_ldflags(self):
        content = self.YAML.read_text()
        assert "-specs=nosys.specs" in content

    def test_compiler_cc(self):
        content = self.YAML.read_text()
        assert "cc: arm-none-eabi-gcc" in content


@_skip_no_sibling
@pytest.mark.eos
@pytest.mark.cross_repo
class TestEosToolchainCMake:
    """2.2 — eos/toolchains/arm-none-eabi-r5.cmake"""

    CMAKE = _EOS_ROOT / "toolchains" / "arm-none-eabi-r5.cmake"

    def test_cmake_exists(self):
        assert self.CMAKE.exists()

    def test_matches_eboot_toolchain(self):
        """eos and eboot toolchain files should have identical core flags."""
        eos_content = self.CMAKE.read_text()
        eboot_content = (
            _EBOOT_ROOT / "toolchains" / "arm-none-eabi-r5.cmake"
        ).read_text()
        # Extract C_FLAGS_INIT from both
        eos_flags = re.search(r'CMAKE_C_FLAGS_INIT\s+"([^"]+)"', eos_content)
        eboot_flags = re.search(r'CMAKE_C_FLAGS_INIT\s+"([^"]+)"', eboot_content)
        assert eos_flags and eboot_flags
        assert eos_flags.group(1) == eboot_flags.group(1)


@_skip_no_eos
@pytest.mark.eos
class TestEosBoardYAML:
    """2.3 — eos/boards/tms570.yaml"""

    BOARD = _EOS_ROOT / "boards" / "tms570.yaml"

    def test_board_exists(self):
        assert self.BOARD.exists()

    def test_core_cortex_r5f(self):
        content = self.BOARD.read_text()
        assert "core: cortex-r5f" in content

    def test_arch_arm(self):
        content = self.BOARD.read_text()
        assert "arch: arm" in content

    def test_vendor_ti(self):
        content = self.BOARD.read_text()
        assert "Texas Instruments" in content

    def test_family_tms570(self):
        content = self.BOARD.read_text()
        assert "family: TMS570" in content

    def test_memory_tcm(self):
        content = self.BOARD.read_text()
        assert "tcm:" in content

    def test_safety_feature(self):
        content = self.BOARD.read_text()
        assert "safety" in content

    def test_mpu_feature(self):
        content = self.BOARD.read_text()
        assert "mpu" in content

    def test_toolchain_reference(self):
        content = self.BOARD.read_text()
        assert "toolchain: arm-none-eabi-r5" in content


@_skip_no_eos
@pytest.mark.eos
class TestEosToolchainC:
    """2.4 — eos/toolchains/src/toolchain.c arm-none-eabi detection."""

    SOURCE = _EOS_ROOT / "toolchains" / "src" / "toolchain.c"

    def test_source_exists(self):
        assert self.SOURCE.exists()

    def test_arm_none_eabi_detection(self):
        content = self.SOURCE.read_text()
        assert 'strstr(target, "arm-none-eabi")' in content

    def test_returns_cortex_m_arch(self):
        content = self.SOURCE.read_text()
        assert "EOS_ARCH_ARM_CORTEX_M" in content

    def test_detection_before_fallthrough(self):
        """arm-none-eabi must be detected before the EOS_ARCH_HOST fallthrough."""
        content = self.SOURCE.read_text()
        assert "arm-none-eabi" in content, "arm-none-eabi not found in toolchain.c"
        assert "EOS_ARCH_HOST" in content, "EOS_ARCH_HOST not found in toolchain.c"
        arm_pos = content.index("arm-none-eabi")
        host_pos = content.index("EOS_ARCH_HOST")
        assert arm_pos < host_pos, (
            "arm-none-eabi detection must come before EOS_ARCH_HOST fallthrough"
        )


@_skip_no_eos
@pytest.mark.eos
class TestEosHalRTOS:
    """2.5 — eos/hal/src/hal_rtos.c updated comments."""

    SOURCE = _EOS_ROOT / "hal" / "src" / "hal_rtos.c"

    def test_source_exists(self):
        assert self.SOURCE.exists()

    def test_cortex_r_in_file_comment(self):
        content = self.SOURCE.read_text()
        assert "Cortex-R" in content

    def test_rti_timer_isr_comment(self):
        content = self.SOURCE.read_text()
        assert "RTI timer ISR" in content

    def test_cortex_m_still_mentioned(self):
        content = self.SOURCE.read_text()
        assert "Cortex-M" in content


# =====================================================================
# Phase 3 — ebuild: MCU Database + CLI + Toolchain + Project Generator
# =====================================================================

@pytest.mark.ebuild
class TestEbuildMCUDatabase:
    """3.1 — ebuild MCU_DATABASE R5 entries."""

    def setup_method(self):
        from ebuild.eos_ai.eos_hw_analyzer import EosHardwareAnalyzer
        self.db = EosHardwareAnalyzer.MCU_DATABASE

    def test_tms570_entry(self):
        assert "tms570" in self.db
        assert self.db["tms570"]["core"] == "cortex-r5f"
        assert self.db["tms570"]["arch"] == "arm"
        assert self.db["tms570"]["vendor"] == "TI"
        assert self.db["tms570"]["family"] == "TMS570"

    def test_tms570lc_entry(self):
        assert "tms570lc" in self.db
        assert self.db["tms570lc"]["core"] == "cortex-r5f"

    def test_rm57_entry(self):
        assert "rm57" in self.db
        assert self.db["rm57"]["core"] == "cortex-r5f"
        assert self.db["rm57"]["family"] == "RM57"

    def test_rm46_entry(self):
        assert "rm46" in self.db
        assert self.db["rm46"]["core"] == "cortex-r4f"

    def test_rz_t1_entry(self):
        assert "rz_t1" in self.db
        assert self.db["rz_t1"]["core"] == "cortex-r4f"
        assert self.db["rz_t1"]["vendor"] == "Renesas"

    def test_tms570_text_detection(self):
        from ebuild.eos_ai.eos_hw_analyzer import EosHardwareAnalyzer
        analyzer = EosHardwareAnalyzer()
        profile = analyzer.interpret_text("TMS570 safety-critical MCU with CAN and UART")
        assert profile.mcu == "TMS570"
        assert profile.arch == "arm"
        assert profile.core == "cortex-r5f"
        assert profile.vendor == "TI"

    def test_rm57_text_detection(self):
        from ebuild.eos_ai.eos_hw_analyzer import EosHardwareAnalyzer
        analyzer = EosHardwareAnalyzer()
        profile = analyzer.interpret_text("RM57 lockstep controller")
        assert profile.mcu == "RM57"
        assert profile.core == "cortex-r5f"


@pytest.mark.ebuild
class TestEbuildCLIBoardMap:
    """3.2 — ebuild CLI commands.py board_map."""

    def _get_board_map(self):
        """Extract board_map from commands.py source (avoid import side effects)."""
        src = (_EBUILD_ROOT / "ebuild" / "cli" / "commands.py").read_text()
        # Find the board_map dict in the 'new' command
        assert '"tms570"' in src
        return src

    def test_tms570_in_board_map(self):
        src = self._get_board_map()
        assert '"tms570"' in src

    def _get_tms570_entry(self):
        src = self._get_board_map()
        match = re.search(r'"tms570"\s*:\s*\{([^}]+)\}', src)
        assert match is not None, "tms570 dict entry not found in board_map"
        return match.group(1)

    def test_tms570_arch_arm(self):
        entry = self._get_tms570_entry()
        assert '"arm"' in entry

    def test_tms570_core_r5f(self):
        entry = self._get_tms570_entry()
        assert '"cortex-r5f"' in entry

    def test_tms570_toolchain(self):
        entry = self._get_tms570_entry()
        assert '"arm-none-eabi"' in entry

    def test_tms570_vendor_ti(self):
        entry = self._get_tms570_entry()
        assert '"ti"' in entry

    def test_am64x_hybrid_board(self):
        src = self._get_board_map()
        assert '"am64x"' in src
        am64x_idx = src.index('"am64x"')
        block = src[am64x_idx:am64x_idx + 200]
        assert "r5f" in block


@pytest.mark.ebuild
class TestEbuildPredefinedToolchains:
    """3.3 — ebuild PREDEFINED_TOOLCHAINS arm-none-eabi entry.

    Uses file-based checks to avoid importing modules with heavy
    dependencies (yaml) that may not be installed.
    """

    def _read_toolchain_py(self):
        return (_EBUILD_ROOT / "ebuild" / "build" / "toolchain.py").read_text()

    def test_arm_none_eabi_exists(self):
        content = self._read_toolchain_py()
        assert '"arm-none-eabi"' in content

    def _get_arm_none_eabi_entry(self):
        content = self._read_toolchain_py()
        match = re.search(r'"arm-none-eabi"\s*:\s*\{([^}]+)\}', content)
        assert match is not None, "arm-none-eabi entry not found in PREDEFINED_TOOLCHAINS"
        return match.group(1)

    def test_arm_none_eabi_prefix(self):
        entry = self._get_arm_none_eabi_entry()
        assert '"arm-none-eabi-"' in entry

    def test_arm_none_eabi_arch(self):
        entry = self._get_arm_none_eabi_entry()
        assert '"arm"' in entry


@pytest.mark.ebuild
class TestEbuildProjectGenerator:
    """3.4 — ebuild eos_project_generator.py R5 mappings."""

    def setup_method(self):
        from ebuild.eos_ai.eos_project_generator import EosProjectGenerator
        self.gen = EosProjectGenerator

    def test_tms570_eboot_board_mapping(self):
        assert self.gen.MCU_TO_EBOOT_BOARD.get("tms570") == "cortex_r5"

    def test_rm57_eboot_board_mapping(self):
        assert self.gen.MCU_TO_EBOOT_BOARD.get("rm57") == "cortex_r5"

    def test_rm46_eboot_board_mapping(self):
        assert self.gen.MCU_TO_EBOOT_BOARD.get("rm46") == "cortex_r5"

    def test_arm_cortex_r_toolchain_mapping(self):
        assert self.gen.ARCH_TO_TOOLCHAIN.get("arm-cortex-r") == "arm-none-eabi-r5.yaml"


# =====================================================================
# End-to-End: Full pipeline integration
# =====================================================================

@_skip_no_sibling
@pytest.mark.integration
@pytest.mark.cross_repo
class TestEndToEndPipeline:
    """Validates the complete cross-repo Cortex-R5 pipeline."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(prefix="r5_integ_")

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_analyze_tms570_produces_correct_profile(self):
        """ebuild analyze → hardware profile → correct architecture."""
        from ebuild.eos_ai.eos_hw_analyzer import EosHardwareAnalyzer
        analyzer = EosHardwareAnalyzer()
        profile = analyzer.interpret_text(
            "TMS570LC4357 safety-critical MCU with 4MB flash, 256KB RAM, "
            "300 MHz, CAN LIN UART SPI I2C Ethernet ADC DMA"
        )
        assert profile.mcu == "TMS570"
        assert profile.arch == "arm"
        assert profile.core == "cortex-r5f"
        assert profile.vendor == "TI"
        assert profile.clock_hz == 300_000_000
        types = {p.peripheral_type for p in profile.peripherals}
        assert "can" in types
        assert "uart" in types
        assert "spi" in types
        assert "ethernet" in types
        assert "adc" in types

    def test_project_generator_resolves_manifest(self):
        """generate-project → manifest → correct eboot board + eos toolchain."""
        from ebuild.eos_ai.eos_hw_analyzer import (
            EosHardwareAnalyzer, HardwareProfile, PeripheralInfo,
        )
        from ebuild.eos_ai.eos_project_generator import EosProjectGenerator

        profile = HardwareProfile(
            mcu="TMS570", arch="arm", core="cortex-r5f",
            vendor="TI", flash_size=4 * 1024 * 1024, ram_size=256 * 1024,
            clock_hz=300_000_000,
        )
        profile.peripherals.extend([
            PeripheralInfo(name="CAN", peripheral_type="can"),
            PeripheralInfo(name="UART", peripheral_type="uart"),
            PeripheralInfo(name="SPI", peripheral_type="spi"),
            PeripheralInfo(name="ADC", peripheral_type="adc"),
        ])

        gen = EosProjectGenerator()
        manifest = gen.resolve_manifest(profile)

        assert manifest.eboot_board == "cortex_r5"
        assert manifest.eos_platform == "rtos"
        assert manifest.eos_toolchain == "arm-none-eabi-r5.yaml"
        assert "EOS_ENABLE_UART" in manifest.eos_enables
        assert "EOS_ENABLE_CAN" in manifest.eos_enables
        assert "EOS_ENABLE_SPI" in manifest.eos_enables
        assert "EOS_ENABLE_ADC" in manifest.eos_enables

        # RTOS platform → services/rtos included
        assert "services/rtos" in manifest.eos_dirs

        # CAN → industrial product profile likely
        assert manifest.eos_product in (
            "industrial", "plc", "automotive", "ev", "aerospace",
        )

    def test_eboot_board_has_correct_eboot_dir(self):
        """Eboot board directory for cortex_r5 has all required files."""
        board_dir = _EBOOT_ROOT / "boards" / "cortex_r5"
        assert board_dir.is_dir()
        assert (board_dir / "board_cortex_r5.h").exists()
        assert (board_dir / "board_cortex_r5.c").exists()
        assert (board_dir / "cortex_r5_stage0.ld").exists()
        assert (board_dir / "cortex_r5_stage1.ld").exists()

    def test_eos_board_yaml_toolchain_resolves(self):
        """tms570.yaml references arm-none-eabi-r5 toolchain → that file exists."""
        board_yaml = _EOS_ROOT / "boards" / "tms570.yaml"
        content = board_yaml.read_text()
        assert "toolchain: arm-none-eabi-r5" in content
        # The referenced toolchain YAML must exist
        tc_yaml = _EOS_ROOT / "toolchains" / "arm-none-eabi-r5.yaml"
        assert tc_yaml.exists()
        # The matching CMake toolchain must also exist
        tc_cmake = _EOS_ROOT / "toolchains" / "arm-none-eabi-r5.cmake"
        assert tc_cmake.exists()

    def test_eboot_cmake_toolchain_resolves(self):
        """CMakeLists.txt references cortex_r5 board → toolchain file exists."""
        cmake = _EBOOT_ROOT / "CMakeLists.txt"
        content = cmake.read_text()
        assert "cortex_r5" in content
        tc = _EBOOT_ROOT / "toolchains" / "arm-none-eabi-r5.cmake"
        assert tc.exists()

    def test_memory_map_consistency(self):
        """Header defines, linker scripts, and board ops use consistent addresses."""
        header = (_EBOOT_ROOT / "boards" / "cortex_r5" / "board_cortex_r5.h").read_text()
        stage0 = (_EBOOT_ROOT / "boards" / "cortex_r5" / "cortex_r5_stage0.ld").read_text()
        stage1 = (_EBOOT_ROOT / "boards" / "cortex_r5" / "cortex_r5_stage1.ld").read_text()

        # ATCM base in header and stage0
        assert "0x00000000" in header  # R5_ATCM_BASE
        assert "0x00000000" in stage0  # ATCM origin

        # BTCM base in header and stage0
        assert "0x00080000" in header  # R5_BTCM_BASE
        assert "0x00080000" in stage0  # BTCM origin

        # Stage1 flash at R5_STAGE1_ADDR
        assert "0x00204000" in header  # R5_STAGE1_ADDR
        assert "0x00204000" in stage1  # FLASH origin

        # RAM base
        assert "0x08000000" in header  # R5_RAM_BASE
        assert "0x08000000" in stage1  # RAM origin

    def test_platform_enum_exists_in_eos_hal(self):
        """EOS_PLATFORM_ARM_R5F must be in eos_hal.h."""
        hal_h = _EBOOT_ROOT / "include" / "eos_hal.h"
        content = hal_h.read_text()
        assert "EOS_PLATFORM_ARM_R5F" in content

    def test_cortex_m_vs_r5_toolchain_differentiation(self):
        """Cortex-M and Cortex-R5 toolchains must differ in key flags."""
        cm_tc = (_EBOOT_ROOT / "toolchains" / "arm-none-eabi.cmake").read_text()
        r5_tc = (_EBOOT_ROOT / "toolchains" / "arm-none-eabi-r5.cmake").read_text()

        # Extract CMAKE_C_FLAGS_INIT from each
        cm_match = re.search(r'CMAKE_C_FLAGS_INIT\s+"([^"]+)"', cm_tc)
        assert cm_match, "CMAKE_C_FLAGS_INIT not found in arm-none-eabi.cmake"
        r5_match = re.search(r'CMAKE_C_FLAGS_INIT\s+"([^"]+)"', r5_tc)
        assert r5_match, "CMAKE_C_FLAGS_INIT not found in arm-none-eabi-r5.cmake"
        cm_flags = cm_match.group(1)
        r5_flags = r5_match.group(1)

        # Cortex-M has -mthumb, R5 does not
        assert "-mthumb" in cm_flags
        assert "-mthumb" not in r5_flags

        # Cortex-M targets cortex-m4, R5 targets cortex-r5
        assert "-mcpu=cortex-m4" in cm_flags
        assert "-mcpu=cortex-r5" in r5_flags

        # Both use the same compiler binary
        assert "arm-none-eabi-gcc" in cm_tc
        assert "arm-none-eabi-gcc" in r5_tc

    def test_ebuild_to_eboot_board_roundtrip(self):
        """ebuild MCU_DATABASE → project generator → eboot board dir exists."""
        from ebuild.eos_ai.eos_hw_analyzer import EosHardwareAnalyzer
        from ebuild.eos_ai.eos_project_generator import EosProjectGenerator

        for mcu_key in ("tms570", "rm57", "rm46"):
            props = EosHardwareAnalyzer.MCU_DATABASE[mcu_key]
            eboot_board = EosProjectGenerator.MCU_TO_EBOOT_BOARD.get(mcu_key)
            assert eboot_board is not None, f"No eboot board for {mcu_key}"
            board_dir = _EBOOT_ROOT / "boards" / eboot_board
            assert board_dir.is_dir(), f"Board dir missing: {board_dir}"

    def test_ci_matrix_covers_r5_toolchain(self):
        """release.yml matrix entry references the same toolchain file that exists."""
        release = (_EBOOT_ROOT / ".github" / "workflows" / "release.yml").read_text()
        assert "toolchains/arm-none-eabi-r5.cmake" in release
        assert (_EBOOT_ROOT / "toolchains" / "arm-none-eabi-r5.cmake").exists()


# =====================================================================
# Phase 5 — Example project + template validation
# =====================================================================

@pytest.mark.ebuild
class TestCortexR5Example:
    """Validates the Cortex-R5 example project and safety-critical template."""

    EXAMPLE = _EBUILD_ROOT / "examples" / "cortex_r5_safety"
    TEMPLATE = _EBUILD_ROOT / "templates" / "safety-critical"

    def test_example_directory_exists(self):
        assert self.EXAMPLE.is_dir()

    def test_example_build_yaml(self):
        content = (self.EXAMPLE / "build.yaml").read_text()
        assert "cortex-r5" in content
        assert "tms570" in content

    def test_example_main_has_r5_patterns(self):
        content = (self.EXAMPLE / "src" / "main.c").read_text()
        assert "cpsid if" in content
        assert "RTI" in content
        assert "SCI" in content
        assert "DWD" in content or "dwd" in content
        assert "ESM" in content

    def test_example_has_linker_script(self):
        assert (self.EXAMPLE / "linker" / "tms570_app.ld").exists()
        content = (self.EXAMPLE / "linker" / "tms570_app.ld").read_text()
        assert "0x00210000" in content
        assert "0x08000000" in content

    def test_example_has_startup(self):
        assert (self.EXAMPLE / "src" / "r5_startup.c").exists()
        content = (self.EXAMPLE / "src" / "r5_startup.c").read_text()
        assert ".vectors" in content
        assert "_reset_handler" in content

    def test_example_has_config_header(self):
        assert (self.EXAMPLE / "include" / "app_config.h").exists()
        content = (self.EXAMPLE / "include" / "app_config.h").read_text()
        assert "APP_SCI_BASE" in content
        assert "APP_RTI_BASE" in content
        assert "APP_ESM_BASE" in content

    def test_example_has_readme(self):
        assert (self.EXAMPLE / "README.md").exists()
        content = (self.EXAMPLE / "README.md").read_text()
        assert "TMS570" in content
        assert "Cortex-R5" in content

    def test_template_directory_exists(self):
        assert self.TEMPLATE.is_dir()

    def test_template_has_all_files(self):
        for f in ["main.c.template", "build.yaml.template",
                   "eos.yaml.template", "README.md.template"]:
            assert (self.TEMPLATE / f).exists(), f"Missing {f}"

    def test_template_uses_placeholders(self):
        content = (self.TEMPLATE / "main.c.template").read_text()
        assert "{{PROJECT_NAME}}" in content
        assert "{{BOARD_NAME}}" in content

    def test_template_main_has_r5_patterns(self):
        content = (self.TEMPLATE / "main.c.template").read_text()
        assert "cpsid if" in content
        assert "SCI" in content
        assert "RTI" in content or "DWD" in content
        assert "ESM" in content

    def test_safety_critical_in_cli_choices(self):
        src = (_EBUILD_ROOT / "ebuild" / "cli" / "commands.py").read_text()
        assert "safety-critical" in src


# =====================================================================
# Standalone runner (no pytest required)
# =====================================================================

if __name__ == "__main__":
    import traceback

    test_classes = [
        # Phase 1 — eboot
        TestEbootToolchain,
        TestEbootBoardHeader,
        TestEbootBoardPort,
        TestEbootLinkerScripts,
        TestEbootCMakeLists,
        TestEbootMPU,
        TestEbootReleaseCI,
        # Phase 2 — eos
        TestEosToolchainYAML,
        TestEosToolchainCMake,
        TestEosBoardYAML,
        TestEosToolchainC,
        TestEosHalRTOS,
        # Phase 3 — ebuild
        TestEbuildMCUDatabase,
        TestEbuildCLIBoardMap,
        TestEbuildPredefinedToolchains,
        TestEbuildProjectGenerator,
        # End-to-end
        TestEndToEndPipeline,
        # Example + template
        TestCortexR5Example,
    ]

    total = 0
    passed = 0
    failed = 0
    errors = []

    for TestClass in test_classes:
        instance = TestClass()
        methods = sorted(m for m in dir(instance) if m.startswith("test_"))
        for method_name in methods:
            total += 1
            try:
                if hasattr(instance, "setup_method"):
                    instance.setup_method()
                getattr(instance, method_name)()
                passed += 1
                print(f"  PASS: {TestClass.__name__}.{method_name}")
            except Exception as e:
                failed += 1
                errors.append(f"{TestClass.__name__}.{method_name}")
                print(f"  FAIL: {TestClass.__name__}.{method_name} — {e}")
                traceback.print_exc()
            finally:
                if hasattr(instance, "teardown_method"):
                    try:
                        instance.teardown_method()
                    except Exception:
                        pass

    print(f"\n{'=' * 60}")
    print(f"Cortex-R5 Integration Tests: {passed}/{total} passed, {failed} failed")
    if errors:
        print(f"\nFailed tests:")
        for e in errors:
            print(f"  FAIL: {e}")
    print(f"{'=' * 60}")
    sys.exit(0 if failed == 0 else 1)
