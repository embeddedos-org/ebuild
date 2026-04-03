add_library(eni_platform STATIC)

target_include_directories(eni_platform PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(eni_platform PUBLIC eni_common)

if(ENI_PLATFORM_EOS)
    target_sources(eni_platform PRIVATE eos/platform_eos.c)
    target_compile_definitions(eni_platform PUBLIC ENI_PLATFORM_EOS_ENABLED)
elseif(ENI_PLATFORM_LINUX)
    target_sources(eni_platform PRIVATE linux/platform_linux.c)
elseif(ENI_PLATFORM_WINDOWS)
    target_sources(eni_platform PRIVATE windows/platform_windows.c)
else()
    # Default to Linux adapter when no platform is explicitly selected
    target_sources(eni_platform PRIVATE linux/platform_linux.c)
endif()
