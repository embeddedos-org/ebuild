add_library(eai_platform STATIC
    src/platform.c
    src/platform_linux.c
    src/platform_windows.c
)

target_include_directories(eai_platform PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(eai_platform PUBLIC eai_common)

if(EAI_PLATFORM_EOS)
    target_sources(eai_platform PRIVATE src/platform_eos.c)
    target_compile_definitions(eai_platform PUBLIC EAI_PLATFORM_EOS_ENABLED)
endif()
