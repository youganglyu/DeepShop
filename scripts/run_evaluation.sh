#!/bin/sh
set -eu

REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PYTHON:-python3}

"$PYTHON_BIN" "$REPO_DIR/src/evaluation/evaluation_common.py" "$@"
printf '%s\n' 'Evaluation command completed.'
