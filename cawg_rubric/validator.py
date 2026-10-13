"""Check a validator's crJSON output against validator conformance cases.

Usage:
    cawg-suite check-validator <crjson-dir> [--project PATH] [--cases FILE ...]
        [--baseline baselines/<validator>.yml] [--json]

The cases and subjects come from a project: the core cawg-tests.yml or a
plugin's cawg-plugin.yml (default: whichever is in the current directory).

<crjson-dir> mirrors the project's assets_root: the validator's crJSON for
<assets_root>/<path>/<name>.jpg must be at <crjson-dir>/<path>/<name>.crjson.json.

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

from .manifest import ManifestError, find_manifest, load_project, load_suite

# Which status entries a case looks at, by subject name (cawg_rubric/suite.yml).
# Plugins can add subjects; pass the project's subject_patterns() to check_case.
SUBJECT_URLS = {k: re.compile(v) for k, v in load_suite().subjects.items()}
SUCCESS_CODES = {"cawg.identity.well-formed", "cawg.identity.trusted"}
CONSISTENCY_EXEMPT = {"cawg.x509.credential.untrusted"}


def crjson_path(crjson_dir, asset):
    return os.path.join(crjson_dir, os.path.splitext(asset)[0] + ".crjson.json")


def subject_statuses(crjson, subject="identity", subjects=None):
    """Return {category: [(url, code), ...]} for status entries on the case's subject."""
    pattern = (subjects or SUBJECT_URLS)[subject]
    out = {"success": [], "informational": [], "failure": []}
    for manifest in crjson.get("manifests", []):
        results = manifest.get("validationResults") or {}
        for category in out:
            for entry in results.get(category) or []:
                url = entry.get("url") or ""
                if pattern.search(url):
                    out[category].append((url, entry.get("code")))
    return out


def check_case(case, crjson, subjects=None):
    """Return a list of problems (empty list means the case passed)."""
    subjects = subjects or SUBJECT_URLS
    subject = case.get("subject", "identity")
    if subject not in subjects:
        return [f"unknown subject {subject!r} (known: {', '.join(sorted(subjects))})"]
    statuses = subject_statuses(crjson, subject, subjects)
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

    if case.get("per_assertion") and any_of:
        # Each assertion of the subject type must carry one of expect_any under
        # its own label (so multiple instances can be told apart).
        pattern = subjects[subject]
        labels = {label for m in crjson.get("manifests", [])
                  for label in (m.get("assertions") or {}) if pattern.search(label)}
        for label in sorted(labels):
            own = {c for entries in statuses.values() for u, c in entries
                   if u == label or u.endswith("/" + label)}
            if not own.intersection(any_of):
                problems.append(f"no {' / '.join(any_of)} status for {label}")

    if case.get("forbid_any_failure") and codes["failure"]:
        problems.append(f"unexpected failure code(s) {', '.join(sorted(codes['failure']))}")

    if subject != "identity":
        return problems

    # Consistency: no well-formed/trusted on an assertion that has a cawg.* failure.
    # §7.2 defines those success codes as "validated"; §7.1, §8.1.5 and §8.2.2
    # failures reject the assertion. cawg.x509.credential.untrusted is excluded:
    # §8.2.2 calls it a rejection, but §7.2 defines well-formed as "validated, no
    # root of trust identified", which is exactly an untrusted chain (TODO.md).
    failed_urls = {u for u, c in statuses["failure"]
                   if c.startswith("cawg.") and c not in CONSISTENCY_EXEMPT}
    for url, code in statuses["success"]:
        if code in SUCCESS_CODES and url in failed_urls:
            problems.append(f"{code} reported alongside a cawg.* failure")
            break
    return problems


def load_cases(cases_paths):
    """Load cases from one or more case files; a file-level subject applies to its cases."""
    if isinstance(cases_paths, str):
        cases_paths = [cases_paths]
    cases = []
    for path in cases_paths:
        with open(path) as f:
            doc = yaml.safe_load(f)
        for case in doc["cases"]:
            case.setdefault("subject", doc.get("subject", "identity"))
            cases.append(case)
    return cases


def run(crjson_dir, cases_paths, subjects=None):
    """Return a list of (case, problems) tuples."""
    results = []
    for case in load_cases(cases_paths):
        path = crjson_path(crjson_dir, case["asset"])
        if not os.path.exists(path):
            results.append((case, [f"no crJSON at {path}"]))
            continue
        with open(path) as f:
            results.append((case, check_case(case, json.load(f), subjects)))
    return results


def load_known_failures(baseline_path):
    with open(baseline_path) as f:
        doc = yaml.safe_load(f) or {}
    return {k["id"] for k in doc.get("known_failures") or []}


def add_arguments(parser):
    parser.add_argument("crjson_dir")
    parser.add_argument("--project", help="cawg-tests.yml, cawg-plugin.yml or a directory with one "
                                          "(default: the current directory)")
    parser.add_argument("--cases", nargs="+", help="Case files (default: the project's validator_cases)")
    parser.add_argument("--baseline", help="YAML file listing known_failures for this validator")
    parser.add_argument("--json", action="store_true", help="Print results as JSON")


def main(argv=None, default_project="."):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    add_arguments(parser)
    return run_cli(parser.parse_args(argv), default_project)


def run_cli(args, default_project="."):
    try:
        project = load_project(find_manifest(args.project or default_project))
    except ManifestError as e:
        print(e, file=sys.stderr)
        return 2
    cases = args.cases or project.case_files()
    if not cases:
        print(f"{project.path}: no validator cases", file=sys.stderr)
        return 2
    results = run(args.crjson_dir, cases, project.subject_patterns())
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
