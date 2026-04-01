add_executable(eai_test_common test_common.c)
target_link_libraries(eai_test_common PRIVATE eai_common)
add_test(NAME eai_common_tests COMMAND eai_test_common)

add_executable(eai_test_min test_min.c)
target_link_libraries(eai_test_min PRIVATE eai_common eai_min)
add_test(NAME eai_min_tests COMMAND eai_test_min)

add_executable(eai_test_framework test_framework.c)
target_link_libraries(eai_test_framework PRIVATE eai_common eai_framework)
add_test(NAME eai_framework_tests COMMAND eai_test_framework)
