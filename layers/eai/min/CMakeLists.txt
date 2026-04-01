add_library(eai_min STATIC
    src/runtime.c
    src/agent.c
    src/router.c
    src/memory_lite.c
)

target_include_directories(eai_min PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(eai_min PUBLIC eai_common)

if(EAI_LLAMA_CPP)
    target_sources(eai_min PRIVATE src/runtime_llama.c)
    target_compile_definitions(eai_min PUBLIC EAI_LLAMA_CPP_ENABLED)
    find_package(llama QUIET)
    if(llama_FOUND)
        target_link_libraries(eai_min PUBLIC llama)
    else()
        message(WARNING "llama.cpp not found — set -Dllama_DIR=/path/to/llama.cpp/lib/cmake/llama")
    endif()
endif()
