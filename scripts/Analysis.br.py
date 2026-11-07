from pathlib import Path
import textwrap, zipfile, os, tar

root = Path("/mnt/data/lmlm-build-system")
files = {
"README.md": r"""
# LMLM Build System

A standalone, reproducible build orchestrator for LMLM native/runtime components.
It borrows the useful orchestration patterns from the supplied Kubernetes build
script (isolated build environments, persistent caches, explicit toolchain
selection, artifact staging and cleanup) without importing Kubernetes-specific
paths, images, naming or assumptions.

## Supported build profiles

- `cpu`: portable CPU build; default and safe baseline.
- `cuda`: NVIDIA CUDA build profile using the CUDA devel image.
- `rocm`: AMD ROCm build profile using the ROCm dev image.
- `host`: build directly on the host (requires CMake, Ninja and a compiler).

GPU profiles are build environments, not proof that a GPU is available. Runtime
GPU access requires a compatible host driver, container runtime configuration,
and hardware. Apple Metal is not a Docker GPU profile: build Metal components on
macOS with Xcode/Clang using the `host` profile and `-DLMLM_ENABLE_METAL=ON`.

## Quick start

```bash
./scripts/lmlm-build.sh doctor
./scripts/lmlm-build.sh configure --profile cpu
./scripts/lmlm-build.sh build --profile cpu --jobs 4
./scripts/lmlm-build.sh test --profile cpu
./scripts/lmlm-build.sh package --profile cpu
```

Docker build:

```bash
./scripts/lmlm-build.sh build --profile cuda --docker
```

Host build on macOS (Metal-capable host):

```bash
./scripts/lmlm-build.sh configure --profile host \
  -- -DLMLM_ENABLE_METAL=ON
./scripts/lmlm-build.sh build --profile host
```

The repository consuming this build system should provide a top-level
`CMakeLists.txt`. This scaffold includes a small example project so the
orchestrator and tests can be exercised immediately.

## Environment

- `LMLM_ROOT`: project root (defaults to this repository).
- `LMLM_BUILD_DIR`: build directory (defaults to `_build/<profile>`).
- `LMLM_ARTIFACT_DIR`: artifact directory (defaults to `artifacts`).
- `LMLM_IMAGE_PREFIX`: Docker image prefix (defaults to `lmlm-build`).
- `LMLM_CMAKE_ARGS`: additional CMake arguments, whitespace-separated.
- `DOCKER`: Docker executable (defaults to `docker`).

For arguments containing spaces, pass them after `--` to `configure`; avoid
placing complex values in `LMLM_CMAKE_ARGS`.

## Security and reproducibility

- Runs host builds as the invoking user; does not use privileged containers.
- Docker builds mount the source read-only and build/cache/artifact directories
  separately.
- Does not mount the Docker socket into build containers.
- Does not pass host environment variables wholesale into containers.
- Pin image versions in `config/toolchains.env` before production CI use.
- Use trusted, digest-pinned base images in release pipelines.
- Do not run untrusted CMake projects with secrets mounted into the container.

## Layout

```text
.
├── CMakeLists.txt
├── CMakePresets.json
├── config/toolchains.env
├── docker/
│   ├── Dockerfile.cpu
│   ├── Dockerfile.cuda
│   └── Dockerfile.rocm
├── cmake/LmlmOptions.cmake
├── scripts/lmlm-build.sh
├── tests/shell/
└── src/
```

## Current scope and limitations

This is a production-oriented starting implementation, not a verified integration
with a separate LMLM runtime repository. Replace the example `src/` target with
the actual runtime targets after inspecting that repository. CUDA and ROCm
profiles configure compiler/toolkit environments; project code must implement
and test its own backend kernels. Metal requires macOS/Xcode and is not built in
Linux containers. No hardware-specific build or test is claimed as executed by
this generated artifact.
""",
"CMakeLists.txt": r"""
cmake_minimum_required(VERSION 3.24)
project(LMLMBuildSystem VERSION 0.1.0 LANGUAGES CXX)

include(cmake/LmlmOptions.cmake)

add_library(lmlm_build_probe STATIC src/build_probe.cpp)
target_compile_features(lmlm_build_probe PUBLIC cxx_std_20)
target_include_directories(lmlm_build_probe PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)
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

if(LMLM_ENABLE_METAL)
  if(NOT APPLE)
    message(FATAL_ERROR "LMLM_ENABLE_METAL requires macOS and Apple Clang.")
  endif()
  enable_language(OBJCXX)
  add_library(lmlm_metal_probe OBJECT src/metal_probe.mm)
endif()

include(CTest)
if(BUILD_TESTING)
  add_executable(lmlm_build_probe_test tests/cpp/build_probe_test.cpp)
  target_link_libraries(lmlm_build_probe_test PRIVATE lmlm_build_probe)
  add_test(NAME lmlm_build_probe_test COMMAND lmlm_build_probe_test)
endif()

install(TARGETS lmlm_build_probe
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)
""",
"cmake/LmlmOptions.cmake": r"""
option(LMLM_ENABLE_CUDA "Compile CUDA components" OFF)
option(LMLM_ENABLE_ROCM "Enable AMD ROCm components (project-managed)" OFF)
option(LMLM_ENABLE_METAL "Compile Apple Metal components" OFF)
option(LMLM_ENABLE_CPU "Enable portable CPU backend" ON)

math(EXPR LMLM_BACKEND_COUNT
  "${LMLM_ENABLE_CUDA}+${LMLM_ENABLE_ROCM}+${LMLM_ENABLE_METAL}")
if(LMLM_BACKEND_COUNT GREATER 1)
  message(FATAL_ERROR "Select at most one accelerator backend per build tree.")
endif()

if(NOT LMLM_ENABLE_CPU AND NOT LMLM_ENABLE_CUDA
   AND NOT LMLM_ENABLE_ROCM AND NOT LMLM_ENABLE_METAL)
  message(FATAL_ERROR "At least one LMLM backend must be enabled.")
endif()

message(STATUS "LMLM CPU backend: ${LMLM_ENABLE_CPU}")
message(STATUS "LMLM CUDA backend: ${LMLM_ENABLE_CUDA}")
message(STATUS "LMLM ROCm backend: ${LMLM_ENABLE_ROCM}")
message(STATUS "LMLM Metal backend: ${LMLM_ENABLE_METAL}")
""",
"CMakePresets.json": r"""
{
  "version": 6,
  "cmakeMinimumRequired": { "major": 3, "minor": 24, "patch": 0 },
  "configurePresets": [
    {
      "name": "cpu",
      "displayName": "LMLM CPU",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/_build/cpu",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Release",
        "LMLM_ENABLE_CPU": "ON",
        "LMLM_ENABLE_CUDA": "OFF",
        "LMLM_ENABLE_ROCM": "OFF",
        "LMLM_ENABLE_METAL": "OFF",
        "BUILD_TESTING": "ON"
      }
    },
    {
      "name": "cuda",
      "displayName": "LMLM CUDA",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/_build/cuda",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Release",
        "CMAKE_CUDA_ARCHITECTURES": "native",
        "LMLM_ENABLE_CPU": "ON",
        "LMLM_ENABLE_CUDA": "ON",
        "LMLM_ENABLE_ROCM": "OFF",
        "LMLM_ENABLE_METAL": "OFF",
        "BUILD_TESTING": "ON"
      }
    },
    {
      "name": "rocm",
      "displayName": "LMLM ROCm",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/_build/rocm",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Release",
        "LMLM_ENABLE_CPU": "ON",
        "LMLM_ENABLE_CUDA": "OFF",
        "LMLM_ENABLE_ROCM": "ON",
        "LMLM_ENABLE_METAL": "OFF",
        "BUILD_TESTING": "ON"
      }
    },
    {
      "name": "metal",
      "displayName": "LMLM Apple Metal",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/_build/metal",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Release",
        "LMLM_ENABLE_CPU": "ON",
        "LMLM_ENABLE_CUDA": "OFF",
        "LMLM_ENABLE_ROCM": "OFF",
        "LMLM_ENABLE_METAL": "ON",
        "BUILD_TESTING": "ON"
      }
    }
  ],
  "buildPresets": [
    { "name": "cpu", "configurePreset": "cpu" },
    { "name": "cuda", "configurePreset": "cuda" },
    { "name": "rocm", "configurePreset": "rocm" },
    { "name": "metal", "configurePreset": "metal" }
  ],
  "testPresets": [
    { "name": "cpu", "configurePreset": "cpu", "output": { "outputOnFailure": true } },
    { "name": "cuda", "configurePreset": "cuda", "output": { "outputOnFailure": true } },
    { "name": "rocm", "configurePreset": "rocm", "output": { "outputOnFailure": true } },
    { "name": "metal", "configurePreset": "metal", "output": { "outputOnFailure": true } }
  ]
}
""",
"config/toolchains.env": r"""
# Set these to tested, immutable tags or digests before production CI.
CPU_IMAGE=ubuntu:24.04
CUDA_IMAGE=nvidia/cuda:12.6.3-devel-ubuntu24.04
ROCM_IMAGE=rocm/dev-ubuntu-24.04:6.2
""",
"docker/Dockerfile.cpu": r"""
ARG BASE_IMAGE=ubuntu:24.04
FROM ${BASE_IMAGE}
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build git python3 ca-certificates \
    pkg-config ccache && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
""",
"docker/Dockerfile.cuda": r"""
ARG BASE_IMAGE=nvidia/cuda:12.6.3-devel-ubuntu24.04
FROM ${BASE_IMAGE}
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build git python3 ca-certificates \
    pkg-config ccache && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
""",
"docker/Dockerfile.rocm": r"""
ARG BASE_IMAGE=rocm/dev-ubuntu-24.04:6.2
FROM ${BASE_IMAGE}
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build git python3 ca-certificates \
    pkg-config ccache && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
""",
"include/lmlm/build_probe.hpp": r"""
#pragma once
namespace lmlm {
const char* build_system_version() noexcept;
}
""",
"src/build_probe.cpp": r"""
#include "lmlm/build_probe.hpp"
namespace lmlm {
const char* build_system_version() noexcept { return "0.1.0"; }
}
""",
"src/cuda_probe.cu": r"""
#include <cuda_runtime.h>
extern "C" __global__ void lmlm_cuda_probe_kernel(int* value) {
  if (threadIdx.x == 0 && blockIdx.x == 0) *value = 1;
}
""",
"src/metal_probe.mm": r"""
#import <Metal/Metal.h>
// Metal runtime integration belongs in the LMLM runtime repository.
""",
"tests/cpp/build_probe_test.cpp": r"""
#include "lmlm/build_probe.hpp"
#include <cstdlib>
#include <cstring>
int main() {
  return std::strcmp(lmlm::build_system_version(), "0.1.0") == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
""",
"scripts/lmlm-build.sh": r"""#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
unset CDPATH

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="${LMLM_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd -P)}"
PROFILE="cpu"
JOBS="${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)}"
USE_DOCKER=0
BUILD_DIR="${LMLM_BUILD_DIR:-}"
ARTIFACT_DIR="${LMLM_ARTIFACT_DIR:-${ROOT}/artifacts}"
DOCKER_BIN="${DOCKER:-docker}"
EXTRA_CMAKE_ARGS=()

log() { printf '[lmlm-build] %s\n' "$*"; }
die() { printf '[lmlm-build] ERROR: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"; }

usage() {
  cat <<'EOF'
Usage: lmlm-build.sh <doctor|configure|build|test|package|clean> [options]
Options:
  --profile cpu|cuda|rocm|metal|host
  --docker             Run build commands in a profile container
  --jobs N             Parallel build jobs
  --build-dir PATH     Override build directory
  --artifacts PATH     Override artifact directory
  -- <cmake args>      Extra arguments for configure
EOF
}

COMMAND="${1:-}"
[[ -n "${COMMAND}" ]] || { usage; exit 2; }
shift
while (($#)); do
  case "$1" in
    --profile) PROFILE="${2:?missing profile}"; shift 2 ;;
    --docker) USE_DOCKER=1; shift ;;
    --jobs) JOBS="${2:?missing job count}"; shift 2 ;;
    --build-dir) BUILD_DIR="${2:?missing build dir}"; shift 2 ;;
    --artifacts) ARTIFACT_DIR="${2:?missing artifacts dir}"; shift 2 ;;
    --) shift; EXTRA_CMAKE_ARGS+=("$@"); break ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

case "${PROFILE}" in cpu|cuda|rocm|metal|host) ;; *) die "Unsupported profile: ${PROFILE}" ;; esac
[[ "${JOBS}" =~ ^[1-9][0-9]*$ ]] || die "--jobs must be a positive integer"
[[ -n "${BUILD_DIR}" ]] || BUILD_DIR="${ROOT}/_build/${PROFILE}"
mkdir -p "${BUILD_DIR}" "${ARTIFACT_DIR}"

load_toolchain_config() {
  local config="${ROOT}/config/toolchains.env"
  [[ -f "${config}" ]] || die "Missing ${config}"
  # This file is repository-controlled shell assignments; do not source untrusted files.
  # shellcheck disable=SC1090
  source "${config}"
}

docker_image_for() {
  load_toolchain_config
  case "${PROFILE}" in
    cpu) printf '%s' "${LMLM_IMAGE_PREFIX:-lmlm-build}:cpu" ;;
    cuda) printf '%s' "${LMLM_IMAGE_PREFIX:-lmlm-build}:cuda" ;;
    rocm) printf '%s' "${LMLM_IMAGE_PREFIX:-lmlm-build}:rocm" ;;
    *) die "Docker profile is only available for cpu, cuda or rocm." ;;
  esac
}

dockerfile_for() {
  case "${PROFILE}" in
    cpu) echo docker/Dockerfile.cpu ;;
    cuda) echo docker/Dockerfile.cuda ;;
    rocm) echo docker/Dockerfile.rocm ;;
    *) die "No Dockerfile for ${PROFILE}" ;;
  esac
}

run_build() {
  local -a cmd=("$@")
  if (( USE_DOCKER )); then
    need "${DOCKER_BIN}"
    local image dockerfile base
    image="$(docker_image_for)"
    dockerfile="$(dockerfile_for)"
    load_toolchain_config
    case "${PROFILE}" in
      cpu) base="${CPU_IMAGE}" ;;
      cuda) base="${CUDA_IMAGE}" ;;
      rocm) base="${ROCM_IMAGE}" ;;
    esac
    if ! "${DOCKER_BIN}" image inspect "${image}" >/dev/null 2>&1; then
      log "Building toolchain image ${image}"
      "${DOCKER_BIN}" build --pull -f "${ROOT}/${dockerfile}" \
        --build-arg "BASE_IMAGE=${base}" -t "${image}" "${ROOT}"
    fi
    local -a gpu_args=()
    if [[ "${PROFILE}" == cuda ]]; then gpu_args+=(--gpus all); fi
    "${DOCKER_BIN}" run --rm "${gpu_args[@]}" \
      --user "$(id -u):$(id -g)" \
      --mount "type=bind,src=${ROOT},dst=/workspace,readonly" \
      --mount "type=bind,src=${BUILD_DIR},dst=/build" \
      --mount "type=bind,src=${ARTIFACT_DIR},dst=/artifacts" \
      --workdir /workspace \
      "${image}" "${cmd[@]/${ROOT}/\/workspace}"
  else
    "${cmd[@]}"
  fi
}

configure() {
  need cmake
  need ninja
  local -a args=(-S "${ROOT}" -B "${BUILD_DIR}" -G Ninja
    -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
    -DLMLM_ENABLE_CPU=ON -DLMLM_ENABLE_CUDA=OFF
    -DLMLM_ENABLE_ROCM=OFF -DLMLM_ENABLE_METAL=OFF)
  case "${PROFILE}" in
    cuda) args+=(-DLMLM_ENABLE_CUDA=ON) ;;
    rocm) args+=(-DLMLM_ENABLE_ROCM=ON) ;;
    metal) args+=(-DLMLM_ENABLE_METAL=ON) ;;
  esac
  args+=("${EXTRA_CMAKE_ARGS[@]}")
  run_build cmake "${args[@]}"
}

case "${COMMAND}" in
  doctor)
    for tool in cmake ninja; do
      if command -v "${tool}" >/dev/null 2>&1; then
        log "${tool}: $(command -v "${tool}")"
      else
        log "${tool}: MISSING"
      fi
    done
    if command -v "${DOCKER_BIN}" >/dev/null 2>&1; then
      log "docker: $(command -v "${DOCKER_BIN}")"
      "${DOCKER_BIN}" info >/dev/null 2>&1 && log "Docker daemon: reachable" || log "Docker daemon: unavailable"
    else
      log "docker: MISSING"
    fi
    if command -v nvidia-smi >/dev/null 2>&1; then nvidia-smi || true; else log "NVIDIA GPU utility: not detected"; fi
    if command -v rocminfo >/dev/null 2>&1; then rocminfo | head -n 30 || true; else log "ROCm utility: not detected"; fi
    if [[ "$(uname -s)" == Darwin ]]; then log "Apple host detected; Metal profile can use Xcode/Apple Clang."; fi
    ;;
  configure) configure ;;
  build)
    [[ -f "${BUILD_DIR}/build.ninja" ]] || configure
    run_build cmake --build "${BUILD_DIR}" --parallel "${JOBS}"
    ;;
  test)
    [[ -f "${BUILD_DIR}/build.ninja" ]] || configure
    run_build ctest --test-dir "${BUILD_DIR}" --output-on-failure
    ;;
  package)
    [[ -f "${BUILD_DIR}/build.ninja" ]] || configure
    run_build cmake --build "${BUILD_DIR}" --parallel "${JOBS}"
    run_build cmake --install "${BUILD_DIR}" --prefix "${ARTIFACT_DIR}/install"
    log "Installed artifacts: ${ARTIFACT_DIR}/install"
    ;;
  clean)
    case "${BUILD_DIR}" in "${ROOT}"/_build/*) rm -rf -- "${BUILD_DIR}" ;; *) die "Refusing to clean build directory outside ${ROOT}/_build" ;; esac
    log "Removed ${BUILD_DIR}"
    ;;
  *) usage; die "Unknown command: ${COMMAND}" ;;
esac
""",
"tests/shell/test_cli.sh": r"""#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
SCRIPT="${ROOT}/scripts/lmlm-build.sh"
"${SCRIPT}" --help >/dev/null
if "${SCRIPT}" nonsense >/dev/null 2>&1; then
  echo "Expected invalid command to fail" >&2
  exit 1
fi
if "${SCRIPT}" configure --profile invalid >/dev/null 2>&1; then
  echo "Expected invalid profile to fail" >&2
  exit 1
fi
echo "CLI smoke tests passed"
""",
".gitignore": r"""
_build/
artifacts/
.cache/
compile_commands.json
""",
}
for name, content in files.items():
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
(root / "scripts/lmlm-build.sh").chmod(0o755)
(root / "tests/shell/test_cli.sh").chmod(0o755)

# Include a minimal CI workflow.
ci = root / ".github/workflows/build.yml"
ci.parent.mkdir(parents=True, exist_ok=True)
ci.write_text(textwrap.dedent(r"""
name: LMLM Build
on:
  push:
  pull_request:
  workflow_dispatch:
jobs:
  cpu:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - name: Install build tools
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake ninja-build
      - name: Configure
        run: ./scripts/lmlm-build.sh configure --profile cpu
      - name: Build
        run: ./scripts/lmlm-build.sh build --profile cpu
      - name: Test
        run: |
          ./scripts/lmlm-build.sh test --profile cpu
          ./tests/shell/test_cli.sh
      - name: Package
        run: ./scripts/lmlm-build.sh package --profile cpu
      - uses: actions/upload-artifact@v4
        with:
          name: lmlm-cpu-install
          path: artifacts/install/
""").lstrip("\n"), encoding="utf-8")

zip_path = Path("/mnt/data/lmlm-build-system.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for p in root.rglob("*"):
        if p.is_file():
            z.write(p, p.relative_to(root.parent))
print(f"Created {zip_path} ({zip_path.stat().st_size} bytes)")
