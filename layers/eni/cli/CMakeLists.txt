add_executable(eni main.c)

target_link_libraries(eni PRIVATE
    eni_common
    eni_min
    eni_framework
    eni_providers
    eni_platform
)
