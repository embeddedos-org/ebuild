cmake_minimum_required(VERSION 3.16)
project(EoS-Platform
    VERSION 0.1.0
    DESCRIPTION "EoS Embedded OS Platform — monorepo build"
    LANGUAGES C
)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Platform options
set(EOS_TARGET "x86_64" CACHE STRING "Target hardware (raspi4, stm32f4, etc.)")
option(EOS_BUILD_TESTS "Build unit tests" OFF)

# Layer options (optional components)
option(EOS_WITH_EAI     "Build EAI — AI layer (llama.cpp, Ebot server)" OFF)
option(EOS_WITH_ENI     "Build ENI — Neural interface (Neuralink adapter)" OFF)
option(EOS_WITH_EIPC    "Build EIPC — Secure IPC (C SDK)" OFF)
option(EOS_WITH_EOSUITE "Build eApps — Dev tools (Ebot client)" OFF)
option(EOS_WITH_ALL     "Build all optional layers" OFF)

if(EOS_WITH_ALL)
    set(EOS_WITH_EAI ON)
    set(EOS_WITH_ENI ON)
    set(EOS_WITH_EIPC ON)
    set(EOS_WITH_EOSUITE ON)
endif()

if(MSVC)
    add_compile_definitions(_CRT_SECURE_NO_WARNINGS)
    add_compile_options(/W3)
elseif(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-Wall -Wextra)
endif()

# ================================================================
# Core: EoS + eBoot (always built, dynamically resolved)
# ================================================================
message(STATUS "=== EoS Platform v${PROJECT_VERSION} ===")
message(STATUS "  Target: ${EOS_TARGET}")

set(EOS_SOURCE_DIR "" CACHE PATH "Path to EoS source (auto-resolved if empty)")
set(EBOOT_SOURCE_DIR "" CACHE PATH "Path to eBoot source (auto-resolved if empty)")

# --- Auto-resolve EoS source directory ---
if(NOT EOS_SOURCE_DIR OR EOS_SOURCE_DIR STREQUAL "")
    # 1. Check sibling directory ../eos (standalone repo — preferred)
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../eos/CMakeLists.txt")
        get_filename_component(EOS_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../eos" ABSOLUTE)
    # 2. Check ~/.ebuild/repos/eos (cached clone)
    elseif(DEFINED ENV{HOME} AND EXISTS "$ENV{HOME}/.ebuild/repos/eos/CMakeLists.txt")
        set(EOS_SOURCE_DIR "$ENV{HOME}/.ebuild/repos/eos")
    elseif(DEFINED ENV{USERPROFILE} AND EXISTS "$ENV{USERPROFILE}/.ebuild/repos/eos/CMakeLists.txt")
        set(EOS_SOURCE_DIR "$ENV{USERPROFILE}/.ebuild/repos/eos")
    # 3. Fallback to embedded core/eos
    elseif(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/core/eos/CMakeLists.txt")
        set(EOS_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/core/eos")
        message(WARNING "Using embedded core/eos/ — run 'ebuild setup' to use standalone repos instead.")
    endif()
endif()

if(EOS_SOURCE_DIR AND EXISTS "${EOS_SOURCE_DIR}/CMakeLists.txt")
    add_subdirectory(${EOS_SOURCE_DIR} ${CMAKE_BINARY_DIR}/eos)
    message(STATUS "  Core/EoS: ON (${EOS_SOURCE_DIR})")
else()
    message(WARNING "EoS source not found. Run 'ebuild setup' or set -DEOS_SOURCE_DIR=<path>.")
endif()

# --- Auto-resolve eBoot source directory ---
if(NOT EBOOT_SOURCE_DIR OR EBOOT_SOURCE_DIR STREQUAL "")
    # 1. Check sibling directory ../eos (standalone repo — preferred)
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../eos/CMakeLists.txt")
        get_filename_component(EBOOT_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../eos" ABSOLUTE)
    # Also try mixed-case eBoot (canonical GitHub name)
    elseif(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../eBoot/CMakeLists.txt")
        get_filename_component(EBOOT_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../eBoot" ABSOLUTE)
    # Also try lowercase eboot
    elseif(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../eboot/CMakeLists.txt")
        get_filename_component(EBOOT_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../eboot" ABSOLUTE)
    # 2. Check ~/.ebuild/repos/eboot (cached clone)
    elseif(DEFINED ENV{HOME} AND EXISTS "$ENV{HOME}/.ebuild/repos/eboot/CMakeLists.txt")
        set(EBOOT_SOURCE_DIR "$ENV{HOME}/.ebuild/repos/eboot")
    elseif(DEFINED ENV{USERPROFILE} AND EXISTS "$ENV{USERPROFILE}/.ebuild/repos/eboot/CMakeLists.txt")
        set(EBOOT_SOURCE_DIR "$ENV{USERPROFILE}/.ebuild/repos/eboot")
    # 3. Fallback to embedded core/eboot
    elseif(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/core/eboot/CMakeLists.txt")
        set(EBOOT_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/core/eboot")
        message(WARNING "Using embedded core/eboot/ — run 'ebuild setup' to use standalone repos instead.")
    endif()
endif()

if(EBOOT_SOURCE_DIR AND EXISTS "${EBOOT_SOURCE_DIR}/CMakeLists.txt")
    add_subdirectory(${EBOOT_SOURCE_DIR} ${CMAKE_BINARY_DIR}/eboot)
    message(STATUS "  Core/eBoot: ON (${EBOOT_SOURCE_DIR})")
else()
    message(WARNING "eBoot source not found. Run 'ebuild setup' or set -DEBOOT_SOURCE_DIR=<path>.")
endif()

# ================================================================
# Optional Layers
# ================================================================
if(EOS_WITH_EIPC)
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/layers/eipc/sdk/c/CMakeLists.txt")
        add_subdirectory(layers/eipc/sdk/c)
        message(STATUS "  Layer/EIPC: ON")
    endif()
endif()

if(EOS_WITH_EAI)
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/layers/eai/CMakeLists.txt")
        add_subdirectory(layers/eai)
        message(STATUS "  Layer/EAI: ON")
    endif()
endif()

if(EOS_WITH_ENI)
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/layers/eni/CMakeLists.txt")
        add_subdirectory(layers/eni)
        message(STATUS "  Layer/ENI: ON")
    endif()
endif()

if(EOS_WITH_EOSUITE AND NOT WIN32)
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/layers/eosuite/CMakeLists.txt")
        add_subdirectory(layers/eosuite)
        message(STATUS "  Layer/eApps: ON")
    endif()
endif()

# ================================================================
# Tests
# ================================================================
if(EOS_BUILD_TESTS)
    enable_testing()
    message(STATUS "  Tests: ON")
endif()

message(STATUS "========================================")
