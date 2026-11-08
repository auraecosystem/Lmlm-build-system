#!/usr/bin/env bash
set -Eeuo pipefail
unset CDPATH

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
PROFILE=cpu
JOBS="${JOBS:-2}"
BUILD_DIR=""
ARTIFACT_DIR="${ROOT}/artifacts"
COMPILER=""
TOOLCHAIN_FILE=""
JSON_OUTPUT=0
EXTRA_ARGS=()

log() { printf '[lmlm-build] %s\n' "$*"; }
die() { printf '[lmlm-build] ERROR: %s\n' "$*" >&2; exit 2; }
need() { command -v "$1" >/dev/null 2>&1 || die "Missing required tool: $1"; }
usage() {
  cat <<'USAGE'
Usage: lmlm-build.sh <doctor|capabilities|configure|build|test|package|clean>
  [--profile cpu|cuda|rocm|metal] [--jobs N]
  [--compiler PATH] [--toolchain-file PATH]
  [--build-dir PATH] [--artifacts PATH] [--json]
  [-- <additional CMake configure arguments>]
USAGE
}

COMMAND="${1:-}"
[[ -n "$COMMAND" ]] || { usage; exit 2; }
if [[ "$COMMAND" == "-h" || "$COMMAND" == "--help" ]]; then usage; exit 0; fi
shift
while (($#)); do
  case "$1" in
    --profile) PROFILE="${2:?missing profile}"; shift 2 ;;
    --jobs) JOBS="${2:?missing job count}"; shift 2 ;;
    --compiler) COMPILER="${2:?missing compiler}"; shift 2 ;;
    --toolchain-file) TOOLCHAIN_FILE="${2:?missing toolchain file}"; shift 2 ;;
    --build-dir) BUILD_DIR="${2:?missing build directory}"; shift 2 ;;
    --artifacts) ARTIFACT_DIR="${2:?missing artifact directory}"; shift 2 ;;
    --json) JSON_OUTPUT=1; shift ;;
    --) shift; EXTRA_ARGS=("$@"); break ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done
case "$PROFILE" in cpu|cuda|rocm|metal) ;; *) die "Unsupported profile: $PROFILE" ;; esac
[[ "$JOBS" =~ ^[1-9][0-9]*$ ]] || die "jobs must be a positive integer"
[[ -n "$BUILD_DIR" ]] || BUILD_DIR="${ROOT}/_build/$PROFILE"

tool_path() {
  local found
  found="$(command -v "$1" 2>/dev/null || true)"
  if [[ -n "$found" ]]; then printf '%s' "$found"; else printf ''; fi
}
json_tool() {
  local name="$1" path
  path="$(tool_path "$name")"
  if [[ -n "$path" ]]; then
    printf '"%s":{"available":true,"path":"%s"}' "$name" "$path"
  else
    printf '"%s":{"available":false,"path":null}' "$name"
  fi
}
doctor() {
  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"
  if ((JSON_OUTPUT)); then
    printf '{"host":{"os":"%s","architecture":"%s"},"tools":{' "$os" "$arch"
    local first=1 tool
    for tool in cmake ninja clang clang++ llvm-config c++ python3 git nvcc hipcc xcrun; do
      ((first)) || printf ','
      json_tool "$tool"
      first=0
    done
    printf '}}\n'
  else
    log "Host: $os / $arch"
    local tool
    for tool in cmake ninja clang clang++ llvm-config c++ python3 git nvcc hipcc xcrun; do
      if command -v "$tool" >/dev/null 2>&1; then
        log "$tool: available ($(command -v "$tool"))"
      else
        log "$tool: not found"
      fi
    done
  fi
}

configure() {
  need cmake
  need ninja
  if [[ -n "$COMPILER" ]]; then
    command -v "$COMPILER" >/dev/null 2>&1 || [[ -x "$COMPILER" ]] || die "C++ compiler not found or not executable: $COMPILER"
  fi
  if [[ -n "$TOOLCHAIN_FILE" && ! -f "$TOOLCHAIN_FILE" ]]; then
    die "CMake toolchain file does not exist: $TOOLCHAIN_FILE"
  fi
  local -a args=(-S "$ROOT" -B "$BUILD_DIR" -G Ninja
    -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON)
  case "$PROFILE" in
    cuda) args+=(-DLMLM_ENABLE_CUDA=ON) ;;
    rocm) args+=(-DLMLM_ENABLE_ROCM=ON) ;;
    metal) args+=(-DLMLM_ENABLE_METAL=ON) ;;
  esac
  [[ -z "$COMPILER" ]] || args+=("-DCMAKE_CXX_COMPILER=$COMPILER")
  [[ -z "$TOOLCHAIN_FILE" ]] || args+=("-DCMAKE_TOOLCHAIN_FILE=$TOOLCHAIN_FILE")
  args+=("${EXTRA_ARGS[@]}")
  cmake "${args[@]}"
}
ensure_configured() {
  [[ -f "$BUILD_DIR/build.ninja" ]] || configure
}
case "$COMMAND" in
  doctor) doctor ;;
  capabilities)
    need cmake
    ensure_configured
    cmake --build "$BUILD_DIR" --target lmlm_cpu_capabilities --parallel "$JOBS"
    "$BUILD_DIR/lmlm_cpu_capabilities"
    ;;
  configure) configure ;;
  build) ensure_configured; cmake --build "$BUILD_DIR" --parallel "$JOBS" ;;
  test) ensure_configured; cmake --build "$BUILD_DIR" --parallel "$JOBS"; ctest --test-dir "$BUILD_DIR" --output-on-failure ;;
  package)
    need cmake
    ensure_configured
    mkdir -p "$ARTIFACT_DIR"
    cmake --build "$BUILD_DIR" --parallel "$JOBS"
    cmake --install "$BUILD_DIR" --prefix "$ARTIFACT_DIR/install"
    log "Package staged at $ARTIFACT_DIR/install"
    ;;
  clean)
    case "$BUILD_DIR" in "${ROOT}"/_build/*) rm -rf -- "$BUILD_DIR"; log "Removed $BUILD_DIR" ;; *) die "Refusing to clean outside ${ROOT}/_build" ;; esac
    ;;
  *) usage; die "Unknown command: $COMMAND" ;;
esac
