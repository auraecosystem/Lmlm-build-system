cmake_minimum_required(VERSION 3.24)
project(LMLMBuildFabric VERSION 0.1.0 LANGUAGES CXX)

include(cmake/LmlmOptions.cmake)

add_library(lmlm_build_probe STATIC src/build_info.cpp)
target_include_directories(lmlm_build_probe PUBLIC include)
target_compile_features(lmlm_build_probe PUBLIC cxx_std_20)
set_target_properties(lmlm_build_probe PROPERTIES
  CXX_EXTENSIONS OFF
  POSITION_INDEPENDENT_CODE ON
)

if(LMLM_ENABLE_CUDA)
  enable_language(CUDA)
  find_package(CUDAToolkit REQUIRED)
  add_library(lmlm_cuda_probe OBJECT src/cuda_probe.cu)
  target_link_libraries(lmlm_cuda_probe PRIVATE CUDA::cudart)
  set_target_properties(lmlm_cuda_probe PROPERTIES
    CUDA_STANDARD 17
    CUDA_STANDARD_REQUIRED ON
  )
endif()

if(LMLM_ENABLE_ROCM)
  enable_language(HIP)
  add_library(lmlm_hip_probe OBJECT src/hip_probe.hip)
  set_target_properties(lmlm_hip_probe PROPERTIES
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
  add_library(lmlm_metal_probe OBJECT src/metal_probe.mm)
  target_link_libraries(lmlm_metal_probe PRIVATE ${METAL_FRAMEWORK})
endif()

include(CTest)
if(BUILD_TESTING)
  add_executable(lmlm_build_probe_test tests/build_info_test.cpp)
  target_link_libraries(lmlm_build_probe_test PRIVATE lmlm_build_probe)
  add_test(NAME lmlm_build_probe_test COMMAND lmlm_build_probe_test)
endif()

install(TARGETS lmlm_build_probe ARCHIVE DESTINATION lib)
install(DIRECTORY include/ DESTINATION include)
