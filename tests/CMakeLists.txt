cmake_minimum_required(VERSION 3.2)

project(SMLParsingTests)

set(CMAKE_EXPORT_COMPILE_COMMANDS TRUE)

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/../../sml/include ${CMAKE_CURRENT_SOURCE_DIR})

file(GLOB test_files "./*.cpp")

foreach(test_file ${test_files})
    get_filename_component(EXEC_NAME ${test_file} NAME_WE)
    add_executable(${EXEC_NAME} ${test_file})
endforeach()