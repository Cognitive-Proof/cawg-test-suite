"""Validator cases: structure checks and the c2pa-rs baseline."""
import os

import yaml

from conftest import FIXTURES, REPO_ROOT
from validator_tests import check_validator

CASES_PATH = os.path.join(REPO_ROOT, "validator_tests", "cases.yml")
BASELINE = os.path.join(REPO_ROOT, "validator_tests", "baselines", "c2pa-rs-0.91.2.yml")


def _cases():
    with open(CASES_PATH) as f:
        return yaml.safe_load(f)["cases"]


def test_case_ids_unique():
    ids = [c["id"] for c in _cases()]
    assert len(ids) == len(set(ids))


def test_case_assets_exist():
    missing = [c["asset"] for c in _cases()
               if not os.path.exists(os.path.join(FIXTURES, "assets", c["asset"]))]
    assert not missing


def test_every_asset_has_a_case():
    assets_dir = os.path.join(FIXTURES, "assets")
    on_disk = {os.path.relpath(os.path.join(d, f), assets_dir)
               for d, _, files in os.walk(assets_dir) for f in files if not f.startswith(".")}
    assert on_disk == {c["asset"] for c in _cases()}


def test_c2pa_rs_baseline_matches():
    results = check_validator.run(os.path.join(FIXTURES, "crjson"), CASES_PATH)
    failed = {case["id"] for case, problems in results if problems}
    assert failed == check_validator.load_known_failures(BASELINE)


def test_consistency_rule_flags_success_with_failure():
    url = "self#jumbf=/c2pa/urn:c2pa:x/c2pa.assertions/cawg.identity"
    crjson = {"manifests": [{"validationResults": {
        "success": [{"code": "cawg.identity.well-formed", "url": url}],
        "failure": [{"code": "cawg.identity.pad.invalid", "url": url}]}}]}
    problems = check_validator.check_case({"expect_failure": ["cawg.identity.pad.invalid"]}, crjson)
    assert problems == ["cawg.identity.well-formed reported alongside a cawg.identity.* failure"]
