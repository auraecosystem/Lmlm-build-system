# LMLM Build Fabric

A self-contained build orchestration layer for LMLM native components. This first
implementation establishes a tested CPU baseline and explicit, opt-in accelerator
profiles. It does not modify the repository's existing root files.

## Requirements

- CMake 3.24+
- Ninja 1.10+
- C++20 compiler
- Bash 4+ for the command-line driver
- Optional: CUDA Toolkit, ROCm/HIP toolchain, or macOS/Xcode for Metal

## Quick start

```bash
./lmlm-build/scripts/lmlm-build.sh doctor
./lmlm-build/scripts/lmlm-build.sh configure --profile cpu
./lmlm-build/scripts/lmlm-build.sh build --profile cpu
./lmlm-build/scripts/lmlm-build.sh test --profile cpu
./lmlm-build/scripts/lmlm-build.sh package --profile cpu
```

Build directories are isolated by profile under `lmlm-build/_build/`.

## Profiles

| Profile | Toolchain | Notes |
|---|---|---|
| cpu | Host C++ compiler | Portable baseline; always available with CMake/compiler |
| cuda | NVIDIA CUDA Toolkit | Requires nvcc and a supported host compiler |
| rocm | AMD HIP/ROCm | Requires ROCm compiler and CMake HIP support |
| metal | Apple Clang + Metal framework | macOS only; never configured in Linux CI |

Accelerator profiles are compile-time selections, not hardware detection. A successful
compile does not prove runtime device access or kernel correctness on physical hardware.
CUDA, HIP, and Metal runtime integration must be validated on their respective devices.

## CLI

```text
lmlm-build.sh <doctor|configure|build|test|package|clean>
  [--profile cpu|cuda|rocm|metal]
  [--jobs N]
  [--build-dir PATH]
  [--artifacts PATH]
  [-- <additional CMake configure arguments>]
```

## Design and safety

- CPU is the default and remains independent of accelerator SDKs.
- Each accelerator is configured in a separate build tree.
- No privileged container, Docker socket, or implicit GPU access is used.
- Build and artifact directories are explicit; clean refuses paths outside this module's
  `_build` directory.
- CI runs the CPU profile only. Hardware-specific jobs should be added only on verified
  self-hosted runners with the corresponding SDK and device.
- No secrets are passed to CMake or build subprocesses by this driver.

## Integration boundary

This module currently builds a small probe library to validate the build fabric itself.
It is not yet wired to LMLM runtime targets. Integrating runtime source requires an
explicit target contract from the runtime repository; no external project source is
vendored or linked here.
