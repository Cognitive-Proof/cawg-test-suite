"""Validator cases: structure checks and the c2pa-rs baseline."""
import os

from conftest import FIXTURES, REPO_ROOT
from validator_tests import check_validator

BASELINE = os.path.join(REPO_ROOT, "validator_tests", "baselines", "c2pa-rs-0.91.2.yml")


def _cases():
    return check_validator.load_cases()


def test_case_ids_unique():
    ids = [c["id"] for c in _cases()]
    assert len(ids) == len(set(ids))


def test_case_assets_exist():
    missing = [c["asset"] for c in _cases()
               if not os.path.exists(os.path.join(FIXTURES, "assets", c["asset"]))]
    assert not missing


# Assets that exist only to exercise generator rubrics; the spec says nothing
# about how validators should report them.
RUBRIC_ONLY_ASSETS = {
    "training-mining/invalid_use_value.jpg",
    "training-mining/undefined_cawg_key.jpg",
    "training-mining/missing_entries.jpg",
    "training-mining/constraints_info_spelling.jpg",
    "training-mining/legacy_c2pa_label.jpg",
}


def test_every_asset_has_a_case():
    assets_dir = os.path.join(FIXTURES, "assets")
    on_disk = {os.path.relpath(os.path.join(d, f), assets_dir)
               for d, _, files in os.walk(assets_dir) for f in files if not f.startswith(".")}
    assert on_disk - RUBRIC_ONLY_ASSETS == {c["asset"] for c in _cases()}


def test_c2pa_rs_baseline_matches():
    results = check_validator.run(os.path.join(FIXTURES, "crjson"))
    failed = {case["id"] for case, problems in results if problems}
    assert failed == check_validator.load_known_failures(BASELINE)


def test_consistency_rule_flags_success_with_failure():
    url = "self#jumbf=/c2pa/urn:c2pa:x/c2pa.assertions/cawg.identity"
    crjson = {"manifests": [{"validationResults": {
        "success": [{"code": "cawg.identity.well-formed", "url": url}],
        "failure": [{"code": "cawg.identity.pad.invalid", "url": url}]}}]}
    problems = check_validator.check_case({"expect_failure": ["cawg.identity.pad.invalid"]}, crjson)
    assert problems == ["cawg.identity.well-formed reported alongside a cawg.* failure"]


def test_case_files_found():
    names = {os.path.basename(p) for p in check_validator.DEFAULT_CASES}
    assert {"identity-1.3-cases.yml", "metadata-1.1-cases.yml",
            "training-mining-1.1-cases.yml"} <= names


def test_forbid_any_failure_on_manifest_subject():
    crjson = {"manifests": [{"validationResults": {"failure": [
        {"code": "assertion.metadata.disallowed",
         "url": "self#jumbf=/c2pa/urn:c2pa:x/c2pa.assertions/cawg.metadata"}]}}]}
    case = {"subject": "manifest", "forbid_any_failure": True}
    assert check_validator.check_case(case, crjson) == [
        "unexpected failure code(s) assertion.metadata.disallowed"]


def test_per_assertion_requires_status_for_each_label():
    base = "self#jumbf=/c2pa/urn:c2pa:x/c2pa.assertions/"
    crjson = {"manifests": [{
        "assertions": {"cawg.identity": {}, "cawg.identity__1": {}},
        "validationResults": {"success": [
            {"code": "cawg.identity.well-formed", "url": base + "cawg.identity"}]}}]}
    case = {"expect_any": ["cawg.identity.well-formed"], "per_assertion": True}
    assert check_validator.check_case(case, crjson) == [
        "no cawg.identity.well-formed status for cawg.identity__1"]
