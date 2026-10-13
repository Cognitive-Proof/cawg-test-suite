#!/usr/bin/env python3
"""Check a validator's crJSON output against the core CAWG validator cases.

Usage:
    python validator_tests/check_validator.py <crjson-dir> [--cases FILE ...]
        [--baseline baselines/<validator>.yml] [--json]

A wrapper for `cawg-suite check-validator` that defaults to the core suite's
cases (cawg-tests.yml). See cawg_rubric/validator.py.
"""

import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
sys.path.insert(0, REPO_ROOT)

from cawg_rubric import validator  # noqa: E402
from cawg_rubric.validator import check_case, load_known_failures  # noqa: E402,F401

DEFAULT_CASES = sorted(glob.glob(os.path.join(HERE, "*-cases.yml")))


def load_cases(cases_paths=None):
    return validator.load_cases(cases_paths or DEFAULT_CASES)


def run(crjson_dir, cases_paths=None):
    return validator.run(crjson_dir, cases_paths or DEFAULT_CASES)


def main(argv=None):
    return validator.main(argv, default_project=os.path.join(REPO_ROOT, "cawg-tests.yml"))


if __name__ == "__main__":
    sys.exit(main())
