add_library(eai_common STATIC
    src/config.c
    src/log.c
    src/manifest.c
    src/tool_registry.c
    src/security.c
    src/tools_builtin.c
    src/runtime_contract.c
)

target_include_directories(eai_common PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

if(EAI_EIPC_ENABLED)
    target_sources(eai_common PRIVATE src/eipc_listener.c)
    target_compile_definitions(eai_common PUBLIC EAI_EIPC_ENABLED)
    target_link_libraries(eai_common PUBLIC eipc_c)
endif()
