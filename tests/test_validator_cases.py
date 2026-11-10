"""Unit tests of the validator case checker.

The case files themselves (unique IDs, assets, every asset has a case, the
c2pa-rs baseline) are checked by the items collected from cawg-tests.yml.
"""
import os

from conftest import REPO_ROOT
from validator_tests import check_validator


def test_consistency_rule_flags_success_with_failure():
    url = "self#jumbf=/c2pa/urn:c2pa:x/c2pa.assertions/cawg.identity"
    crjson = {"manifests": [{"validationResults": {
        "success": [{"code": "cawg.identity.well-formed", "url": url}],
        "failure": [{"code": "cawg.identity.pad.invalid", "url": url}]}}]}
    problems = check_validator.check_case({"expect_failure": ["cawg.identity.pad.invalid"]}, crjson)
    assert problems == ["cawg.identity.well-formed reported alongside a cawg.* failure"]


def test_case_files_found():
    names = {os.path.basename(p) for p in check_validator.DEFAULT_CASES}
    assert check_validator.DEFAULT_CASES[0].startswith(os.path.join(REPO_ROOT, "validator_tests"))
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


def test_unknown_subject_is_a_problem():
    assert check_validator.check_case({"subject": "nope"}, {"manifests": []}) == [
        "unknown subject 'nope' (known: identity, manifest, metadata)"]


def test_wrapper_cli_uses_core_cases(capsys):
    crjson_dir = os.path.join(REPO_ROOT, "fixtures", "crjson")
    baseline = os.path.join(REPO_ROOT, "validator_tests", "baselines", "c2pa-rs-0.91.2.yml")
    assert check_validator.main([crjson_dir, "--baseline", baseline]) == 0
    assert "49/78 cases passed" in capsys.readouterr().out
