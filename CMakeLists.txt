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
# Core: EoS (always built)
# ================================================================
message(STATUS "=== EoS Platform v${PROJECT_VERSION} ===")
message(STATUS "  Target: ${EOS_TARGET}")
add_subdirectory(core/eos)
message(STATUS "  Core/EoS: ON")

# ================================================================
# Core: eBoot (always built)
# ================================================================
add_subdirectory(core/eboot)
message(STATUS "  Core/eBoot: ON")

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