#!/usr/bin/env bash
set -Eeuo pipefail
MODULE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
CLI="$MODULE_ROOT/scripts/lmlm-build.sh"
"$CLI" --help >/dev/null
"$CLI" doctor --json | grep -q '"host"'
"$CLI" doctor --json | grep -q '"clang"'
if "$CLI" nonsense >/dev/null 2>&1; then
  echo "invalid command unexpectedly succeeded" >&2
  exit 1
fi
if "$CLI" configure --profile invalid >/dev/null 2>&1; then
  echo "invalid profile unexpectedly succeeded" >&2
  exit 1
fi
if "$CLI" configure --toolchain-file "$MODULE_ROOT/does-not-exist.cmake" >/dev/null 2>&1; then
  echo "missing toolchain file unexpectedly succeeded" >&2
  exit 1
fi
echo "CLI tests passed"
