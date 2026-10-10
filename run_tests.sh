#!/bin/bash
# Run the cawg-test-suite tests. Extra arguments are passed to pytest.
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"
# Use $PYTHON if set, else the repo's .venv, else python3.
if [ -z "$PYTHON" ]; then
    if [ -x .venv/bin/python ]; then PYTHON=.venv/bin/python; else PYTHON=python3; fi
fi
"$PYTHON" -m pytest tests "$@"
