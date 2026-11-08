# Native Toolchain Orchestration

## Scope

The build script is the operator-facing entry point for the native build fabric. It reports
the available toolchain, selects a compiler, configures an isolated backend profile, builds,
tests, stages install artifacts, and accepts explicit CMake cross-compilation toolchains.

## Toolchain layers

1. **Build orchestration:** Bash CLI, CMake, Ninja.
2. **Compiler layer:** C++20 host compiler; Clang/LLVM are detected and can be selected.
3. **Host baseline:** CPU feature probe and portable tests.
4. **Accelerator SDKs:** CUDA, ROCm/HIP, and Apple Metal are independent opt-in profiles.
5. **Cross compilation:** platform-owned CMake toolchain file, sysroot, and SDK.
6. **Runtime integration:** explicit LMLM runtime target contract; never inferred.

## Commands

- `doctor [--json]`: inspect host and toolchain availability.
- `configure --profile PROFILE [--compiler PATH] [--toolchain-file FILE]`: configure.
- `build`, `test`, `capabilities`, `package`, `clean`: operate on the selected profile.

## Cross-compilation contract

The caller must provide a valid CMake toolchain file. It is responsible for target system,
processor, compiler, sysroot, SDK, and emulator settings. The build fabric validates that
the file exists and passes it to CMake; it does not invent target settings.

## Validation levels

- Configure: compiler, generator, SDK, and toolchain file are accepted by CMake.
- Compile: native or accelerator targets build.
- Test: tests execute on the host or configured emulator.
- Device: a physical accelerator is enumerated.
- Kernel: an accelerator kernel executes and its result is checked.
- Runtime integration: the actual LMLM runtime target links and passes its own tests.

A passing CPU CI run validates only the CPU path and generic orchestration.
