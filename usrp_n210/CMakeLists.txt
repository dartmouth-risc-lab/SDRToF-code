cmake_minimum_required(VERSION 3.16)
project(usrp_n210 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(UHD REQUIRED)

add_library(usrp_core
  src/usrp/device.cpp
  src/usrp/rx_stream.cpp
  src/usrp/tx_stream.cpp
)

target_include_directories(usrp_core PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${UHD_INCLUDE_DIRS}
)
target_link_libraries(usrp_core PUBLIC
  ${UHD_LIBRARIES}
)

#add_executable(usrp_probe apps/usrp_probe.cpp)
#target_link_libraries(usrp_probe PRIVATE usrp_core)

#add_executable(rx_capture apps/rx_capture.cpp)
#target_link_libraries(rx_capture PRIVATE usrp_core)

#add_executable(tx_tone apps/tx_tone.cpp)
#target_link_libraries(tx_tone PRIVATE usrp_core)

add_executable(usrp_full_duplex apps/usrp_full_duplex.cpp)
add_executable(usrp_full_duplex_prev apps/usrp_full_duplex_prev.cpp)
target_link_libraries(usrp_full_duplex PRIVATE usrp_core)
target_link_libraries(usrp_full_duplex_prev PRIVATE usrp_core)