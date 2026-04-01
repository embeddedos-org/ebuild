add_library(eai_models STATIC models.c)
target_include_directories(eai_models PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(eai_models PUBLIC eai_common)