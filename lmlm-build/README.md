# LMLM Build Fabric

A self-contained native build orchestrator for LMLM components. Version 0.3 adds compiler
selection, cross-compilation toolchain-file support, machine-readable toolchain diagnostics,
and CMake presets for the supported backend profiles.

## Quick start

```bash
./lmlm-build/scripts/lmlm-build.sh doctor
./lmlm-build/scripts/lmlm-build.sh doctor --json
./lmlm-build/scripts/lmlm-build.sh configure --profile cpu
./lmlm-build/scripts/lmlm-build.sh build --profile cpu
./lmlm-build/scripts/lmlm-build.sh test --profile cpu
./lmlm-build/scripts/lmlm-build.sh capabilities --profile cpu
./lmlm-build/scripts/lmlm-build.sh package --profile cpu
```

Build trees are isolated by backend profile under `lmlm-build/_build/`.

## Compiler and cross-compilation

Select a compiler explicitly:

```bash
./lmlm-build/scripts/lmlm-build.sh configure --profile cpu --compiler clang++
```

Pass a CMake toolchain file for cross-compilation (for example, an SDK or target sysroot
provided by your platform toolchain):

```bash
./lmlm-build/scripts/lmlm-build.sh configure --profile cpu \
  --toolchain-file /absolute/path/to/target-toolchain.cmake
```

The toolchain file is intentionally supplied by the target platform owner. This repository
does not guess target triples, sysroots, SDK paths, or deployable hardware targets.
Use `-- <CMake arguments>` for additional CMake configuration values.

Equivalent IDE/GUI presets are provided in `lmlm-build/CMakePresets.json`:
`lmlm-cpu`, `lmlm-cuda`, `lmlm-rocm`, and `lmlm-metal`.

## Backend profiles

| Profile | Probe | Requirements |
|---|---|---|
| cpu | Architecture and SIMD capability report | C++20 compiler |
| cuda | Device enumeration and verified kernel | CUDA Toolkit and NVIDIA device for runtime pass |
| rocm | HIP device enumeration and verified kernel | ROCm/HIP toolchain and AMD device |
| metal | Metal device enumeration | macOS and Xcode/Apple Clang |

Accelerator profiles are opt-in and isolated. A successful compile does not prove device
execution. CPU CI does not validate physical CUDA, ROCm, or Metal hardware.

## Toolchain diagnostics

`doctor` reports host architecture and availability of CMake, Ninja, LLVM/Clang,
the host C++ compiler, Python, Git, and accelerator SDK entry points. Use `--json` for
automation and environment capture. Missing optional tools are reported, not treated as
fatal for the CPU baseline.

## Runtime boundary

The build fabric owns toolchain configuration, native compilation, backend probes, tests,
and package staging. The LMLM runtime owns model execution, scheduling, memory management,
device policy, and kernel dispatch. Runtime linkage remains opt-in and requires an explicit
target/header/ABI/backend-registration contract; no source is silently cloned or vendored.

## Safety and reproducibility

- CPU remains the default and does not require accelerator SDKs.
- Each backend uses a separate build directory.
- Cross-compilation requires an explicit, existing toolchain file.
- The clean command refuses paths outside this module's `_build` directory.
- Hardware validation is reported separately from compile/configure validation.
