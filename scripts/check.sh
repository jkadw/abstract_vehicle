#!/bin/sh

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN="${PYTHON:-python3}"

printf '%s\n' "Running syntax checks..."
"$PYTHON_BIN" -m compileall -q "$ROOT_DIR/custom_components" "$ROOT_DIR/tests"

printf '%s\n' "Running tests..."
if command -v pytest >/dev/null 2>&1; then
    pytest -q "$ROOT_DIR/tests"
else
    "$PYTHON_BIN" -m pytest -q "$ROOT_DIR/tests"
fi
