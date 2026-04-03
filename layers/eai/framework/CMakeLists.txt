add_library(eai_framework STATIC
    src/runtime_manager.c
    src/orchestrator.c
    src/connector_mqtt.c
    src/connector_opcua.c
    src/connector_modbus.c
    src/connector_can.c
    src/memory.c
    src/policy.c
    src/observability.c
)

target_include_directories(eai_framework PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(eai_framework PUBLIC eai_common)
