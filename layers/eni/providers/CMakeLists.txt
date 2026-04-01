option(ENI_PROVIDER_NEURALINK "Enable Neuralink BCI adapter" ON)
option(ENI_PROVIDER_SIMULATOR "Enable BCI simulator (testing)" ON)
option(ENI_PROVIDER_GENERIC   "Enable generic decoder" ON)

set(PROVIDER_SOURCES "")
set(PROVIDER_INCLUDES "")

if(ENI_PROVIDER_SIMULATOR)
    list(APPEND PROVIDER_SOURCES simulator/simulator.c)
    list(APPEND PROVIDER_INCLUDES ${CMAKE_CURRENT_SOURCE_DIR}/simulator)
endif()

if(ENI_PROVIDER_GENERIC)
    list(APPEND PROVIDER_SOURCES generic/generic.c)
    list(APPEND PROVIDER_INCLUDES ${CMAKE_CURRENT_SOURCE_DIR}/generic)
endif()

if(ENI_PROVIDER_NEURALINK)
    list(APPEND PROVIDER_SOURCES neuralink/neuralink.c)
    list(APPEND PROVIDER_INCLUDES ${CMAKE_CURRENT_SOURCE_DIR}/neuralink)
    add_compile_definitions(ENI_HAS_NEURALINK)
endif()

add_library(eni_providers STATIC ${PROVIDER_SOURCES})
target_include_directories(eni_providers PUBLIC ${PROVIDER_INCLUDES})
target_link_libraries(eni_providers PUBLIC eni_common)

if(UNIX AND NOT APPLE)
    target_link_libraries(eni_providers PRIVATE m)
endif()

message(STATUS "  Providers: simulator=${ENI_PROVIDER_SIMULATOR} generic=${ENI_PROVIDER_GENERIC} neuralink=${ENI_PROVIDER_NEURALINK}")