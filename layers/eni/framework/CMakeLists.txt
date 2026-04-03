add_library(eni_framework STATIC
    src/provider_manager.c
    src/stream_bus.c
    src/router.c
    src/orchestrator.c
    src/connectors.c
    src/observability.c
    src/service.c
)

target_include_directories(eni_framework PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(eni_framework PUBLIC eni_common)
