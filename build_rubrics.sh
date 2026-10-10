#!/bin/bash
# Build rubrics/*.rubric.yml from rubrics/composables/ and validate them.
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"
# Use $PYTHON if set, else the repo's .venv, else python3.
if [ -z "$PYTHON" ]; then
    if [ -x .venv/bin/python ]; then PYTHON=.venv/bin/python; else PYTHON=python3; fi
fi
"$PYTHON" -m cawg_rubric.build
"$PYTHON" -m cawg_rubric.validate_rubric --all
