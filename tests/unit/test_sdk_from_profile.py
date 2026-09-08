# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Regression + feature tests for profile-driven SDK generation.

Method (characterization-first, per Working Effectively with Legacy Code):
1. test_sdk_from_name_falls_back_to_x86_64 pins the legacy name-based fallback
   of generate_sdk(name) for an unknown MCU -- it must still regress to x86_64
   so we never silently "fix" the fallback and break callers that rely on it.
2. test_sdk_from_profile_nrf52840 proves the P0 fix: a detected nrf52840
   profile now yields an arm-none-eabi SDK with the right EOS_ENABLE_* header,
   not a host x86_64 toolchain.
3. test_pipeline_sdk_raspi4_stays_aarch64 proves a documented TARGET_ARCH
   target the analyzer gives no `mcu` for keeps its canonical aarch64 toolchain
   (the exact defect the PR fixes, must not be reintroduced).
4. test_detected_unmapped_mcu_skips_foreign_linker_script proves a detected MCU
   not in EBOOT_BOARD gets the honest x86_64 fallback and NO wrong memory map.
"""
import json
import os
import tempfile
from pathlib import Path

from ebuild.sdk_generator import (
    EBOOT_BOARD,
    TARGET_ARCH,
    _info_from_profile,
    _resolve_eboot_board_dir,
    board_dir_for_core,
    board_dir_for_mcu,
    generate_sdk,
    generate_sdk_from_profile,
)
from ebuild.eos_ai.eos_hw_analyzer import HardwareProfile, PeripheralInfo


def _read(path):
    with open(path) as f:
        return f.read()


def _proc_eboot(sdk_dir):
    import re

    tc = _read(os.path.join(sdk_dir, "toolchain.cmake"))
    proc = re.search(r"CMAKE_SYSTEM_PROCESSOR ([a-z0-9_]+)", tc)
    proc = proc.group(1) if proc else "?"
    eb = _read(os.path.join(sdk_dir, "eboot", "eboot_board.cmake"))
    board = re.search(r"set\(EBOOT_BOARD ([^)]+)\)", eb)
    board = board.group(1).strip() if board else "?"
    return proc, board


def test_sdk_from_name_falls_back_to_x86_64():
    """Pin the legacy name-based fallback: unknown MCU -> x86_64 SDK.

    This is the behaviour the P0 fix deliberately preserves for callers that
    only have a target string. If it ever changes, the fallback regressed.
    """
    with tempfile.TemporaryDirectory() as out:
        sdk_dir = generate_sdk("nrf52840", out)
        tc = _read(os.path.join(sdk_dir, "toolchain.cmake"))
        # Legacy table has no nrf52840 -> default x86_64 triplet.
        assert "x86_64-linux-gnu-gcc" in tc, tc
        info = _read(os.path.join(sdk_dir, "sdk-info.txt"))
        assert "Arch:    x86_64" in info, info


def test_sdk_from_profile_nrf52840():
    """P0 fix: detected nrf52840 profile -> arm-none-eabi SDK, not x86_64.

    Drive the SDK from the detected profile. nrf52840 is in the analyzer DB so
    it resolves to an arm-none-eabi toolchain, while the legacy name-only path
    would have emitted x86_64.
    """
    profile = HardwareProfile()
    profile.mcu = "nrf52840"
    profile.arch = "arm"
    profile.core = "cortex-m4f"
    profile.vendor = "Nordic"
    profile.mcu_family = "nRF52"
    profile.peripherals = [
        PeripheralInfo(name="ble", peripheral_type="ble"),
        PeripheralInfo(name="i2c", peripheral_type="i2c"),
        PeripheralInfo(name="spi", peripheral_type="spi"),
    ]

    with tempfile.TemporaryDirectory() as out:
        sdk_dir, _, _ = generate_sdk_from_profile(profile, out, target="nrf52840")
        tc = _read(os.path.join(sdk_dir, "toolchain.cmake"))
        assert "arm-none-eabi-gcc" in tc, "SDK must target the detected ARM chip, got:\n" + tc
        assert "x86_64" not in tc, "P0 regression: SDK regressed to host x86_64"
        info = _read(os.path.join(sdk_dir, "sdk-info.txt"))
        assert "Arch:    arm" in info, info
        # Manifest records the detected target, not the host.
        manifest = json.loads(_read(os.path.join(out, "manifest.json")))
        assert manifest["target"]["arch"] == "arm", manifest
        assert manifest["target"]["triplet"] == "arm-none-eabi", manifest


def test_pipeline_sdk_matches_detected_profile():
    """End-to-end guard: the pipeline SDK step must follow the detected profile.

    _run_pipeline_steps detects nrf52840 in the analyzer DB, then Step 4 must
    emit an arm-none-eabi SDK. If the pipeline ever reverts to
    generate_sdk(board.lower()), this FAILS because the name-only path produces
    an x86_64 SDK for nrf52840.
    """
    from ebuild.cli.commands import _run_pipeline_steps
    from ebuild.cli.logger import Logger

    with tempfile.TemporaryDirectory() as out:
        build_dir = os.path.join(out, "_build")
        profile, _configs, _boot = _run_pipeline_steps(
            board="nrf52840", hardware=None, build_dir=Path(build_dir), log=Logger(verbose=False)
        )
        # Analyzer detected the ARM chip.
        assert profile.arch == "arm", profile.arch
        sdk_dir = os.path.join(build_dir, "sdk")
        tc = _read(os.path.join(sdk_dir, "eos-sdk-nrf52840", "toolchain.cmake"))
        assert "arm-none-eabi-gcc" in tc, "pipeline SDK must match detected ARM chip:\n" + tc
        assert "x86_64" not in tc, "P0 regression: pipeline SDK regressed to host x86_64"


def test_pipeline_sdk_raspi4_stays_aarch64():
    """Documented target with no analyzer `mcu` keeps its canonical toolchain.

    raspi4 is a TARGET_ARCH key but the analyzer gives it no `mcu`, so the
    profile path must fall back to get_target_info("raspi4") and keep
    aarch64-linux-gnu, never an empty `eos-sdk-` dir or an x86_64 SDK. This is
    the exact defect the PR exists to fix; reintroducing it here fails.
    """
    from ebuild.cli.commands import _run_pipeline_steps
    from ebuild.cli.logger import Logger

    with tempfile.TemporaryDirectory() as out:
        build_dir = os.path.join(out, "_build")
        _run_pipeline_steps(
            board="raspi4", hardware=None, build_dir=Path(build_dir), log=Logger(verbose=False)
        )
        sdk_dir = os.path.join(build_dir, "sdk", "eos-sdk-raspi4")
        tc = _read(os.path.join(sdk_dir, "toolchain.cmake"))
        assert "aarch64-linux-gnu-gcc" in tc, "raspi4 must stay aarch64, got:\n" + tc
        assert "x86_64" not in tc, "raspi4 regressed to host x86_64"
        # Directory name is correct, not empty.
        assert os.path.isdir(sdk_dir), "eos-sdk-raspi4 directory must exist"


def test_detected_unmapped_mcu_skips_foreign_linker_script():
    """A detected Cortex-M part absent from EBOOT_BOARD gets the right detected
    toolchain (arm-none-eabi) and NO linker script carrying another chip's
    memory map.

    stm32f103 is a Cortex-M part the analyzer detects, so it must compile with
    arm-none-eabi (the whole point of the fix). eboot ships no board for it, so
    the writer must skip the per-chip .ld rather than emit a foreign memory map
    (the old code wrote an nRF52 linker script here).
    """
    profile = HardwareProfile()
    profile.mcu = "stm32f103"
    profile.arch = "arm"
    profile.core = "cortex-m3"
    profile.vendor = "ST"
    profile.mcu_family = "STM32F1"

    with tempfile.TemporaryDirectory() as out:
        sdk_dir, _, _ = generate_sdk_from_profile(profile, out, target="stm32f103")
        # Detected MCU -> correct bare-metal toolchain (not the host x86_64).
        tc = _read(os.path.join(sdk_dir, "toolchain.cmake"))
        assert "arm-none-eabi-gcc" in tc, tc
        assert "x86_64" not in tc, "detected MCU must not fall back to host x86_64"
        # No foreign per-chip linker script must be written.
        ld = os.path.join(sdk_dir, "eboot", "eboot_stm32f103.ld")
        assert not os.path.exists(ld), "must not emit another chip's memory map"


def test_sdk_from_profile_unknown_mcu_uses_fallback():
    """A profile with no usable arch/core still degrades to the x86_64 fallback."""
    profile = HardwareProfile()
    profile.mcu = "some-unknown-part"
    profile.arch = ""
    profile.core = ""
    profile.vendor = ""
    with tempfile.TemporaryDirectory() as out:
        sdk_dir, _, _ = generate_sdk_from_profile(profile, out, target="some-unknown-part")
        tc = _read(os.path.join(sdk_dir, "toolchain.cmake"))
        assert "x86_64-linux-gnu-gcc" in tc, tc


def test_known_targets_do_not_regress_through_pipeline():
    """Every supported board keeps its legacy toolchain + eboot through the pipeline.

    A known board (a TARGET_ARCH key) must produce exactly the same
    CMAKE_SYSTEM_PROCESSOR and EBOOT_BOARD through the pipeline as the legacy
    generate_sdk(name) call. generate_sdk_from_profile must prefer the canonical
    name mapping for known targets and only enrich boards the name table lacks.
    """
    from ebuild.cli.commands import _run_pipeline_steps
    from ebuild.cli.logger import Logger

    for name in TARGET_ARCH:
        with tempfile.TemporaryDirectory() as leg_out:
            leg_dir = generate_sdk(name, leg_out)
            leg_proc, leg_board = _proc_eboot(leg_dir)

        with tempfile.TemporaryDirectory() as out:
            build_dir = os.path.join(out, "_build")
            _run_pipeline_steps(
                board=name, hardware=None, build_dir=Path(build_dir), log=Logger(verbose=False)
            )
            pipe_proc, pipe_board = _proc_eboot(
                os.path.join(build_dir, "sdk", "eos-sdk-" + name.lower())
            )

        assert pipe_proc == leg_proc, f"{name}: toolchain {pipe_proc} != legacy {leg_proc}"
        assert pipe_board == leg_board, f"{name}: eboot {pipe_board} != legacy {leg_board}"


def test_profile_aarch64_core_cortex_a72_is_64bit_toolchain():
    """arch=arm64 + core=cortex-a72 must be aarch64-linux-gnu.

    The 64-bit arch must win over the Cortex-A core string, so a 64-bit ARM
    part (e.g. rk3588 = cortex-a76, or an unknown cortex-a72 part) gets the
    64-bit toolchain, not the 32-bit arm-linux-gnueabihf the previous Core-
    before-Arch ordering produced. This is a case where arch and core disagree
    and the previous suite had no such example.
    """
    profile = HardwareProfile()
    profile.mcu = "rk3588"
    profile.arch = "arm64"
    profile.core = "cortex-a72"
    profile.vendor = "Rockchip"
    profile.mcu_family = "RK3588"

    with tempfile.TemporaryDirectory() as out:
        sdk_dir, _, _ = generate_sdk_from_profile(profile, out, target="rk3588")
        tc = _read(os.path.join(sdk_dir, "toolchain.cmake"))
        assert "aarch64-linux-gnu-gcc" in tc, "64-bit ARM must get aarch64 toolchain, got:\n" + tc
        assert "arm-linux-gnueabihf" not in tc, "regressed to 32-bit toolchain for 64-bit ARM"
        assert "x86_64" not in tc, "regressed to host x86_64"
        info = _read(os.path.join(sdk_dir, "sdk-info.txt"))
        assert "Arch:    aarch64" in info, info


def test_profile_riscv64_is_sbc_class():
    """Detected riscv64 is class=sbc, not a virtual machine.

    A real 64-bit RISC-V part (e.g. sifive_u = rv64gc) must get riscv64-linux-gnu
    and class=sbc. The previous code labelled every detected RISC-V part as
    class=virtual, discarding the real-silicon vs QEMU distinction that
    TARGET_ARCH itself makes (riscv_virt=virtual, sifive_u=sbc).
    """
    profile = HardwareProfile()
    profile.mcu = "sifive_u"
    profile.arch = "riscv64"
    profile.core = "rv64gc"
    profile.vendor = "SiFive"
    profile.mcu_family = "FU740"

    with tempfile.TemporaryDirectory() as out:
        sdk_dir, _, _ = generate_sdk_from_profile(profile, out, target="sifive_u")
        tc = _read(os.path.join(sdk_dir, "toolchain.cmake"))
        assert "riscv64-linux-gnu-gcc" in tc, "riscv64 must get riscv64 toolchain, got:\n" + tc
        assert "x86_64" not in tc, "regressed to host x86_64"
        info = _read(os.path.join(sdk_dir, "sdk-info.txt"))
        assert "Arch:    riscv64" in info, info
        assert "Class:   sbc" in info, "detected RISC-V must be class=sbc, not virtual:\n" + info


def test_profile_riscv32_uses_honest_fallback():
    """riscv32 has no repo toolchain, so it must NOT get a
    64-bit triplet. Returning None makes the caller keep the honest x86_64
    fallback instead of inventing riscv64-linux-gnu for 32-bit silicon
    (esp32c3 / sifive_e / gd32vf103 in MCU_DATABASE are rv32imac)."""
    profile = HardwareProfile()
    profile.mcu = "esp32c3"
    profile.arch = "riscv32"
    profile.core = "rv32imc"
    profile.vendor = "Espressif"
    profile.mcu_family = "ESP32C3"

    with tempfile.TemporaryDirectory() as out:
        sdk_dir, _, _ = generate_sdk_from_profile(profile, out, target="esp32c3")
        tc = _read(os.path.join(sdk_dir, "toolchain.cmake"))
        assert "riscv64-linux-gnu-gcc" not in tc, "must not emit 64-bit toolchain for 32-bit RISC-V:\n" + tc
        # Honest fallback: x86_64 (no rv32 toolchain ships in the repo).
        assert "x86_64-linux-gnu-gcc" in tc, "riscv32 must fall back to x86_64, got:\n" + tc


def test_unmapped_mcu_emits_no_x86_eboot_board():
    """A detected MCU must never fall back to the x86 eboot board (the master
    bug). stm32f103 now resolves the upstream cortex_m3 core-class board via
    stage 3, so the honest-board assertion lives in
    test_pipeline_completes_for_good_toolchain_missing_board; this test keeps
    guarding the never-x86 rule with a part whose board eBoot genuinely does
    not ship (atmega328p, AVR, no x86_64 default).
    """
    profile = HardwareProfile()
    profile.mcu = "atmega328p"
    profile.arch = "avr"
    profile.core = "avr5"
    profile.vendor = "Microchip"
    profile.mcu_family = "AVR"

    with tempfile.TemporaryDirectory() as out:
        sdk_dir, _, _ = generate_sdk_from_profile(profile, out, target="atmega328p")
        cfg = _read(os.path.join(sdk_dir, "eboot", "eboot_board.cmake"))
        assert "EBOOT_BOARD x86" not in cfg, "must not silently pick x86 board:\n" + cfg
        assert "EBOOT_BOARD " not in cfg, "no eboot board must be emitted for unmapped MCU:\n" + cfg
        hdr = _read(os.path.join(sdk_dir, "eboot", "eboot_target_config.h"))
        assert "EBOOT_BOARD_NAME" not in hdr, "no board name for unmapped MCU:\n" + hdr


def test_eboot_key_is_target_name_or_none():
    """_resolve_eboot_board_dir must return a board dir, or None on a miss.

    Stage 1 (no profile): exact target-name match in EBOOT_BOARD, else None.
    Stage 2 (with profile): MCU-prefix match against the analyzer's map, so a
    detected chip whose board the target table knows only by MCU prefix (e.g.
    nrf52840 -> nrf52) resolves, which the old target-only lookup never did.
    """
    from ebuild.sdk_generator import _resolve_eboot_board_dir

    # Stage 1: target-name match
    assert _resolve_eboot_board_dir("riscv_virt") == "riscv64_virt"
    assert _resolve_eboot_board_dir("nrf52") == "nrf52"
    assert _resolve_eboot_board_dir("not-a-real-chip") is None

    # Stage 2: MCU-prefix match needs a profile
    profile = HardwareProfile()
    profile.mcu = "nrf52840"
    assert _resolve_eboot_board_dir("nrf52840", profile) == "nrf52"
    # Bare profile (no core set): stage 2 misses on the MCU name and stage 3
    # has no core to match, so a chip-named miss stays a miss here. With a
    # real core (cortex-m3) stm32f103 resolves via stage 3 — pinned in
    # test_pipeline_completes_for_good_toolchain_missing_board.
    profile.mcu = "stm32f103"
    assert _resolve_eboot_board_dir("stm32f103", profile) is None

    # Every TARGET_ARCH key that has an eboot board resolves to a real board
    # directory (a value in EBOOT_BOARD), or None when eBoot ships no board.
    valid = set(EBOOT_BOARD.values())
    for key in TARGET_ARCH:
        resolved = _resolve_eboot_board_dir(key)
        assert resolved is None or resolved in valid, (key, resolved)


def test_pipeline_nrf52840_gets_eboot_nrf52():
    """Flagship example must end up with a real eBoot board.

    nrf52840 is not a TARGET_ARCH key, but the analyzer knows it by MCU prefix
    (MCU_TO_EBOOT_BOARD: nrf52840 -> nrf52). The profile path must resolve it
    so the headline example produces a usable SDK, not a fail-loud no-board.
    """
    profile = HardwareProfile()
    profile.mcu = "nrf52840"
    profile.arch = "arm"
    profile.core = "cortex-m4f"
    profile.vendor = "Nordic"
    profile.mcu_family = "nRF52"

    with tempfile.TemporaryDirectory() as out:
        sdk_dir, _, _ = generate_sdk_from_profile(profile, out, target="nrf52840")
        eb = _read(os.path.join(sdk_dir, "eboot", "eboot_board.cmake"))
        assert "set(EBOOT_BOARD nrf52)" in eb, eb
        # nrf52840 is not an exact TARGET_ARCH key, so no per-chip MEMORY block
        # is emitted (a family board dir must never select a memory map).
        assert not os.path.exists(os.path.join(sdk_dir, "eboot", "eboot_nrf52840.ld"))
        info = _read(os.path.join(sdk_dir, "sdk-info.txt"))
        assert "Vendor:  Nordic" in info, info


def test_stm32f103_still_no_eboot_and_fails_closed():
    """stm32f103 has no chip-named MCU row: stage 3 resolves the upstream
    cortex_m3 core-class board, so it no longer fails closed — it gets the
    real board (see test_pipeline_completes_for_good_toolchain_missing_board).
    This test now pins the chip-named-row miss behaviour on a part whose core
    eBoot also does not ship: the FATAL_ERROR text names the chip honestly.
    """
    profile = HardwareProfile()
    profile.mcu = "atmega328p"
    profile.arch = "avr"
    profile.core = "avr5"
    profile.vendor = "Microchip"
    profile.mcu_family = "AVR"

    with tempfile.TemporaryDirectory() as out:
        sdk_dir, _, _ = generate_sdk_from_profile(profile, out, target="atmega328p")
        eb = _read(os.path.join(sdk_dir, "eboot", "eboot_board.cmake"))
        assert "EBOOT_BOARD " not in eb
        assert "FATAL_ERROR" in eb and "atmega328p" in eb, eb
        # Toolchain also misses (no avr toolchain): the diagnostic says so.
        assert "no cross-toolchain" in eb, eb


def test_riscv_alt_spelling_falls_back():
    """rv32* / riscv32imac must not slip through to riscv64 (finding 5)."""
    p = HardwareProfile()
    p.mcu = "custom32"
    p.arch = "riscv32imac"
    p.core = "rv32imac"
    assert _info_from_profile(p) is None
    p2 = HardwareProfile()
    p2.mcu = "x"
    p2.arch = "riscv"
    p2.core = "rv32imac"
    assert _info_from_profile(p2) is None


def test_vendor_threaded_from_profile():
    """Analyzer vendor is carried into the SDK, not dropped to Generic (F4)."""
    p = HardwareProfile()
    p.mcu = "nrf52840"
    p.arch = "arm"
    p.core = "cortex-m4f"
    p.vendor = "Nordic"
    p.mcu_family = "nRF52"
    assert _info_from_profile(p)["vendor"] == "Nordic"


def test_family_sibling_does_not_inherit_flagship_memory_map():
    """stm32f401 prefix-matches the stm32f4 board but has 256K/64K, not 1024K/128K.

    The MCU-prefix match may select the board *directory* (family-wide), but it
    must never select the per-chip MEMORY block. A sibling gets board vars and
    a warning, never a foreign linker script.
    """
    profile = HardwareProfile()
    profile.mcu = "stm32f401"
    profile.arch = "arm"
    profile.core = "cortex-m4"
    profile.vendor = "ST"
    profile.mcu_family = "STM32F4"

    with tempfile.TemporaryDirectory() as out:
        sdk_dir, _, _ = generate_sdk_from_profile(profile, out, target="stm32f401")
        assert not os.path.exists(os.path.join(sdk_dir, "eboot", "eboot_stm32f401.ld"))
        eb = _read(os.path.join(sdk_dir, "eboot", "eboot_board.cmake"))
        assert "set(EBOOT_BOARD stm32f4)" in eb, eb


def test_toolchain_miss_fails_closed_despite_resolved_board():
    """A resolved board paired with an unsupported toolchain must fail closed.

    A detected Xtensa part prefix-matches an eBoot board dir, but the SDK ships
    no Xtensa toolchain, so the output falls back to x86_64. Emitting the real
    board next to a fallback arch looks valid but is contradictory — the writer
    must emit no EBOOT_BOARD and a FATAL_ERROR instead.
    """
    profile = HardwareProfile()
    profile.mcu = "esp32dev"
    profile.arch = "xtensa"
    profile.core = "lx6"
    profile.vendor = "Espressif"
    profile.mcu_family = "ESP32"

    with tempfile.TemporaryDirectory() as out:
        sdk_dir, _, _ = generate_sdk_from_profile(profile, out, target="esp32dev")
        tc = _read(os.path.join(sdk_dir, "toolchain.cmake"))
        assert "x86_64-linux-gnu-gcc" in tc, tc
        eb = _read(os.path.join(sdk_dir, "eboot", "eboot_board.cmake"))
        assert "set(EBOOT_BOARD " not in eb, eb
        assert "FATAL_ERROR" in eb and "esp32dev" in eb, eb


def test_toolchain_miss_is_marked_fallback_everywhere():
    """A toolchain miss must be visible on every consumer surface, not just the
    eboot cmake file: environment-setup exports CMAKE_TOOLCHAIN_FILE (which
    never includes eboot_board.cmake), so a sourced env would silently hand out
    a desktop compiler for an unmapped chip — the exact defect this PR fixes.
    """
    profile = HardwareProfile()
    profile.mcu = "esp32dev"
    profile.arch = "xtensa"
    profile.core = "lx6"
    profile.vendor = "Espressif"
    profile.mcu_family = "ESP32"

    with tempfile.TemporaryDirectory() as out:
        sdk_dir, _, _ = generate_sdk_from_profile(profile, out, target="esp32dev")
        manifest = json.loads(_read(os.path.join(out, "manifest.json")))
        assert manifest["target"].get("toolchain") == "fallback", manifest
        info = _read(os.path.join(sdk_dir, "sdk-info.txt"))
        assert "Toolchain:  fallback" in info, info
        env = _read(os.path.join(sdk_dir, "environment-setup"))
        assert "unsupported target esp32dev" in env, env
        bat = _read(os.path.join(sdk_dir, "environment-setup.bat"))
        assert "unsupported target esp32dev" in bat, bat


def test_supported_target_has_no_fallback_markers():
    """Known targets stay byte-identical: no fallback keys appear anywhere."""
    with tempfile.TemporaryDirectory() as out:
        sdk_dir = generate_sdk("nrf52", out)
        manifest = json.loads(_read(os.path.join(out, "manifest.json")))
        assert "toolchain" not in manifest["target"], manifest
        info = _read(os.path.join(sdk_dir, "sdk-info.txt"))
        assert "fallback" not in info, info
        env = _read(os.path.join(sdk_dir, "environment-setup"))
        assert "unsupported target" not in env, env


def test_generate_sdk_from_profile_returns_status_triple():
    """Callers (pipeline step 4) need the resolution status, not just the dir."""
    ok_profile = HardwareProfile()
    ok_profile.mcu = "nrf52840"
    ok_profile.arch = "arm"
    ok_profile.core = "cortex-m4f"
    ok_profile.vendor = "Nordic"
    ok_profile.mcu_family = "nRF52"
    miss_profile = HardwareProfile()
    miss_profile.mcu = "esp32dev"
    miss_profile.arch = "xtensa"
    miss_profile.core = "lx6"

    with tempfile.TemporaryDirectory() as out:
        sdk_dir, toolchain_ok, eboot_board = generate_sdk_from_profile(
            ok_profile, out, target="nrf52840")
        assert os.path.isdir(sdk_dir)
        assert toolchain_ok is True
        assert eboot_board == "nrf52"
        _, toolchain_ok, eboot_board = generate_sdk_from_profile(
            miss_profile, out, target="esp32dev")
        assert toolchain_ok is False
        assert eboot_board is None


def test_prefix_scan_prefers_longest_match():
    """The MCU-prefix scan must prefer the longest prefix: esp32c3/esp32s3 both
    start with esp32, and ultrasparc_t starts with ultrasparc — first-match
    order would resolve all three to the wrong (shorter) board dir.
    """
    for mcu, board in (("esp32c3", "esp32c3"), ("esp32s3", "esp32s3"),
                       ("ultrasparc_t", "sparc64")):
        profile = HardwareProfile()
        profile.mcu = mcu
        assert _resolve_eboot_board_dir(mcu, profile) == board, mcu


def test_pipeline_completes_for_good_toolchain_missing_board(capsys):
    """A correct toolchain with no eBoot board must warn and continue, not exit.

    stm32f103 derives arm-none-eabi correctly; eBoot ships no board for it.
    The pipeline must finish (master completed for these chips) while the
    board consumer still fails by name via the FATAL_ERROR in
    eboot_board.cmake.
    """
    from ebuild.cli.commands import _run_pipeline_steps
    from ebuild.cli.logger import Logger
    from pathlib import Path

    with tempfile.TemporaryDirectory() as out:
        _run_pipeline_steps(board="stm32f103", hardware=None,
                            build_dir=Path(out), log=Logger(verbose=False))
        sdk_dir = os.path.join(out, "sdk", "eos-sdk-stm32f103")
        tc = _read(os.path.join(sdk_dir, "toolchain.cmake"))
        assert "arm-none-eabi-gcc" in tc, tc
        eb = _read(os.path.join(sdk_dir, "eboot", "eboot_board.cmake"))
        # eBoot ships a cortex_m3 board port upstream: the board must resolve,
        # not fail closed (the FATAL_ERROR here would be a false statement).
        assert "FATAL_ERROR" not in eb, eb
        assert "set(EBOOT_BOARD cortex_m3)" in eb, eb
    captured = capsys.readouterr()
    assert "no eBoot board for stm32f103" not in captured.out + captured.err


def test_legacy_name_path_marks_fallback_on_all_surfaces():
    """Legacy generate_sdk with an unmapped name gets the FATAL_ERROR and all
    four fallback markers — honest labelling, same as the profile path.
    """
    with tempfile.TemporaryDirectory() as out:
        sdk_dir = generate_sdk("stm32f103", out)
        eb = _read(os.path.join(sdk_dir, "eboot", "eboot_board.cmake"))
        assert "FATAL_ERROR" in eb, eb
        manifest = json.loads(_read(os.path.join(out, "manifest.json")))
        assert manifest["target"].get("toolchain") == "fallback", manifest
        info = _read(os.path.join(sdk_dir, "sdk-info.txt"))
        assert "Toolchain:  fallback" in info, info
        env = _read(os.path.join(sdk_dir, "environment-setup"))
        assert "unsupported target stm32f103" in env, env


def test_profile_non_cortex_arm_gets_arm_toolchain():
    """ARM7TDMI / XScale parts have no Cortex core string but arm-none-eabi
    is exactly their toolchain. pxa270 resolves a real board (xscale);
    lpc2148 (arm7tdmi) gets the triplet with the board warning.
    """
    pxa = HardwareProfile()
    pxa.mcu = "pxa270"
    pxa.arch = "arm"
    pxa.core = "xscale"
    pxa.vendor = "Marvell"
    pxa.mcu_family = "PXA27x"
    lpc = HardwareProfile()
    lpc.mcu = "lpc2148"
    lpc.arch = "arm"
    lpc.core = "arm7tdmi"
    lpc.vendor = "NXP"
    lpc.mcu_family = "LPC2000"

    with tempfile.TemporaryDirectory() as out:
        pxa_dir, pxa_ok, pxa_board = generate_sdk_from_profile(pxa, out, target="pxa270")
        assert pxa_ok is True
        assert pxa_board == "xscale", pxa_board
        tc = _read(os.path.join(pxa_dir, "toolchain.cmake"))
        assert "arm-none-eabi-gcc" in tc, tc
        lpc_dir, lpc_ok, lpc_board = generate_sdk_from_profile(lpc, out, target="lpc2148")
        assert lpc_ok is True
        # eBoot ships an arm7tdmi core-class board upstream: stage 3 resolves it.
        assert lpc_board == "arm7tdmi", lpc_board
        tc = _read(os.path.join(lpc_dir, "toolchain.cmake"))
        assert "arm-none-eabi-gcc" in tc, tc
        eb = _read(os.path.join(lpc_dir, "eboot", "eboot_board.cmake"))
        assert "FATAL_ERROR" not in eb, eb


def test_core_named_boards_resolve_from_core_string():
    """eBoot ships generic core-class ports: a chip with no chip-named row
    gets the real board its core uses. Separator-insensitive and
    microarch-suffix aware (arm926ej-s -> arm9, arm1176jzf-s -> arm11)."""
    cases = {
        "stm32f103": "cortex-m3",
        "stm32f030": "cortex-m0",
        "stm32l072": "cortex-m0+",
        "lpc55s06": "cortex-m23",
        "stm32u5": "cortex-m33",
        "ra8m1": "cortex-m85",
        "cortex_r52": "cortex-r52",
        "rz_t1": "cortex-r4f",
        "at91sam9g25": "arm926ej-s",
        "bcm2835": "arm1176jzf-s",
        "zynq7020": "cortex-a9",
        "rk3588": "cortex-a76",
        "sama5d36": "cortex-a5",
        "omap5432": "cortex-a15",
    }
    for mcu, core in cases.items():
        assert board_dir_for_core(core) is not None, mcu + " (" + core + ")"


def test_board_stage_order_is_exact_then_mcu_then_core():
    """Stage order must hold: a chip whose MCU row and core both resolve keeps
    the MCU row; a chip with an exact EBOOT_BOARD target keeps that."""
    p = HardwareProfile()
    p.mcu = "stm32f401"
    p.core = "cortex-m4"
    assert _resolve_eboot_board_dir("stm32f401", p) == "stm32f4"
    assert _resolve_eboot_board_dir("nrf52") == "nrf52"


def test_wrong_width_rows_dropped():
    """sifive_e (RV32) must not resolve to the 64-bit sifive_u board, and
    ultrasparc (sparc64 arch) must not resolve to the 32-bit sparc board.
    Both previously masked wrong-width rows that become real the moment an
    rv32 toolchain lands."""
    assert board_dir_for_mcu("sifive_e") is None
    assert board_dir_for_mcu("sifive_e7") is None
    assert board_dir_for_mcu("ultrasparc") is None
    assert board_dir_for_mcu("ultrasparc_t") == "sparc64"


def test_sdk_command_exits_nonzero_on_fallback_target():
    """`ebuild sdk --target <unsupported>` must exit 1 like the pipeline path
    (review 5111127987 finding 2): the same generator, two entry points, one
    definition of success."""
    from click.testing import CliRunner
    from ebuild.cli.commands import cli

    runner = CliRunner()
    with tempfile.TemporaryDirectory() as out:
        result = runner.invoke(cli, ["sdk", "--target", "nrf52840",
                                     "--output", out])
        assert result.exit_code != 0, "fallback SDK must not exit 0"
        assert "no cross-toolchain" in result.output, result.output


def test_sdk_command_succeeds_on_known_target():
    """`ebuild sdk --target nrf52` (a TARGET_ARCH key) still exits 0."""
    from click.testing import CliRunner
    from ebuild.cli.commands import cli

    runner = CliRunner()
    with tempfile.TemporaryDirectory() as out:
        result = runner.invoke(cli, ["sdk", "--target", "nrf52",
                                     "--output", out])
        assert result.exit_code == 0, result.output
        assert "SDK generated" in result.output, result.output


def test_mmu_class_rule_pinned():
    """at91sam9g25 (ARM926) and bcm2835 (ARM11) sit on opposite sides of the
    class split by rule: classic non-Cortex ARM -> mcu/bare-metal triplet,
    Cortex-A/ARM11 application cores -> sbc/hosted triplet. The comment on
    the ``arch == \"arm\"`` branch documents why; this pins the boundary so a
    refactor cannot silently flip a side."""
    a9 = HardwareProfile()
    a9.arch = "arm"
    a9.core = "arm926ej-s"
    a11 = HardwareProfile()
    a11.arch = "arm"
    a11.core = "arm1176jzf-s"
    ca9 = HardwareProfile()
    ca9.arch = "arm"
    ca9.core = "cortex-a9"
    assert _info_from_profile(a9)["class"] == "mcu"
    assert _info_from_profile(a9)["triplet"] == "arm-none-eabi"
    assert _info_from_profile(a11)["class"] == "sbc"
    assert _info_from_profile(a11)["triplet"] == "arm-linux-gnueabihf"
    assert _info_from_profile(ca9)["class"] == "sbc"
