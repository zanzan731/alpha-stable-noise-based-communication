find_package(PkgConfig)

PKG_CHECK_MODULES(PC_GR_ALPHA gnuradio-alpha)

FIND_PATH(
    GR_ALPHA_INCLUDE_DIRS
    NAMES gnuradio/alpha/api.h
    HINTS $ENV{ALPHA_DIR}/include
        ${PC_ALPHA_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    GR_ALPHA_LIBRARIES
    NAMES gnuradio-alpha
    HINTS $ENV{ALPHA_DIR}/lib
        ${PC_ALPHA_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
          )

include("${CMAKE_CURRENT_LIST_DIR}/gnuradio-alphaTarget.cmake")

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(GR_ALPHA DEFAULT_MSG GR_ALPHA_LIBRARIES GR_ALPHA_INCLUDE_DIRS)
MARK_AS_ADVANCED(GR_ALPHA_LIBRARIES GR_ALPHA_INCLUDE_DIRS)
