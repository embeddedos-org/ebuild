cmake_minimum_required(VERSION 3.15)
project(eBootloader
    VERSION 0.4.0
    LANGUAGES C
    DESCRIPTION "Multi-platform modular bootloader with RTOS support"
)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

if(MSVC)
    add_compile_definitions(_CRT_SECURE_NO_WARNINGS)
endif()

# ====================================================================
# Options
# ====================================================================
set(EBLDR_BOARD "none" CACHE STRING
    "Target board to build (requires cross-compiler). Options: \
stm32f4 | stm32h7 | nrf52 | rpi4 | riscv64_virt | esp32 | x86_64_efi | \
imx8m | am64x | samd51 | sifive_u | cortex_r5 | none")

option(EBLDR_BUILD_TESTS "Build unit tests (native only)" OFF)

set(EBLDR_INCLUDE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/include)

# ====================================================================
# Compiler flags
# ====================================================================
if(CMAKE_CROSSCOMPILING)
    add_compile_options(-Wall -Wextra -Os -ffunction-sections -fdata-sections -fno-common)
    add_link_options(-Wl,--gc-sections)
elseif(MSVC)
    add_compile_options(/W3)
elseif(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-Wall -Wextra)
endif()

# ====================================================================
# Core Libraries — platform-agnostic, always built
# ====================================================================
# These contain zero architecture-specific code (no inline asm,
# no memory-mapped I/O). They compile on any host: Windows, Linux, Mac.

# ---- HAL dispatch + board registry ----
add_library(eboot_hal STATIC
    hal/hal_core.c
    hal/board_registry.c
)
target_include_directories(eboot_hal PUBLIC ${EBLDR_INCLUDE_DIR})

# ---- Core boot logic ----
add_library(eboot_core STATIC
    core/bootctl.c
    core/image_verify.c
    core/slot_manager.c
    core/boot_policy.c
    core/recovery.c
    core/fw_services.c
    core/fw_update.c
    core/fw_transport_uart.c
    core/rtos_boot.c
    core/rtos_params.c
    core/boot_menu.c
    core/device_table.c
    core/runtime_services.c
    core/crypto_boot.c
    core/multicore.c
    core/board_config.c
    core/dram_init.c
    core/pci_enum.c
    core/storage.c
    core/power_init.c
    core/clock_init.c
    core/mpu_boot.c
    core/ecc_scrub.c
    core/bmc_handoff.c
    core/os_adapter.c
)
target_include_directories(eboot_core PUBLIC ${EBLDR_INCLUDE_DIR})
target_link_libraries(eboot_core PUBLIC eboot_hal)

# ---- Stage-1 boot manager ----
add_library(eboot_stage1 STATIC
    stage1/main.c
    stage1/boot_scan.c
    stage1/boot_select.c
    stage1/boot_log.c
    stage1/jump_app.c
)
target_include_directories(eboot_stage1 PUBLIC ${EBLDR_INCLUDE_DIR})
target_link_libraries(eboot_stage1 PUBLIC eboot_core)

# ====================================================================
# Board Port — architecture-specific, cross-compilation only
# ====================================================================
# Board ports contain MMIO register access, inline assembly, and
# linker scripts specific to their target architecture. They are
# compiled ONLY when a matching cross-compiler is used.
#
# Usage:
#   cmake -B build -DEBLDR_BOARD=stm32f4 \
#     -DCMAKE_TOOLCHAIN_FILE=toolchains/arm-none-eabi.cmake
#
# Native builds (no EBLDR_BOARD or EBLDR_BOARD=none) build only
# the core libraries — sufficient for unit tests and host-side tools.

macro(eboot_add_board BOARD_NAME BOARD_SRC BOARD_DIR)
    add_library(board_${BOARD_NAME} STATIC ${BOARD_SRC})
    target_include_directories(board_${BOARD_NAME} PUBLIC
        ${EBLDR_INCLUDE_DIR}
        ${CMAKE_CURRENT_SOURCE_DIR}/${BOARD_DIR}
    )
    target_link_libraries(board_${BOARD_NAME} PUBLIC eboot_hal)
    message(STATUS "  Board port: ${BOARD_NAME}")
endmacro()

if(NOT EBLDR_BOARD STREQUAL "none")
    # Build the selected board port
    if(EBLDR_BOARD STREQUAL "stm32f4")
        eboot_add_board(stm32f4 boards/stm32f4/board_stm32f4.c boards/stm32f4)
    elseif(EBLDR_BOARD STREQUAL "stm32h7")
        eboot_add_board(stm32h7 boards/stm32h7/board_stm32h7.c boards/stm32h7)
    elseif(EBLDR_BOARD STREQUAL "nrf52")
        eboot_add_board(nrf52 boards/nrf52/board_nrf52.c boards/nrf52)
    elseif(EBLDR_BOARD STREQUAL "rpi4")
        eboot_add_board(rpi4 boards/rpi4/board_rpi4.c boards/rpi4)
    elseif(EBLDR_BOARD STREQUAL "riscv64_virt")
        eboot_add_board(riscv64_virt boards/riscv64_virt/board_riscv64_virt.c boards/riscv64_virt)
    elseif(EBLDR_BOARD STREQUAL "esp32")
        eboot_add_board(esp32 boards/esp32/board_esp32.c boards/esp32)
    elseif(EBLDR_BOARD STREQUAL "x86_64_efi")
        eboot_add_board(x86_64_efi boards/x86_64_efi/board_x86_64_efi.c boards/x86_64_efi)
    elseif(EBLDR_BOARD STREQUAL "imx8m")
        eboot_add_board(imx8m boards/imx8m/board_imx8m.c boards/imx8m)
    elseif(EBLDR_BOARD STREQUAL "am64x")
        eboot_add_board(am64x boards/am64x/board_am64x.c boards/am64x)
    elseif(EBLDR_BOARD STREQUAL "samd51")
        eboot_add_board(samd51 boards/samd51/board_samd51.c boards/samd51)
    elseif(EBLDR_BOARD STREQUAL "sifive_u")
        eboot_add_board(sifive_u boards/sifive_u/board_sifive_u.c boards/sifive_u)
    elseif(EBLDR_BOARD STREQUAL "strongarm")
        eboot_add_board(strongarm boards/strongarm/board_strongarm.c boards/strongarm)
    elseif(EBLDR_BOARD STREQUAL "xscale")
        eboot_add_board(xscale boards/xscale/board_xscale.c boards/xscale)
    elseif(EBLDR_BOARD STREQUAL "frv")
        eboot_add_board(frv boards/frv/board_frv.c boards/frv)
    elseif(EBLDR_BOARD STREQUAL "sh4")
        eboot_add_board(sh4 boards/sh4/board_sh4.c boards/sh4)
    elseif(EBLDR_BOARD STREQUAL "h8300")
        eboot_add_board(h8300 boards/h8300/board_h8300.c boards/h8300)
    elseif(EBLDR_BOARD STREQUAL "x86")
        eboot_add_board(x86 boards/x86/board_x86.c boards/x86)
    elseif(EBLDR_BOARD STREQUAL "mips")
        eboot_add_board(mips boards/mips/board_mips.c boards/mips)
    elseif(EBLDR_BOARD STREQUAL "mn103")
        eboot_add_board(mn103 boards/mn103/board_mn103.c boards/mn103)
    elseif(EBLDR_BOARD STREQUAL "powerpc")
        eboot_add_board(powerpc boards/powerpc/board_powerpc.c boards/powerpc)
    elseif(EBLDR_BOARD STREQUAL "m68k")
        eboot_add_board(m68k boards/m68k/board_m68k.c boards/m68k)
    elseif(EBLDR_BOARD STREQUAL "v850")
        eboot_add_board(v850 boards/v850/board_v850.c boards/v850)
    elseif(EBLDR_BOARD STREQUAL "sparc")
        eboot_add_board(sparc boards/sparc/board_sparc.c boards/sparc)
    elseif(EBLDR_BOARD STREQUAL "stm32mp1")
        eboot_add_board(stm32mp1 boards/stm32mp1/board_stm32mp1.c boards/stm32mp1)
    elseif(EBLDR_BOARD STREQUAL "qemu_arm64")
        eboot_add_board(qemu_arm64 boards/qemu_arm64/board_qemu_arm64.c boards/qemu_arm64)
    elseif(EBLDR_BOARD STREQUAL "cortex_r5")
        eboot_add_board(cortex_r5 boards/cortex_r5/board_cortex_r5.c boards/cortex_r5)
    else()
        message(FATAL_ERROR "Unknown board: ${EBLDR_BOARD}. \
Available: stm32f4 stm32h7 nrf52 samd51 rpi4 imx8m am64x stm32mp1 qemu_arm64 \
riscv64_virt sifive_u esp32 x86 x86_64_efi mips powerpc sparc m68k sh4 v850 \
frv h8300 mn103 strongarm xscale cortex_r5")
    endif()

    # ---- Firmware executable (cross-compile with linker script) ----
    if(CMAKE_CROSSCOMPILING)
        set(_LD_STAGE0 "${CMAKE_CURRENT_SOURCE_DIR}/boards/${EBLDR_BOARD}/${EBLDR_BOARD}_stage0.ld")
        set(_LD_STAGE1 "${CMAKE_CURRENT_SOURCE_DIR}/boards/${EBLDR_BOARD}/${EBLDR_BOARD}_stage1.ld")

        if(EXISTS "${_LD_STAGE0}")
            add_executable(ebldr_stage0
                stage0/reset_entry.c
                stage0/hw_init_minimal.c
                stage0/watchdog.c
                stage0/recovery_entry.c
                stage0/jump_stage1.c
            )
            target_include_directories(ebldr_stage0 PRIVATE
                ${EBLDR_INCLUDE_DIR}
                ${CMAKE_CURRENT_SOURCE_DIR}/boards/${EBLDR_BOARD}
            )
            target_link_libraries(ebldr_stage0 PRIVATE eboot_core board_${EBLDR_BOARD})
            set_target_properties(ebldr_stage0 PROPERTIES
                LINK_FLAGS "-T${_LD_STAGE0} -nostartfiles"
                SUFFIX ".elf"
            )
            add_custom_command(TARGET ebldr_stage0 POST_BUILD
                COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:ebldr_stage0> ebldr_stage0.bin
                COMMENT "Generating stage0 binary for ${EBLDR_BOARD}"
            )
        endif()

        if(EXISTS "${_LD_STAGE1}")
            add_executable(eboot_firmware stage1/main.c)
            target_include_directories(eboot_firmware PRIVATE
                ${EBLDR_INCLUDE_DIR}
                ${CMAKE_CURRENT_SOURCE_DIR}/boards/${EBLDR_BOARD}
            )
            target_link_libraries(eboot_firmware PRIVATE eboot_stage1 board_${EBLDR_BOARD})
            set_target_properties(eboot_firmware PROPERTIES
                LINK_FLAGS "-T${_LD_STAGE1} -nostartfiles"
                SUFFIX ".elf"
            )
            add_custom_command(TARGET eboot_firmware POST_BUILD
                COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:eboot_firmware> eboot_firmware.bin
                COMMENT "Generating firmware binary for ${EBLDR_BOARD}"
            )
        endif()
    endif()
endif()

# ====================================================================
# Unit Tests — native builds only
# ====================================================================
if(EBLDR_BUILD_TESTS AND NOT CMAKE_CROSSCOMPILING)
    enable_testing()
    add_subdirectory(tests)
endif()

# ====================================================================
# Status
# ====================================================================
message(STATUS "----------------------------------------------------")
message(STATUS "eBootloader v${PROJECT_VERSION}")
message(STATUS "  Board       : ${EBLDR_BOARD}")
message(STATUS "  Tests       : ${EBLDR_BUILD_TESTS}")
message(STATUS "  Cross-compile: ${CMAKE_CROSSCOMPILING}")
if(EBLDR_BOARD STREQUAL "none")
    message(STATUS "  Mode        : Core libraries only (host build)")
    message(STATUS "  Outputs     : eboot_hal, eboot_core, eboot_stage1")
    message(STATUS "")
    message(STATUS "  To build for a target board:")
    message(STATUS "    cmake -B build -DEBLDR_BOARD=stm32f4 \\")
    message(STATUS "      -DCMAKE_TOOLCHAIN_FILE=toolchains/arm-none-eabi.cmake")
else()
    message(STATUS "  Mode        : Board port (${EBLDR_BOARD})")
endif()
message(STATUS "----------------------------------------------------")
