# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

import argparse
import json
import os
import re

# MCU family prefix -> eboot board directory name (Tier-1 source of truth;
# EosProjectGenerator imports it from here so the dependency points down).
MCU_TO_EBOOT_BOARD = {
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
        # --- TI ---
        "msp430": "msp430",
        "tms320f28": "c28x",
        "tms320c67": "c6000",
        "am335x_pru": "pru",
        # --- Renesas + Infineon ---
        "rl78": "rl78",
        "rx65": "rx",
        "rx72": "rx",
        "tc397": "tricore",
        "tc375": "tricore",
        "xc2267": "c166",
        # --- FPGA ---
        "microblaze": "microblaze",
        "nios2": "nios2",
        "mor1kx": "openrisc",
        "lm32": "lm32",
        # --- DSP ---
        "adsp_bf": "blackfin",
        "adsp_21": "sharc",
        "sdm845": "hexagon",
        "ceva_xm": "ceva",
        "hifi5": "xtensa_hifi",
        # --- Misc ---
        "arc_em": "arc",
        "stc89": "8051",
        "efm8": "8051",
        "esp32c3": "esp32c3",
        "esp32s3": "esp32s3",
        # --- Server/exotic ---
        "ultrasparc_t": "sparc64",
        "power9": "ppc64",
        "loongson": "loongarch",
        "pa87": "parisc",
        "itanium": "ia64",
        "alpha21": "alpha",
        "ibm_z": "s390",
        "etrax": "cris",
        "csr8675": "kalimba",
}


# Longest prefix first, computed once: shorter family rows (esp32)
# must not shadow their more specific parts (esp32c3), and no caller
# should re-sort the table per lookup.
_MCU_PREFIXES = sorted(MCU_TO_EBOOT_BOARD.items(), key=lambda kv: -len(kv[0]))


def board_dir_for_mcu(mcu):
    """Longest-prefix MCU -> eBoot board directory lookup (None on a miss).

    Public name (no leading underscore): shared across the module boundary by
    ``eos_project_generator``, so a rename must update that caller too.
    """
    mcu = (mcu or "").lower()
    for prefix, board in _MCU_PREFIXES:
        if mcu.startswith(prefix):
            return board
    return None


# Core-class board directories eBoot ships (generic ports shared by every
# chip of that core: cortex_m3, arm9, cortex_a76, ...). Frozen list read from
# the pinned eBoot revision in core/UPSTREAM.yaml at the time of writing —
# the generated SDK's ``EBOOT_BOARD_DIR`` is resolved against the eBoot tree
# the generated project pairs with (an eBoot clone), not against ebuild's
# vendored test snapshot, which carries only the 26 legacy boards.
_EBOOT_CORE_BOARDS = frozenset([
    "8051", "alpha", "arc", "arm11", "arm7tdmi", "arm9", "avr", "avr32",
    "blackfin", "c166", "c28x", "c6000", "ceva", "cortex_a15", "cortex_a35",
    "cortex_a5", "cortex_a55", "cortex_a76", "cortex_a9", "cortex_m0",
    "cortex_m0plus", "cortex_m23", "cortex_m3", "cortex_m33", "cortex_m55",
    "cortex_m85", "cortex_r4", "cortex_r5", "cortex_r52", "cris", "dspic",
    "esp32c3", "esp32s3", "hexagon", "kalimba", "mips64", "msp430",
    "nrf52", "openrisc", "parisc", "pic16", "pic18", "pic24", "pic32",
    "ppc64", "pru", "riscv32", "rl78", "rx", "s390", "sharc", "sparc64",
    "stm32mp1", "strongarm", "tricore", "v850", "xscale", "xtensa_hifi",
])


def _normalise_core(core):
    """Canonical core spelling for board-dir matching: lowercase, no
    separators. ``Cortex-A9`` / ``cortex_a9`` / ``cortexa9`` all become
    ``cortexa9``, so the analyzer's hyphen spellings and the on-disk
    underscore spellings compare equal."""
    return re.sub(r"[^a-z0-9]", "", (core or "").lower())


# Core-name normalisation hits for the microarch suffixes the analyzer uses:
# arm926ej-s is an ARM9, arm1176jzf-s is an ARM11, cortex-r4f is a Cortex-R4.
_CORE_ABBREV = (
    ("arm926ej", "arm9"),
    ("arm1176jzf", "arm11"),
    ("cortexr4f", "cortexr4"),
    ("cortexm0", "cortexm0"),   # keep m0 distinct from m0plus below
    ("cortexr5f", "cortexr5"),
)


def board_dir_for_core(core):
    """Core-class board lookup against the boards eBoot actually ships
    (None on a miss). Separator-insensitive: ``cortex-m3`` matches the
    upstream ``cortex_m3``; ``arm926ej-s`` matches ``arm9``."""
    norm = _normalise_core(core)
    if not norm:
        return None
    # Exact normalised match first (cortex-m3 == cortex_m3), then a unique
    # normalised prefix (arm926ej-s -> arm9); ambiguous prefixes miss.
    for abbrev, target in _CORE_ABBREV:
        if norm.startswith(abbrev) and abbrev != target:
            norm = target
            break
    for d in _EBOOT_CORE_BOARDS:
        if _normalise_core(d) == norm:
            return d
    return None

TARGET_ARCH = {
    'stm32f4': {
        'arch': 'arm',
        'triplet': 'arm-none-eabi',
        'cpu': 'cortex-m4',
        'vendor': 'ST',
        'soc': 'STM32F407',
        'class': 'mcu',
    },
    'stm32h7': {
        'arch': 'arm',
        'triplet': 'arm-none-eabi',
        'cpu': 'cortex-m7',
        'vendor': 'ST',
        'soc': 'STM32H743',
        'class': 'mcu',
    },
    'nrf52': {
        'arch': 'arm',
        'triplet': 'arm-none-eabi',
        'cpu': 'cortex-m4',
        'vendor': 'Nordic',
        'soc': 'nRF52840',
        'class': 'mcu',
    },
    'rp2040': {
        'arch': 'arm',
        'triplet': 'arm-none-eabi',
        'cpu': 'cortex-m0plus',
        'vendor': 'RPi',
        'soc': 'RP2040',
        'class': 'mcu',
    },
    'raspi3': {
        'arch': 'aarch64',
        'triplet': 'aarch64-linux-gnu',
        'cpu': 'cortex-a53',
        'vendor': 'Broadcom',
        'soc': 'BCM2837',
        'class': 'sbc',
    },
    'raspi4': {
        'arch': 'aarch64',
        'triplet': 'aarch64-linux-gnu',
        'cpu': 'cortex-a72',
        'vendor': 'Broadcom',
        'soc': 'BCM2711',
        'class': 'sbc',
    },
    'imx8m': {
        'arch': 'aarch64',
        'triplet': 'aarch64-linux-gnu',
        'cpu': 'cortex-a53',
        'vendor': 'NXP',
        'soc': 'i.MX8M',
        'class': 'soc',
    },
    'am64x': {
        'arch': 'aarch64',
        'triplet': 'aarch64-linux-gnu',
        'cpu': 'cortex-a53',
        'vendor': 'TI',
        'soc': 'AM6442',
        'class': 'soc',
    },
    'vexpress': {
        'arch': 'arm',
        'triplet': 'arm-linux-gnueabihf',
        'cpu': 'cortex-a15',
        'vendor': 'ARM',
        'soc': 'VExpress',
        'class': 'devboard',
    },
    'riscv_virt': {
        'arch': 'riscv64',
        'triplet': 'riscv64-linux-gnu',
        'cpu': 'rv64gc',
        'vendor': 'QEMU',
        'soc': 'virt',
        'class': 'virtual',
    },
    'sifive_u': {
        'arch': 'riscv64',
        'triplet': 'riscv64-linux-gnu',
        'cpu': 'u74',
        'vendor': 'SiFive',
        'soc': 'FU740',
        'class': 'sbc',
    },
    'malta': {
        'arch': 'mipsel',
        'triplet': 'mipsel-linux-gnu',
        'cpu': '24kf',
        'vendor': 'MIPS',
        'soc': 'Malta',
        'class': 'devboard',
    },
    'x86_64': {
        'arch': 'x86_64',
        'triplet': 'x86_64-linux-gnu',
        'cpu': 'generic',
        'vendor': 'Generic',
        'soc': 'x86_64',
        'class': 'pc',
    },
    'qemu_virt': {
        'arch': 'x86_64',
        'triplet': 'x86_64-linux-gnu',
        'cpu': 'generic',
        'vendor': 'QEMU',
        'soc': 'q35',
        'class': 'virtual',
    },
}


def get_target_info(target):
    return TARGET_ARCH.get(target, TARGET_ARCH["x86_64"])


# Map ebuild targets to eboot board directories
EBOOT_BOARD = {
    "stm32f4":    "stm32f4",
    "stm32h7":    "stm32h7",
    "nrf52":      "nrf52",
    "rp2040":     "samd51",
    "raspi3":     "qemu_arm64",
    "raspi4":     "rpi4",
    "imx8m":      "imx8m",
    "am64x":      "am64x",
    "vexpress":   "qemu_arm64",
    "riscv_virt": "riscv64_virt",
    "sifive_u":   "sifive_u",
    "malta":      "mips",
    "x86_64":     "x86_64_efi",
    "qemu_virt":  "x86",
}



def _resolve_eboot_board_dir(target, profile=None):
    """Resolve the eBoot board *directory* for a target.

    Three-stage lookup, in order:
      1. Exact target-name match in EBOOT_BOARD (the TARGET_ARCH target names
         eBoot ships a board for, e.g. ``nrf52``, ``stm32f4``, ``raspi4``).
      2. MCU-prefix match against MCU_TO_EBOOT_BOARD for a detected chip whose
         board directory name the analyzer knows but the target table does not
         (e.g. profile mcu ``nrf52840`` -> ``nrf52``).
      3. Core-name match against the board list eBoot actually ships: eBoot
         ports generic *core-class* boards (``cortex_m3``, ``arm9``, ...), so a
         chip with no chip-named row still gets the real board its core uses
         (``stm32f103`` -> ``cortex_m3``). Normalised: ``cortex-a9``/``cortexa9``
         -> ``cortex_a9``, and separator spellings generally are matched by
         stripping separators before comparing.

    Returns the board directory name, or None when no stage matches. The
    caller then fails closed (FATAL_ERROR) rather than inventing a board.
    Stage 3 is last so no currently-resolving target changes.
    """
    if target in EBOOT_BOARD:
        return EBOOT_BOARD[target]
    if profile is not None:
        board = board_dir_for_mcu(getattr(profile, "mcu", None))
        if board is not None:
            return board
        return board_dir_for_core(getattr(profile, "core", None))
    return None


def _info_from_profile(profile):
    """Derive a TARGET_ARCH-shaped info dict from a detected profile.

    The architecture is tested before the core, so 64-bit ARM (``arch`` =
    ``aarch64``/``arm64``) always wins over a Cortex-A core string, while
    32-bit Cortex-A / ARM11 parts (Linux-class, ``arch`` = ``arm``) still get
    ``arm-linux-gnueabihf`` and ``class: sbc`` rather than the bare-metal
    ``arm-none-eabi``. Only architectures the SDK ships a toolchain for (ARM
    Cortex-M/R, classic ARM7/ARM9/StrongARM/XScale, Cortex-A, AArch64, RISC-V)
    return a dict; everything else returns None so the caller keeps the
    original x86_64 fallback instead of
    inventing a toolchain we do not have. The RISC-V width guard covers both
    the exact ``riscv32`` arch and alternate spellings (``riscv32imac``) plus
    core-only rows (``rv32imac``), so a 32-bit part can never fall through to a
    64-bit toolchain.
    """
    arch = (getattr(profile, "arch", None) or "").lower()
    core = (getattr(profile, "core", None) or "").lower()
    vendor = getattr(profile, "vendor", "") or "Generic"
    if "cortex-m" in core or "cortex-r" in core:
        return {"arch": "arm", "triplet": "arm-none-eabi",
                "cpu": core or "cortex-m4", "vendor": vendor,
                "soc": getattr(profile, "mcu_family", "") or "MCU", "class": "mcu"}
    if arch in ("aarch64", "arm64"):
        return {"arch": "aarch64", "triplet": "aarch64-linux-gnu",
                "cpu": core or "cortex-a53", "vendor": vendor,
                "soc": getattr(profile, "mcu_family", "") or "SBC", "class": "sbc"}
    if "cortex-a" in core or "arm11" in core:
        return {"arch": "arm", "triplet": "arm-linux-gnueabihf",
                "cpu": core or "cortex-a53", "vendor": vendor,
                "soc": getattr(profile, "mcu_family", "") or "SBC", "class": "sbc"}
    if arch == "arm":
        # Classic ARM (ARM7TDMI / ARM9 / StrongARM / XScale): no Cortex core
        # string. Class rule: ``class`` describes the EoS payload tier, not the
        # bootloader — eBoot itself always builds bare-metal, so the loader
        # never links against a *-linux-gnueabihf sysroot regardless of class.
        # These parts have no MMU-capable Linux story in the shipped boards
        # (their eBoot ports are direct-boot), so they land on arm-none-eabi +
        # class: mcu, while Cortex-A application cores keep the hosted triplet
        # + class: sbc (Linux payload) their boards are built for.
        return {"arch": "arm", "triplet": "arm-none-eabi",
                "cpu": core or "arm7tdmi", "vendor": vendor,
                "soc": getattr(profile, "mcu_family", "") or "MCU", "class": "mcu"}
    # riscv32 has no toolchain in the repo (only riscv64-* ship), so treat it
    # like xtensa/MIPS: return None and let the caller keep the honest x86_64
    # fallback rather than inventing a 64-bit toolchain for 32-bit silicon.
    # Guards both the exact "riscv32" arch and alternate spellings ("riscv32imac")
    # plus core-only rows ("rv32imac").
    if arch.startswith("riscv32") or "rv32" in core:
        return None
    if "riscv" in arch:
        return {"arch": "riscv64", "triplet": "riscv64-linux-gnu",
                "cpu": core or "rv64gc", "vendor": vendor,
                "soc": getattr(profile, "mcu_family", "") or "RISC-V", "class": "sbc"}
    return None


def generate_sdk(target, output_dir, hardware_file=None):
    info = get_target_info(target)
    sdk_dir, _, _ = _write_sdk_files(target, info, output_dir,
                                     toolchain_ok=target in TARGET_ARCH)
    return sdk_dir


def _write_sdk_files(target, info, output_dir, profile=None, toolchain_ok=True):
    """Shared SDK file writer used by both name- and profile-based generation.

    ``target`` is the board/MCU string and names the SDK directory
    (``eos-sdk-<target>``); ``info`` drives the arch, toolchain triplet, eboot
    board, and linker script. The two are independent so a detected chip such
    as ``nrf52840`` keeps its directory name while inheriting the ``nrf52``
    toolchain definition. ``profile`` (optional) lets a detected MCU whose
    board eBoot ships resolve its eboot board via MCU prefix even when the
    target name is not an EBOOT_BOARD key. ``toolchain_ok`` (default True) must
    be False when ``info`` is a fallback rather than a real toolchain: a
    resolved board directory is then dropped so the output can never pair a
    real board with a fallback arch and look valid.
    """
    sdk_dir = os.path.join(output_dir, "eos-sdk-" + target)
    for d in ["sysroot/usr/include", "sysroot/usr/lib", "sysroot/usr/lib/pkgconfig"]:
        os.makedirs(os.path.join(sdk_dir, d), exist_ok=True)
    triplet = info["triplet"]
    arch = info["arch"]
    # toolchain.cmake — NO f-strings, use concatenation
    tc = []
    tc.append("# EoS SDK Toolchain for " + triplet)
    tc.append("set(CMAKE_SYSTEM_NAME Linux)")
    tc.append("set(CMAKE_SYSTEM_PROCESSOR " + arch + ")")
    tc.append("set(CMAKE_C_COMPILER " + triplet + "-gcc)")
    tc.append("set(CMAKE_CXX_COMPILER " + triplet + "-g++)")
    tc.append("set(CMAKE_SYSROOT ${CMAKE_CURRENT_LIST_DIR}/sysroot)")
    tc.append("set(CMAKE_FIND_ROOT_PATH ${CMAKE_SYSROOT})")
    tc.append("set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)")
    tc.append("set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)")
    tc.append("set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)")
    with open(os.path.join(sdk_dir, "toolchain.cmake"), "w") as f:
        f.write("\n".join(tc) + "\n")
    # environment-setup — NO f-strings, use shell $VAR syntax in raw strings
    env = []
    env.append("#!/bin/sh")
    env.append("# EoS SDK Environment for " + target)
    abs_sdk_dir = os.path.abspath(sdk_dir).replace("\\", "/")
    env.append(f'export EOS_SDK_ROOT="{abs_sdk_dir}"')
    env.append('export EOS_SDK_SYSROOT="$EOS_SDK_ROOT/sysroot"')
    env.append('export EOS_SDK_TARGET="' + target + '"')
    env.append('export EOS_SDK_ARCH="' + arch + '"')
    env.append('export CC="' + triplet + '-gcc"')
    env.append('export CXX="' + triplet + '-g++"')
    env.append('export CMAKE_TOOLCHAIN_FILE="$EOS_SDK_ROOT/toolchain.cmake"')
    env.append('export PKG_CONFIG_PATH="$EOS_SDK_SYSROOT/usr/lib/pkgconfig"')
    msg = f'echo "EoS SDK for {target} ({info["vendor"]} {info["soc"]}) initialized"'
    env.append(msg)
    if not toolchain_ok:
        # Fail-loud on the primary consumer surface: environment-setup exports
        # CMAKE_TOOLCHAIN_FILE, which never includes eboot_board.cmake — without
        # this echo a sourced env would silently hand out a desktop compiler.
        env.append('echo "WARNING: unsupported target ' + target + ' - no toolchain '
                   'ships for this chip; see eboot/eboot_board.cmake (ebuild sdk --list)"')
    with open(os.path.join(sdk_dir, "environment-setup"), "w") as f:
        f.write("\n".join(env) + "\n")
    if os.name != "nt":
        os.chmod(os.path.join(sdk_dir, "environment-setup"), 0o755)
    # Generate Windows batch equivalent
    bat = []
    bat.append("@echo off")
    bat.append("REM EoS SDK Environment for " + target)
    bat.append('set "EOS_SDK_ROOT=' + os.path.abspath(sdk_dir).replace("/", "\\") + '"')
    bat.append('set "EOS_SDK_SYSROOT=%EOS_SDK_ROOT%\\sysroot"')
    bat.append('set "EOS_SDK_TARGET=' + target + '"')
    bat.append('set "EOS_SDK_ARCH=' + arch + '"')
    bat.append('set "CC=' + triplet + '-gcc"')
    bat.append('set "CXX=' + triplet + '-g++"')
    bat.append('set "CMAKE_TOOLCHAIN_FILE=%EOS_SDK_ROOT%\\toolchain.cmake"')
    bat.append('set "PKG_CONFIG_PATH=%EOS_SDK_SYSROOT%\\usr\\lib\\pkgconfig"')
    bat.append(f'echo EoS SDK for {target} ({info["vendor"]} {info["soc"]}) initialized')
    if not toolchain_ok:
        bat.append('echo WARNING: unsupported target ' + target + ' - no toolchain '
                   'ships for this chip (ebuild sdk --list)')
    with open(os.path.join(sdk_dir, "environment-setup.bat"), "w") as f:
        f.write("\r\n".join(bat) + "\r\n")
    # sdk-info.txt
    si = []
    si.append("EoS SDK")
    si.append("Target:  " + target)
    si.append("Arch:    " + arch)
    si.append("CPU:     " + info["cpu"])
    si.append("Triplet: " + triplet)
    si.append("Vendor:  " + info["vendor"])
    si.append("SoC:     " + info["soc"])
    si.append("Class:   " + info["class"])
    if not toolchain_ok:
        si.append("Toolchain:  fallback (unsupported target " + target + ")")
    with open(os.path.join(sdk_dir, "sdk-info.txt"), "w") as f:
        f.write("\n".join(si) + "\n")
    # manifest.json
    target_entry = {
        "name": target,
        "arch": arch,
        "cpu": info["cpu"],
        "triplet": triplet,
        "vendor": info["vendor"],
        "soc": info["soc"],
        "class": info["class"],
    }
    if not toolchain_ok:
        target_entry["toolchain"] = "fallback"
    manifest = {
        "product": "eos-" + target,
        "target": target_entry,
        "network": {
            "default_ip": "192.168.1.100",
            "ebot_port": 8420,
        },
    }
    with open(os.path.join(output_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    # Generate eboot board config for this target. Derive the board via the
    # unified resolver (exact target-name match, then MCU-prefix match against
    # the Tier-1 table). A detected chip the board table knows by MCU prefix
    # (e.g. nrf52840 -> nrf52) gets its real board directory; the per-chip
    # MEMORY block below is still gated on an exact target match. A toolchain
    # miss drops the board entirely so the FATAL_ERROR block fires.
    eboot_board = _resolve_eboot_board_dir(target, profile)
    if not toolchain_ok:
        # Fail closed on a toolchain miss: a resolved board directory must
        # never be paired with a fallback (x86_64) arch — the two halves would
        # contradict each other and the file would look valid. Drop the board
        # so the FATAL_ERROR block below fires.
        eboot_board = None
    eboot_dir = os.path.join(sdk_dir, "eboot")
    os.makedirs(eboot_dir, exist_ok=True)

    # eboot board config header
    eboot_cfg = []
    eboot_cfg.append("/* Auto-generated eBoot config for " + target + " */")
    eboot_cfg.append("#ifndef EBOOT_TARGET_CONFIG_H")
    eboot_cfg.append("#define EBOOT_TARGET_CONFIG_H")
    eboot_cfg.append("")
    eboot_cfg.append('#define EBOOT_TARGET_NAME     "' + target + '"')
    if eboot_board is not None:
        eboot_cfg.append('#define EBOOT_BOARD_NAME      "' + eboot_board + '"')
    eboot_cfg.append('#define EBOOT_TARGET_ARCH     "' + arch + '"')
    eboot_cfg.append('#define EBOOT_TARGET_CPU      "' + info["cpu"] + '"')
    eboot_cfg.append('#define EBOOT_TARGET_VENDOR   "' + info["vendor"] + '"')
    eboot_cfg.append('#define EBOOT_TARGET_SOC      "' + info["soc"] + '"')
    if info["class"] == "mcu":
        eboot_cfg.append("#define EBOOT_BARE_METAL      1")
        eboot_cfg.append("#define EBOOT_HAS_MMU         0")
        eboot_cfg.append("#define EBOOT_BOOT_MODE       EBOOT_MODE_DIRECT")
    else:
        eboot_cfg.append("#define EBOOT_BARE_METAL      0")
        eboot_cfg.append("#define EBOOT_HAS_MMU         1")
        eboot_cfg.append("#define EBOOT_BOOT_MODE       EBOOT_MODE_UBOOT")
    eboot_cfg.append("")
    eboot_cfg.append("#endif /* EBOOT_TARGET_CONFIG_H */")
    with open(os.path.join(eboot_dir, "eboot_target_config.h"), "w") as f:
        f.write("\n".join(eboot_cfg) + "\n")

    # eboot CMake board selection
    eboot_cmake = []
    eboot_cmake.append("# Auto-generated eBoot board selection for " + target)
    eboot_cmake.append("set(EBOOT_TARGET " + target + ")")
    if eboot_board is not None:
        eboot_cmake.append("set(EBOOT_BOARD " + eboot_board + ")")
    eboot_cmake.append("set(EBOOT_ARCH " + arch + ")")
    eboot_cmake.append("set(EBOOT_CPU " + info["cpu"] + ")")
    if info["class"] == "mcu":
        eboot_cmake.append("set(EBOOT_BARE_METAL ON)")
    else:
        eboot_cmake.append("set(EBOOT_BARE_METAL OFF)")
    if eboot_board is not None:
        line = 'set(EBOOT_BOARD_DIR "${CMAKE_CURRENT_LIST_DIR}/../eboot/boards/'
        eboot_cmake.append(line + eboot_board + '")')
    with open(os.path.join(eboot_dir, "eboot_board.cmake"), "w") as f:
        f.write("\n".join(eboot_cmake) + "\n")

    # eboot linker script selection (for MCUs). Only emit a per-chip linker
    # script on an EXACT target match: the MEMORY figures below are per-part,
    # not per-family, so a family board dir (e.g. stm32f401 -> stm32f4) must
    # never select a sibling's memory map. Otherwise the linker would place
    # .text past physical flash and _estack above physical SRAM.
    linker_key = target if target in TARGET_ARCH else None
    if info["class"] == "mcu" and linker_key is not None:
        ld = []
        ld.append("/* Auto-generated linker script for " + target + " */")
        ld.append("MEMORY {")
        if linker_key == "stm32f4":
            ld.append("  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 1024K")
            ld.append("  SRAM  (rwx) : ORIGIN = 0x20000000, LENGTH = 128K")
        elif linker_key == "stm32h7":
            ld.append("  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 2048K")
            ld.append("  DTCM  (rwx) : ORIGIN = 0x20000000, LENGTH = 128K")
            ld.append("  SRAM  (rwx) : ORIGIN = 0x24000000, LENGTH = 512K")
        elif linker_key == "nrf52":
            ld.append("  FLASH (rx)  : ORIGIN = 0x00000000, LENGTH = 1024K")
            ld.append("  SRAM  (rwx) : ORIGIN = 0x20000000, LENGTH = 256K")
        elif linker_key == "rp2040":
            ld.append("  FLASH (rx)  : ORIGIN = 0x10000000, LENGTH = 2048K")
            ld.append("  SRAM  (rwx) : ORIGIN = 0x20000000, LENGTH = 264K")
        else:
            ld.append("  FLASH (rx)  : ORIGIN = 0x00000000, LENGTH = 512K")
            ld.append("  SRAM  (rwx) : ORIGIN = 0x20000000, LENGTH = 64K")
        ld.append("}")
        ld.append("")
        ld.append("SECTIONS {")
        ld.append("  .isr_vector : { KEEP(*(.isr_vector)) } > FLASH")
        ld.append("  .text :       { *(.text*) } > FLASH")
        ld.append("  .rodata :     { *(.rodata*) } > FLASH")
        ld.append("  .data :       { *(.data*) } > SRAM AT> FLASH")
        ld.append("  .bss :        { *(.bss*) *(COMMON) } > SRAM")
        ld.append("  ._stack :     { . = ALIGN(8); _estack = .; } > SRAM")
        ld.append("}")
        with open(os.path.join(eboot_dir, "eboot_" + target + ".ld"), "w") as f:
            f.write("\n".join(ld) + "\n")
    if eboot_board is None:
        # Fail closed (Master Design §9.2): instead of writing nothing — which
        # CMake would silently expand to an empty/wrong EBOOT_BOARD_DIR — append
        # a FATAL_ERROR so any consumer that includes this file errors by name.
        # Covers both a board miss and a toolchain miss (whose board was dropped
        # above): an unsupported target gets an actionable diagnostic, never a
        # half-valid file. The two diagnostics say which half missed: a
        # toolchain miss fell back to the host compiler (name it), a board miss
        # has a good toolchain but no board for this chip (name the chip, not
        # `ebuild sdk --list`, which lists TARGET_ARCH targets and can never
        # contain a detected MCU like stm32f103).
        with open(os.path.join(eboot_dir, "eboot_board.cmake"), "a") as f:
            if not toolchain_ok:
                f.write('message(FATAL_ERROR "eos-sdk-' + target + ': no cross-toolchain '
                        'ships for ' + target + '; the SDK fell back to the host '
                        'x86_64 compiler. Run `ebuild sdk --list` for supported targets.")\n')
            else:
                f.write('message(FATAL_ERROR "eos-sdk-' + target + ': eBoot ships no '
                        'board port for ' + target + ' (toolchain ' + triplet + ' is '
                        'correct). Check eBoot boards/ for a port covering this chip.")\n')
        if not toolchain_ok:
            print("  [warn] no cross-toolchain ships for " + target + ": fell back to the "
                  "host x86_64 compiler; FATAL_ERROR written, no linker script. "
                  "Run `ebuild sdk --list`.")
        else:
            print("  [warn] eBoot ships no board port for " + target + " (toolchain " +
                  triplet + " is correct): FATAL_ERROR written, no linker script. "
                  "Check eBoot boards/ for a port covering this chip.")
    elif info["class"] == "mcu" and linker_key is None:
        # Board resolved (family-wide directory) but no memory map exists for
        # this exact part: say so explicitly instead of going silent.
        print("  [warn] no per-chip linker script for " + target +
              ": eBoot ships no memory map for this exact part. "
              "Run `ebuild sdk --list` for supported targets.")

    print("  eBoot board: " + (eboot_board if eboot_board is not None else "none (unmapped)") + " (" + info["class"] + ")")

    print("EoS SDK generated for " + target)
    print("  Vendor:  " + info["vendor"] + " " + info["soc"])
    print("  Arch:    " + arch + " (" + info["cpu"] + ")")
    print("  Triplet: " + triplet)
    print("  Location: " + sdk_dir)
    return sdk_dir, toolchain_ok, eboot_board


def generate_sdk_from_profile(profile, output_dir, target=None):
    """Generate an EoS SDK from a detected ``HardwareProfile``.

    The directory/target name is taken from the caller (the board string the
    pipeline resolved), not from ``profile.mcu``: several documented targets
    (``raspi4``, ``vexpress``, ``riscv_virt``, ``malta``, ``qemu_virt``,
    ``raspi3``) have no ``mcu`` in the analyzer, so deriving the name from it
    produced an empty ``eos-sdk-`` directory. Priority:

    1. If the resolved target is a known ``TARGET_ARCH`` key, use that
       canonical mapping exactly as the legacy ``generate_sdk`` would. This
       keeps every supported board byte-identical to the pre-fix behavior,
       including its eboot board.
    2. Otherwise derive the toolchain from the detected profile (core, arch,
       vendor, ``EOS_ENABLE_*`` flags) so a chip the analyzer identified but
       the name table does not know (e.g. ``nrf52840``) gets the right
       toolchain instead of the silent x86_64 fallback. Chips the SDK has no
       toolchain for keep the honest x86_64 fallback.

    Returns ``(sdk_dir, toolchain_ok, eboot_board)`` so callers can fail the
    pipeline on an unsupported target instead of logging success.
    """
    target = (target or getattr(profile, "mcu", "") or "").lower() or "unknown"
    if target in TARGET_ARCH:
        info = get_target_info(target)
        toolchain_ok = True
    else:
        info = _info_from_profile(profile)
        toolchain_ok = info is not None
        if info is None:
            info = get_target_info(target)
    return _write_sdk_files(target, info, output_dir, profile=profile,
                            toolchain_ok=toolchain_ok)


def list_targets():
    print("Supported EoS SDK targets:\n")
    header = "  %-15s %-10s %-10s %-12s %-15s %s"
    print(header % ("Target", "Arch", "Vendor", "SoC", "CPU", "Class"))
    print("  " + "-"*15 + " " + "-"*10 + " " + "-"*10 + " " + "-"*12 + " " + "-"*15 + " " + "-"*10)
    for name in sorted(TARGET_ARCH.keys()):
        i = TARGET_ARCH[name]
        print("  %-15s %-10s %-10s %-12s %-15s %s" % (name, i["arch"], i["vendor"], i["soc"], i["cpu"], i["class"]))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="EoS SDK Generator")
    p.add_argument("--target", default="x86_64")
    p.add_argument("--output", default="build")
    p.add_argument("--hardware-file", default=None)
    p.add_argument("--list", action="store_true")
    a = p.parse_args()
    if a.list:
        list_targets()
    else:
        generate_sdk(a.target, a.output, a.hardware_file)
