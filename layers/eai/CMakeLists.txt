cmake_minimum_required(VERSION 3.16)
project(EAI
    VERSION 0.1.0
    DESCRIPTION "AI Layer — Embedded AI platform for intelligent systems"
    LANGUAGES C
)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

option(EAI_BUILD_MIN       "Build EAI-Min lightweight runtime"       ON)
option(EAI_BUILD_FRAMEWORK "Build EAI-Framework industrial platform" ON)
option(EAI_BUILD_CLI       "Build EAI CLI tool"                      ON)
option(EAI_BUILD_TESTS     "Build unit tests"                        OFF)

option(EAI_PLATFORM_EOS   "Enable EoS platform adapter"   OFF)
option(EAI_PLATFORM_LINUX     "Enable Linux platform adapter"     ON)
option(EAI_PLATFORM_WINDOWS   "Enable Windows platform adapter"   OFF)
option(EAI_PLATFORM_CONTAINER "Enable container platform adapter" OFF)

option(EAI_EIPC_ENABLED "Enable EIPC integration for ENI→EAI communication" OFF)
option(EAI_LLAMA_CPP "Enable real llama.cpp runtime backend" OFF)

if(EAI_EIPC_ENABLED)
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../eipc/sdk/c ${CMAKE_BINARY_DIR}/eipc_c_sdk EXCLUDE_FROM_ALL)
endif()

if(WIN32)
    set(EAI_PLATFORM_LINUX OFF)
    set(EAI_PLATFORM_WINDOWS ON)
endif()

# Common library (shared contracts + utilities)
add_subdirectory(common)

# Platform adapters
add_subdirectory(platform)

if(EAI_BUILD_MIN)
    add_subdirectory(min)
endif()

if(EAI_BUILD_FRAMEWORK)
    add_subdirectory(framework)
endif()

add_subdirectory(models)

if(EAI_BUILD_CLI)
    add_subdirectory(cli)
endif()

if(EAI_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

message(STATUS "--------------------------------------------")
message(STATUS "EAI v${PROJECT_VERSION}")
message(STATUS "  EAI-Min:       ${EAI_BUILD_MIN}")
message(STATUS "  EAI-Framework: ${EAI_BUILD_FRAMEWORK}")
message(STATUS "  CLI:           ${EAI_BUILD_CLI}")
message(STATUS "  Platform:      eos=${EAI_PLATFORM_EOS} linux=${EAI_PLATFORM_LINUX} win=${EAI_PLATFORM_WINDOWS} container=${EAI_PLATFORM_CONTAINER}")
message(STATUS "--------------------------------------------")
