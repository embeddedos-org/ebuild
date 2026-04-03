add_executable(eai src/main.c)

target_link_libraries(eai PRIVATE
    eai_common
    eai_min
    eai_framework
    eai_platform
)
