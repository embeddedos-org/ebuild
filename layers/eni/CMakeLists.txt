cmake_minimum_required(VERSION 3.16)
project(ENI
    VERSION 0.1.0
    DESCRIPTION "Neural Interface Adapter — BCI/sensor input integration for EoS AI Layer"
    LANGUAGES C
)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

option(ENI_BUILD_MIN       "Build ENI-Min lightweight runtime"       ON)
option(ENI_BUILD_FRAMEWORK "Build ENI-Framework industrial platform" ON)
option(ENI_BUILD_CLI       "Build ENI CLI tool"                      ON)
option(ENI_BUILD_TESTS     "Build unit tests"                        OFF)

option(ENI_EIPC_ENABLED    "Enable EIPC integration for ENI→EAI communication" OFF)

if(ENI_EIPC_ENABLED)
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../eipc/sdk/c ${CMAKE_BINARY_DIR}/eipc_c_sdk EXCLUDE_FROM_ALL)
endif()

option(ENI_PLATFORM_EOS   "Enable EoS platform adapter"   OFF)
option(ENI_PLATFORM_LINUX     "Enable Linux platform adapter"     ON)
option(ENI_PLATFORM_WINDOWS   "Enable Windows platform adapter"   OFF)
option(ENI_PLATFORM_CONTAINER "Enable container platform adapter" OFF)

if(WIN32)
    set(ENI_PLATFORM_LINUX OFF)
    set(ENI_PLATFORM_WINDOWS ON)
endif()

# Common library (shared contracts + utilities)
add_subdirectory(common)

# Platform adapters
add_subdirectory(platform)

# Providers (simulator, generic decoder)
add_subdirectory(providers)

if(ENI_BUILD_MIN)
    add_subdirectory(min)
endif()

if(ENI_BUILD_FRAMEWORK)
    add_subdirectory(framework)
endif()

if(ENI_BUILD_CLI)
    add_subdirectory(cli)
endif()

if(ENI_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

message(STATUS "--------------------------------------------")
message(STATUS "ENI v${PROJECT_VERSION}")
message(STATUS "  ENI-Min:       ${ENI_BUILD_MIN}")
message(STATUS "  ENI-Framework: ${ENI_BUILD_FRAMEWORK}")
message(STATUS "  CLI:           ${ENI_BUILD_CLI}")
message(STATUS "  Platform:      eos=${ENI_PLATFORM_EOS} linux=${ENI_PLATFORM_LINUX} win=${ENI_PLATFORM_WINDOWS} container=${ENI_PLATFORM_CONTAINER}")
message(STATUS "--------------------------------------------")
