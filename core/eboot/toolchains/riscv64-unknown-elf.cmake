# ---------------------------------------------------------------
# CMake Toolchain — RISC-V 64-bit bare-metal
# Compiler: riscv64-unknown-elf-gcc
# Targets:  SiFive, StarFive boards (bare-metal)
# ---------------------------------------------------------------

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR riscv64)

set(CMAKE_C_COMPILER   riscv64-unknown-elf-gcc)
set(CMAKE_CXX_COMPILER riscv64-unknown-elf-g++)
set(CMAKE_ASM_COMPILER riscv64-unknown-elf-gcc)
set(CMAKE_AR           riscv64-unknown-elf-ar)
set(CMAKE_RANLIB       riscv64-unknown-elf-ranlib)
set(CMAKE_OBJCOPY      riscv64-unknown-elf-objcopy)
set(CMAKE_OBJDUMP      riscv64-unknown-elf-objdump)
set(CMAKE_SIZE         riscv64-unknown-elf-size)

set(CMAKE_C_FLAGS_INIT   "-march=rv64imac -mabi=lp64 --specs=picolibc.specs -ffunction-sections -fdata-sections -fno-common")
set(CMAKE_CXX_FLAGS_INIT "${CMAKE_C_FLAGS_INIT}")
set(CMAKE_EXE_LINKER_FLAGS_INIT "-Wl,--gc-sections -nostartfiles -nostdlib")

set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
