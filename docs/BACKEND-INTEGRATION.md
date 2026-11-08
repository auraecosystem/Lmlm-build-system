# Backend and Runtime Integration Contract

## Responsibilities

The build fabric owns toolchain configuration, native compilation, hardware capability
probes, tests, and installable build artifacts. LMLM Runtime remains the owner of model
execution, scheduling, memory management, device selection policy, and kernel dispatch.

## Current backend contract

| Backend | Build target | Runtime validation |
|---|---|---|
| CPU | `lmlm_build_probe`, `lmlm_cpu_capabilities` | Host architecture and SIMD feature report |
| CUDA | `lmlm_cuda_probe` | CUDA device enumeration and verified kernel result |
| ROCm/HIP | `lmlm_rocm_probe` | HIP device enumeration and verified kernel result |
| Metal | `lmlm_metal_probe` | Metal device enumeration |

Each accelerator is opt-in and configured in a separate build directory. CPU builds must
not require accelerator SDKs.

## Runtime target integration requirements

A runtime integration change must be based on an explicit target contract from the runtime
source owner. At minimum, that contract must identify:

1. CMake target name(s) and whether they are created by `add_subdirectory` or package import.
2. Public headers and include directory ownership.
3. Required C++ standard, compiler constraints, and ABI settings.
4. Backend registration interface and ownership of device discovery.
5. Static/shared linkage requirements and transitive dependencies.
6. Cross-compilation and supported operating-system constraints.
7. Tests that can run without physical accelerators and tests requiring hardware.

The build fabric must not guess a runtime target name, clone another repository, or silently
vendor source. An integration can then be added as an explicit opt-in CMake option with
clear path validation and isolated build presets.

## Validation levels

- **Configure:** CMake finds the requested compiler and SDK.
- **Compile:** backend probe executable builds.
- **Device:** runtime enumerates at least one compatible device.
- **Kernel:** backend launches a minimal operation and verifies its result.
- **Runtime integration:** the actual LMLM runtime target links and passes its own tests.

These levels are distinct. CPU CI does not establish CUDA, ROCm, or Metal device validation.
