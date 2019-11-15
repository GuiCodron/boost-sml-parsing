cmake_minimum_required (VERSION 3.2)
project(SM_Declaration)


add_library (sml INTERFACE)
target_include_directories(sml INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/../sml/include)

add_executable(state_machine sm.cpp)
target_link_libraries(state_machine sml)

