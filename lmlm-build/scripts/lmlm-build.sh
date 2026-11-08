#!/usr/bin/env bash
set -Eeuo pipefail
unset CDPATH

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
PROFILE=cpu
JOBS="${JOBS:-2}"
BUILD_DIR=""
ARTIFACT_DIR="${ROOT}/artifacts"
EXTRA_ARGS=()

log() { printf '[lmlm-build] %s\n' "$*"; }
die() { printf '[lmlm-build] ERROR: %s\n' "$*" >&2; exit 2; }
need() { command -v "$1" >/dev/null 2>&1 || die "Missing required tool: $1"; }
usage() {
  cat <<'USAGE'
Usage: lmlm-build.sh <doctor|capabilities|configure|build|test|package|clean>
  [--profile cpu|cuda|rocm|metal] [--jobs N]
  [--build-dir PATH] [--artifacts PATH] [-- CMake arguments]
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
    --build-dir) BUILD_DIR="${2:?missing build directory}"; shift 2 ;;
    --artifacts) ARTIFACT_DIR="${2:?missing artifact directory}"; shift 2 ;;
    --) shift; EXTRA_ARGS=("$@"); break ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done
case "$PROFILE" in cpu|cuda|rocm|metal) ;; *) die "Unsupported profile: $PROFILE" ;; esac
[[ "$JOBS" =~ ^[1-9][0-9]*$ ]] || die "jobs must be a positive integer"
[[ -n "$BUILD_DIR" ]] || BUILD_DIR="${ROOT}/_build/$PROFILE"
mkdir -p "$ARTIFACT_DIR"

configure() {
  need cmake
  need ninja
  local -a args=(-S "$ROOT" -B "$BUILD_DIR" -G Ninja
    -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON)
  case "$PROFILE" in
    cuda) args+=(-DLMLM_ENABLE_CUDA=ON) ;;
    rocm) args+=(-DLMLM_ENABLE_ROCM=ON) ;;
    metal) args+=(-DLMLM_ENABLE_METAL=ON) ;;
  esac
  args+=("${EXTRA_ARGS[@]}")
  cmake "${args[@]}"
}
ensure_configured() {
  [[ -f "$BUILD_DIR/build.ninja" ]] || configure
}
case "$COMMAND" in
  doctor)
    for tool in cmake ninja c++; do
      if command -v "$tool" >/dev/null 2>&1; then log "$tool: available"; else log "$tool: missing"; fi
    done
    for tool in nvcc hipcc xcrun; do
      if command -v "$tool" >/dev/null 2>&1; then log "$tool: available"; else log "$tool: not found"; fi
    done
    log "Host: $(uname -s) / $(uname -m)"
    ;;
  capabilities)
    ensure_configured
    cmake --build "$BUILD_DIR" --target lmlm_cpu_capabilities --parallel "$JOBS"
    "$BUILD_DIR/lmlm_cpu_capabilities"
    ;;
  configure) configure ;;
  build) ensure_configured; cmake --build "$BUILD_DIR" --parallel "$JOBS" ;;
  test) ensure_configured; cmake --build "$BUILD_DIR" --parallel "$JOBS"; ctest --test-dir "$BUILD_DIR" --output-on-failure ;;
  package)
    ensure_configured
    cmake --build "$BUILD_DIR" --parallel "$JOBS"
    cmake --install "$BUILD_DIR" --prefix "$ARTIFACT_DIR/install"
    log "Package staged at $ARTIFACT_DIR/install"
    ;;
  clean)
    case "$BUILD_DIR" in "${ROOT}"/_build/*) rm -rf -- "$BUILD_DIR"; log "Removed $BUILD_DIR" ;; *) die "Refusing to clean outside ${ROOT}/_build" ;; esac
    ;;
  *) usage; die "Unknown command: $COMMAND" ;;
esac
