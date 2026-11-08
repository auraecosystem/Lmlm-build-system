# LMLM Build Fabric

A self-contained build orchestration layer for native LMLM components. Version 0.2 adds
runtime CPU feature reporting and executable accelerator device/kernel probes.

## Requirements

- CMake 3.24+
- Ninja 1.10+
- C++20 compiler
- Bash 4+ for the CLI
- Optional accelerator SDKs: NVIDIA CUDA Toolkit, AMD ROCm/HIP, or macOS/Xcode

## Quick start

```bash
./lmlm-build/scripts/lmlm-build.sh doctor
./lmlm-build/scripts/lmlm-build.sh configure --profile cpu
./lmlm-build/scripts/lmlm-build.sh build --profile cpu
./lmlm-build/scripts/lmlm-build.sh test --profile cpu
./lmlm-build/scripts/lmlm-build.sh capabilities --profile cpu
./lmlm-build/scripts/lmlm-build.sh package --profile cpu
```

Build directories are isolated by profile under `lmlm-build/_build/`.

## Backend profiles

| Profile | Probe | Requirements |
|---|---|---|
| cpu | Runtime architecture and SIMD feature detection | Host C++ compiler |
| cuda | Enumerates CUDA devices, launches a kernel, verifies result | CUDA Toolkit, supported host compiler, NVIDIA device for runtime pass |
| rocm | Enumerates HIP devices, launches a kernel, verifies result | ROCm/HIP toolchain and supported AMD device |
| metal | Enumerates Metal devices through Metal framework | macOS and Xcode/Apple Clang |

Configure one accelerator profile per build tree. A successful accelerator compile proves
toolchain integration only. Device enumeration and kernel execution require matching
hardware and runtime drivers. A machine without an accelerator reports unavailable rather
than pretending the backend passed.

## CLI

```text
lmlm-build.sh <doctor|capabilities|configure|build|test|package|clean>
  [--profile cpu|cuda|rocm|metal]
  [--jobs N] [--build-dir PATH] [--artifacts PATH]
  [-- <additional CMake configure arguments>]
```

## Architecture boundary

This repository owns the build fabric, capability probes, and backend build targets.
It does not vendor or automatically link LMLM runtime source. Runtime integration requires
an explicit public target contract (target names, include directories, compile features,
and backend registration API) supplied by the runtime implementation. Until then, this
module validates the toolchain and device layer independently.

## Security and reproducibility

- CPU is the default; accelerator SDKs are opt-in.
- Each accelerator uses a separate build tree.
- No privileged container or implicit GPU access is used.
- The clean command refuses paths outside this module's `_build` directory.
- CI validates CPU only; hardware-specific jobs require verified hardware runners.
