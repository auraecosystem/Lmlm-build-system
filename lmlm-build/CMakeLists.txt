cmake_minimum_required(VERSION 3.24)
project(LMLMBuildFabric VERSION 0.2.0 LANGUAGES CXX)

include(cmake/LmlmOptions.cmake)

add_library(lmlm_build_probe STATIC src/build_info.cpp src/capabilities.cpp)
target_include_directories(lmlm_build_probe PUBLIC include)
target_compile_features(lmlm_build_probe PUBLIC cxx_std_20)
set_target_properties(lmlm_build_probe PROPERTIES
  CXX_EXTENSIONS OFF
  POSITION_INDEPENDENT_CODE ON
)

add_executable(lmlm_cpu_capabilities src/capabilities_main.cpp)
target_link_libraries(lmlm_cpu_capabilities PRIVATE lmlm_build_probe)

if(LMLM_ENABLE_CUDA)
  enable_language(CUDA)
  find_package(CUDAToolkit REQUIRED)
  add_executable(lmlm_cuda_probe src/cuda_probe.cu)
  target_link_libraries(lmlm_cuda_probe PRIVATE CUDA::cudart)
  set_target_properties(lmlm_cuda_probe PROPERTIES
    CUDA_STANDARD 17
    CUDA_STANDARD_REQUIRED ON
  )
endif()

if(LMLM_ENABLE_ROCM)
  enable_language(HIP)
  add_executable(lmlm_rocm_probe src/hip_probe.hip)
  set_target_properties(lmlm_rocm_probe PROPERTIES
    HIP_STANDARD 17
    HIP_STANDARD_REQUIRED ON
  )
endif()

if(LMLM_ENABLE_METAL)
  if(NOT APPLE)
    message(FATAL_ERROR "LMLM_ENABLE_METAL requires macOS.")
  endif()
  enable_language(OBJCXX)
  find_library(METAL_FRAMEWORK Metal REQUIRED)
  find_library(FOUNDATION_FRAMEWORK Foundation REQUIRED)
  add_executable(lmlm_metal_probe src/metal_probe.mm)
  target_link_libraries(lmlm_metal_probe PRIVATE ${METAL_FRAMEWORK} ${FOUNDATION_FRAMEWORK})
endif()

include(CTest)
if(BUILD_TESTING)
  add_executable(lmlm_build_probe_test tests/build_info_test.cpp)
  target_link_libraries(lmlm_build_probe_test PRIVATE lmlm_build_probe)
  add_test(NAME lmlm_build_probe_test COMMAND lmlm_build_probe_test)

  add_executable(lmlm_capabilities_test tests/capabilities_test.cpp)
  target_link_libraries(lmlm_capabilities_test PRIVATE lmlm_build_probe)
  add_test(NAME lmlm_capabilities_test COMMAND lmlm_capabilities_test)
endif()

install(TARGETS lmlm_build_probe lmlm_cpu_capabilities
  ARCHIVE DESTINATION lib
  RUNTIME DESTINATION bin
)
install(DIRECTORY include/ DESTINATION include)
