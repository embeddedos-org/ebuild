cmake_minimum_required(VERSION 3.10)
project(EOSUITE C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

set(EOSUITE_VERSION "1.1.0")

if(MSVC)
    set(CMAKE_C_FLAGS_RELEASE "/O1 /DNDEBUG")
    add_compile_definitions(_CRT_SECURE_NO_WARNINGS)
else()
    set(CMAKE_C_FLAGS_RELEASE "-Os -DNDEBUG")
endif()

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

set(CORE_SOURCES
    src/main.c
    src/calculator.c
    src/timer_app.c
    src/snake.c
    src/notepad.c
    src/hex_viewer.c
    src/ssh_client.c
    src/serial_term.c
    src/session_manager.c
    src/eguard.c
    src/eweb.c
    src/ezip.c
    src/ecleaner.c
    src/evpn.c
    src/echat.c
    src/epaint.c
    src/eplay.c
    src/ebuffer.c
    src/econverter.c
    src/epdf.c
)

if(WIN32)
    list(APPEND CORE_SOURCES src/platform_win.c)
else()
    list(APPEND CORE_SOURCES src/platform_unix.c)
endif()

add_executable(EOSUITE ${CORE_SOURCES})
target_include_directories(EOSUITE PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

if(WIN32)
    target_link_libraries(EOSUITE ws2_32)
elseif(APPLE)
    target_link_libraries(EOSUITE m)
    find_library(COREFOUNDATION_LIB CoreFoundation)
    find_library(IOKIT_LIB IOKit)
    if(COREFOUNDATION_LIB)
        target_link_libraries(EOSUITE ${COREFOUNDATION_LIB})
    endif()
    if(IOKIT_LIB)
        target_link_libraries(EOSUITE ${IOKIT_LIB})
    endif()
else()
    target_link_libraries(EOSUITE m)
    find_package(Threads QUIET)
    if(Threads_FOUND)
        target_link_libraries(EOSUITE Threads::Threads)
    endif()
endif()

if(NOT WIN32 AND NOT MSVC)
    set(CMAKE_C_FLAGS_RELEASE "${CMAKE_C_FLAGS_RELEASE} -s")
endif()

install(TARGETS EOSUITE DESTINATION bin)
