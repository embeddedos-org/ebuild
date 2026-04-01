# eBootloader Unit Tests
# All tests link against core libraries and run natively (no board ports needed).

# --- test_bootctl: Boot control block ---
add_executable(test_bootctl unit/test_bootctl.c)
target_link_libraries(test_bootctl PRIVATE eboot_core)
add_test(NAME test_bootctl COMMAND test_bootctl)

# --- test_crypto: SHA-256 against known vectors ---
add_executable(test_crypto unit/test_crypto.c)
target_link_libraries(test_crypto PRIVATE eboot_core)
add_test(NAME test_crypto COMMAND test_crypto)

# --- test_device_table: UEFI-style device table ---
add_executable(test_device_table unit/test_device_table.c)
target_link_libraries(test_device_table PRIVATE eboot_core)
add_test(NAME test_device_table COMMAND test_device_table)

# --- test_runtime_svc: Runtime variable store ---
add_executable(test_runtime_svc unit/test_runtime_svc.c)
target_link_libraries(test_runtime_svc PRIVATE eboot_core)
add_test(NAME test_runtime_svc COMMAND test_runtime_svc)

# --- test_board_config: Declarative hardware config ---
add_executable(test_board_config unit/test_board_config.c)
target_link_libraries(test_board_config PRIVATE eboot_core)
add_test(NAME test_board_config COMMAND test_board_config)

# --- test_multicore: Multicore boot management ---
add_executable(test_multicore unit/test_multicore.c)
target_link_libraries(test_multicore PRIVATE eboot_core)
add_test(NAME test_multicore COMMAND test_multicore)

# --- test_board_registry: Runtime board selection ---
add_executable(test_board_registry unit/test_board_registry.c)
target_link_libraries(test_board_registry PRIVATE eboot_core)
add_test(NAME test_board_registry COMMAND test_board_registry)
