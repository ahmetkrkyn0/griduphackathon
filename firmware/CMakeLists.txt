# Pano Beyni tasinabilir cekirdegi (TA3, Kisi A).
#
# Kurulum ve test:
#   cmake -S firmware -B firmware/build
#   cmake --build firmware/build
#   ctest --test-dir firmware/build --output-on-failure
#
# Cekirdek yalnizca C11 ve standart kutuphaneye baglidir; dinamik bellek kullanmaz.
# Ayni kaynak hem host ikilisinde hem MCU hedefinde derlenir (PLAN.md TA3 Adim 5).
cmake_minimum_required(VERSION 3.16)
project(panobeyni C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

option(PANO_USE_FLOAT "Cekirdegi tek duyarlikli (float) derle" OFF)

add_library(panocore STATIC
    core/rls.c
    core/thermal.c
    core/dewpoint.c
    core/limits.c
    core/modbus_map.c
)
target_include_directories(panocore PUBLIC core)
if(PANO_USE_FLOAT)
    target_compile_definitions(panocore PUBLIC PANO_USE_FLOAT)
endif()
if(NOT MSVC)
    target_compile_options(panocore PRIVATE -Wall -Wextra -Wpedantic)
    target_link_libraries(panocore PUBLIC m)
endif()

enable_testing()

add_executable(test_rls tests/test_rls.c)
target_link_libraries(test_rls PRIVATE panocore)

add_executable(test_dewpoint tests/test_dewpoint.c)
target_link_libraries(test_dewpoint PRIVATE panocore)

add_executable(test_rls_robustness tests/test_rls_robustness.c)
target_link_libraries(test_rls_robustness PRIVATE panocore)

add_executable(test_limits tests/test_limits.c)
target_link_libraries(test_limits PRIVATE panocore)

add_executable(test_modbus_map tests/test_modbus_map.c)
target_link_libraries(test_modbus_map PRIVATE panocore)

# Ortak test vektoru Python tarafinda uretilir; yolu teste argüman olarak gecirilir.
set(PANO_VECTORS "${CMAKE_CURRENT_SOURCE_DIR}/../data/fixtures/rls_vectors.csv")

add_test(NAME rls_matches_python COMMAND test_rls "${PANO_VECTORS}")
add_test(NAME dewpoint_reference_values COMMAND test_dewpoint)
add_test(NAME rls_survives_covariance_windup COMMAND test_rls_robustness)
add_test(NAME limits_match_the_contract COMMAND test_limits)
add_test(NAME modbus_write_protection COMMAND test_modbus_map)
