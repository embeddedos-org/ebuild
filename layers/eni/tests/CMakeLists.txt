add_executable(eni_test_common test_common.c)
target_link_libraries(eni_test_common PRIVATE eni_common)
add_test(NAME eni_common_tests COMMAND eni_test_common)

add_executable(eni_test_min test_min.c)
target_link_libraries(eni_test_min PRIVATE eni_common eni_min)
add_test(NAME eni_min_tests COMMAND eni_test_min)

add_executable(eni_test_framework test_framework.c)
target_link_libraries(eni_test_framework PRIVATE eni_common eni_framework)
add_test(NAME eni_framework_tests COMMAND eni_test_framework)

add_executable(eni_test_providers test_providers.c)
target_link_libraries(eni_test_providers PRIVATE eni_common eni_providers)
add_test(NAME eni_provider_tests COMMAND eni_test_providers)
