#!/usr/bin/env python3
"""Check a validator's crJSON output against the CAWG validator conformance cases.

Usage:
    python validator_tests/check_validator.py <crjson-dir> [--cases cases.yml]
        [--baseline baselines/<validator>.yml] [--json]

<crjson-dir> mirrors fixtures/assets/: the validator's crJSON for
fixtures/assets/<path>/<name>.jpg must be at <crjson-dir>/<path>/<name>.crjson.json.

Exit status is 0 when every case passes. With --baseline, exit status is 0 when
exactly the cases listed in the baseline's known_failures fail, so CI notices
both regressions and fixes.
"""

import argparse
import json
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CASES = os.path.join(HERE, "cases.yml")

IDENTITY_URL = re.compile(r"(^|/)cawg\.identity(__\d+)?$")
SUCCESS_CODES = {"cawg.identity.well-formed", "cawg.identity.trusted"}


def crjson_path(crjson_dir, asset):
    return os.path.join(crjson_dir, os.path.splitext(asset)[0] + ".crjson.json")


def identity_statuses(crjson):
    """Return {category: [(url, code), ...]} for status entries on identity assertions."""
    out = {"success": [], "informational": [], "failure": []}
    for manifest in crjson.get("manifests", []):
        results = manifest.get("validationResults") or {}
        for category in out:
            for entry in results.get(category) or []:
                url = entry.get("url") or ""
                if IDENTITY_URL.search(url):
                    out[category].append((url, entry.get("code")))
    return out


def check_case(case, crjson):
    """Return a list of problems (empty list means the case passed)."""
    statuses = identity_statuses(crjson)
    codes = {cat: {c for _, c in entries} for cat, entries in statuses.items()}
    all_codes = set().union(*codes.values())
    problems = []

    for code in case.get("expect_failure", []):
        if code not in codes["failure"]:
            problems.append(f"missing failure code {code}")
    for code in case.get("expect_success", []):
        if code not in codes["success"]:
            problems.append(f"missing success code {code}")
    any_of = case.get("expect_any", [])
    if any_of and not all_codes.intersection(any_of):
        problems.append(f"missing one of {', '.join(any_of)}")
    for prefix in case.get("forbid_failure_prefixes", []):
        bad = sorted(c for c in codes["failure"] if c.startswith(prefix))
        if bad:
            problems.append(f"unexpected failure code(s) {', '.join(bad)}")

    # Consistency: no well-formed/trusted on an assertion with a cawg.identity.* failure.
    failed_urls = {u for u, c in statuses["failure"] if c.startswith("cawg.identity.")}
    for url, code in statuses["success"]:
        if code in SUCCESS_CODES and url in failed_urls:
            problems.append(f"{code} reported alongside a cawg.identity.* failure")
            break
    return problems


def run(crjson_dir, cases_path=DEFAULT_CASES):
    """Return a list of (case, problems) tuples."""
    with open(cases_path) as f:
        cases = yaml.safe_load(f)["cases"]
    results = []
    for case in cases:
        path = crjson_path(crjson_dir, case["asset"])
        if not os.path.exists(path):
            results.append((case, [f"no crJSON at {path}"]))
            continue
        with open(path) as f:
            results.append((case, check_case(case, json.load(f))))
    return results


def load_known_failures(baseline_path):
    with open(baseline_path) as f:
        doc = yaml.safe_load(f) or {}
    return {k["id"] for k in doc.get("known_failures") or []}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("crjson_dir")
    parser.add_argument("--cases", default=DEFAULT_CASES)
    parser.add_argument("--baseline", help="YAML file listing known_failures for this validator")
    parser.add_argument("--json", action="store_true", help="Print results as JSON")
    args = parser.parse_args(argv)

    results = run(args.crjson_dir, args.cases)
    failed = {case["id"] for case, problems in results if problems}

    if args.json:
        print(json.dumps([{"id": c["id"], "asset": c["asset"], "level": c.get("level", "must"),
                           "passed": not p, "problems": p} for c, p in results], indent=2))
    else:
        for case, problems in results:
            status = "PASS" if not problems else "FAIL"
            level = case.get("level", "must").upper()
            print(f"{status}  [{level:6}] {case['id']}")
            for p in problems:
                print(f"        - {p}")
        print(f"\n{len(results) - len(failed)}/{len(results)} cases passed")

    if args.baseline:
        known = load_known_failures(args.baseline)
        new_failures = sorted(failed - known)
        fixed = sorted(known - failed)
        if new_failures:
            print(f"New failures not in baseline: {', '.join(new_failures)}", file=sys.stderr)
        if fixed:
            print(f"Baseline failures that now pass (update the baseline): {', '.join(fixed)}",
                  file=sys.stderr)
        return 1 if new_failures or fixed else 0
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
