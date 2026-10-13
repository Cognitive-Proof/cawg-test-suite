#!/bin/bash
# Build cawg_rubric/rubrics/*.rubric.yml from the composables and validate them.
# Extra arguments are passed to `cawg-suite build` (e.g. --plugin PATH).
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"
# Use $PYTHON if set, else the repo's .venv, else python3.
if [ -z "$PYTHON" ]; then
    if [ -x .venv/bin/python ]; then PYTHON=.venv/bin/python; else PYTHON=python3; fi
fi
"$PYTHON" -m cawg_rubric.cli build "$@"
