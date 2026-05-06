cmake_minimum_required(VERSION 3.18)
project(nfp_cgal_probe CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# CGAL is installed as header-only via apt
# Boost libraries are available via find_package
find_package(Boost REQUIRED COMPONENTS chrono system thread)

# CGAL header-only: define before including any CGAL header
add_definitions(-DCGAL_HEADER_ONLY)

include_directories(/usr/include)

add_executable(nfp_cgal_probe src/main.cpp)

# CGAL needs GMP + MPFR for exact number types
find_library(GMP_LIBRARY NAMES gmp libgmp REQUIRED)
find_library(MPFR_LIBRARY NAMES mpfr libmpfr REQUIRED)

target_link_libraries(nfp_cgal_probe
    ${GMP_LIBRARY}
    ${MPFR_LIBRARY}
    Threads::Threads
)
