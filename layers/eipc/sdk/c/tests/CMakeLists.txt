add_executable(eipc_test_frame test_frame.c)
target_link_libraries(eipc_test_frame PRIVATE eipc_c)
add_test(NAME eipc_frame_tests COMMAND eipc_test_frame)

add_executable(eipc_test_hmac test_hmac.c)
target_link_libraries(eipc_test_hmac PRIVATE eipc_c)
add_test(NAME eipc_hmac_tests COMMAND eipc_test_hmac)

add_executable(eipc_test_transport test_transport.c)
target_link_libraries(eipc_test_transport PRIVATE eipc_c)
add_test(NAME eipc_transport_tests COMMAND eipc_test_transport)
