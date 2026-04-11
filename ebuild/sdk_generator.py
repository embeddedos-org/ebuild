# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

import argparse
import json
import os

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


def get_eboot_board(target):
    return EBOOT_BOARD.get(target, "x86")


def generate_sdk(target, output_dir, hardware_file=None):
    info = get_target_info(target)
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
    with open(os.path.join(sdk_dir, "sdk-info.txt"), "w") as f:
        f.write("\n".join(si) + "\n")
    # manifest.json
    manifest = {
        "product": "eos-" + target,
        "target": {
            "name": target,
            "arch": arch,
            "cpu": info["cpu"],
            "triplet": triplet,
            "vendor": info["vendor"],
            "soc": info["soc"],
            "class": info["class"],
        },
        "network": {
            "default_ip": "192.168.1.100",
            "ebot_port": 8420,
        },
    }
    with open(os.path.join(output_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    # Generate eboot board config for this target
    eboot_board = get_eboot_board(target)
    eboot_dir = os.path.join(sdk_dir, "eboot")
    os.makedirs(eboot_dir, exist_ok=True)

    # eboot board config header
    eboot_cfg = []
    eboot_cfg.append("/* Auto-generated eBoot config for " + target + " */")
    eboot_cfg.append("#ifndef EBOOT_TARGET_CONFIG_H")
    eboot_cfg.append("#define EBOOT_TARGET_CONFIG_H")
    eboot_cfg.append("")
    eboot_cfg.append('#define EBOOT_TARGET_NAME     "' + target + '"')
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
    eboot_cmake.append("set(EBOOT_BOARD " + eboot_board + ")")
    eboot_cmake.append("set(EBOOT_ARCH " + arch + ")")
    eboot_cmake.append("set(EBOOT_CPU " + info["cpu"] + ")")
    if info["class"] == "mcu":
        eboot_cmake.append("set(EBOOT_BARE_METAL ON)")
    else:
        eboot_cmake.append("set(EBOOT_BARE_METAL OFF)")
    line = 'set(EBOOT_BOARD_DIR "${CMAKE_CURRENT_LIST_DIR}/../eboot/boards/'
    eboot_cmake.append(line + eboot_board + '")')
    with open(os.path.join(eboot_dir, "eboot_board.cmake"), "w") as f:
        f.write("\n".join(eboot_cmake) + "\n")

    # eboot linker script selection (for MCUs)
    if info["class"] == "mcu":
        ld = []
        ld.append("/* Auto-generated linker script for " + target + " */")
        ld.append("MEMORY {")
        if target == "stm32f4":
            ld.append("  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 1024K")
            ld.append("  SRAM  (rwx) : ORIGIN = 0x20000000, LENGTH = 128K")
        elif target == "stm32h7":
            ld.append("  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 2048K")
            ld.append("  DTCM  (rwx) : ORIGIN = 0x20000000, LENGTH = 128K")
            ld.append("  SRAM  (rwx) : ORIGIN = 0x24000000, LENGTH = 512K")
        elif target == "nrf52":
            ld.append("  FLASH (rx)  : ORIGIN = 0x00000000, LENGTH = 1024K")
            ld.append("  SRAM  (rwx) : ORIGIN = 0x20000000, LENGTH = 256K")
        elif target == "rp2040":
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

    print("  eBoot board: " + eboot_board + " (" + info["class"] + ")")

    print("EoS SDK generated for " + target)
    print("  Vendor:  " + info["vendor"] + " " + info["soc"])
    print("  Arch:    " + arch + " (" + info["cpu"] + ")")
    print("  Triplet: " + triplet)
    print("  Location: " + sdk_dir)
    return sdk_dir


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
