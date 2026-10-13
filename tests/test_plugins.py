"""Plugin manifests: loading, guardrails, assembly and the CLI.

The example plugin's own conformance checks (units, snapshots, validator cases)
run from its directory: `cd examples/plugins/example-music && pytest`.
"""
import os

import pytest
import yaml

from cawg_rubric import __version__, build, cli
from cawg_rubric.manifest import ManifestError, check_plugin, check_requires, load_project
from cawg_rubric.validator import check_case
from conftest import REPO_ROOT

EXAMPLE = os.path.join(REPO_ROOT, "examples", "plugins", "example-music")

STATEMENT = {
    "id": "acme:has_metadata",
    "expression": "length(_metadata()) > `0`",
    "reportText": {"true": {"en": "ok"}, "false": {"en": "missing"}},
}


def write_plugin(tmp_path, statements=(STATEMENT,), globals_doc=None, **overrides):
    """Write a minimal plugin to tmp_path and return its manifest path."""
    manifest = {
        "name": "org.example.acme",
        "version": "1.0.0",
        "requires": f"cawg-test-suite=={__version__}",
        "statement_prefix": "acme",
        "profiles": [{
            "id": "acme-1.0",
            "name": "Acme 1.0",
            "extends": ["cawg:metadata-1.1"],
            "composables": ["acme.yml"],
        }],
    }
    profile_keys = {"extends", "overrides", "composables"}
    for key, value in overrides.items():
        if key in profile_keys:
            manifest["profiles"][0][key] = value
        else:
            manifest[key] = value
    if globals_doc is not None:
        manifest["globals"] = "globals.yml"
        (tmp_path / "globals.yml").write_text(yaml.safe_dump(globals_doc))
    (tmp_path / "acme.yml").write_text(yaml.safe_dump(list(statements)))
    path = tmp_path / "cawg-plugin.yml"
    path.write_text(yaml.safe_dump(manifest))
    return str(path)


def problems_of(path):
    return check_plugin(load_project(path))


def test_example_plugin_passes_guardrails():
    assert problems_of(EXAMPLE) == []


def test_minimal_plugin_passes_guardrails(tmp_path):
    assert problems_of(write_plugin(tmp_path)) == []


def test_reserved_statement_prefix(tmp_path):
    path = write_plugin(tmp_path, statement_prefix="metadata",
                        statements=[{**STATEMENT, "id": "metadata:has_metadata"}])
    assert "statement_prefix: 'metadata' is reserved for the core suite" in problems_of(path)


def test_statement_must_use_plugin_prefix(tmp_path):
    # Reusing a core ID would replace the core statement, so it must be rejected.
    path = write_plugin(tmp_path, statements=[{**STATEMENT, "id": "metadata:validation_no_failures"}])
    assert problems_of(path) == [
        "profile acme-1.0: statement 'metadata:validation_no_failures' must be named acme:<name>"]


def test_override_tightens_warning(tmp_path):
    path = write_plugin(tmp_path, overrides={"metadata:terms_defined_in_context": "fail"})
    project = load_project(path)
    assert check_plugin(project) == []
    _, statements = build.assemble(project.profiles[0], project)
    stmt = next(s for s in statements if s["id"] == "metadata:terms_defined_in_context")
    assert stmt["failIfMatched"] is True and "warnIfMatched" not in stmt
    assert "Tightened from a warning to a failure by org.example.acme" in stmt["description"]


@pytest.mark.parametrize("value", ["warn", "off", "pass"])
def test_override_cannot_weaken(tmp_path, value):
    path = write_plugin(tmp_path, overrides={"metadata:validation_no_failures": value})
    assert problems_of(path) == [
        f"profile acme-1.0: override 'metadata:validation_no_failures': {value!r} is not allowed; "
        "plugins can only tighten a warning to 'fail', never weaken or disable a statement"]


def test_override_of_failure_is_rejected(tmp_path):
    path = write_plugin(tmp_path, overrides={"metadata:validation_no_failures": "fail"})
    assert problems_of(path) == [
        "profile acme-1.0: override 'metadata:validation_no_failures' is already a failure"]


def test_override_of_boolean_is_rejected(tmp_path):
    path = write_plugin(tmp_path, overrides={"metadata:metadata_assertion_present": "fail"})
    assert problems_of(path) == ["profile acme-1.0: override 'metadata:metadata_assertion_present' "
                                 "is a true/false statement with no warning to tighten"]


def test_override_unknown_id(tmp_path):
    # identity-1.3 is not extended, so its statements can't be overridden.
    path = write_plugin(tmp_path, overrides={"identity:role_cawg_namespace": "fail"})
    assert problems_of(path) == ["profile acme-1.0: override 'identity:role_cawg_namespace' "
                                 "is not a statement of cawg:metadata-1.1"]


def test_globals_cannot_redefine_core(tmp_path):
    path = write_plugin(tmp_path, globals_doc={
        "variables": {"$tdm_use_values": ["allowed"]},
        "expressions": {"_metadata": "`[]`", "_acmeOk": "true()"}})
    assert problems_of(path) == [
        "globals: '$tdm_use_values' redefines a core variable; use a plugin-specific name",
        "globals: '_metadata' redefines a core expression; use a plugin-specific name"]


def test_globals_include_is_rejected(tmp_path):
    path = write_plugin(tmp_path, globals_doc={"include": ["../globals.yml"]})
    assert "globals: include is not supported; the core globals are always available" in problems_of(path)


def test_subject_cannot_redefine_core(tmp_path):
    path = write_plugin(tmp_path, subjects={"identity": "x", "acme_label": r"(^|/)org\.example\.acme$"})
    assert problems_of(path) == ["subjects: 'identity' redefines a core subject"]


def test_requires_must_accept_installed_version(tmp_path):
    path = write_plugin(tmp_path, requires="cawg-test-suite>=99")
    assert problems_of(path) == [
        f"requires: 'cawg-test-suite>=99' does not accept the installed cawg-test-suite {__version__}"]
    assert check_requires("cawg-test-suite>=0.2,<0.3", "0.2.5") is None
    assert check_requires("cawg-test-suite>=0.2,<0.3", "0.3.0") is not None


def test_unknown_extends_is_a_manifest_error(tmp_path):
    with pytest.raises(ManifestError, match=r"extends unknown profile 'cawg:metadata-9\.9'"):
        load_project(write_plugin(tmp_path, extends=["cawg:metadata-9.9"]))


def test_schema_errors_are_manifest_errors(tmp_path):
    path = write_plugin(tmp_path, colour="blue")
    with pytest.raises(ManifestError, match="Additional properties are not allowed"):
        load_project(path)


def test_plugin_subjects_extend_core_subjects(tmp_path):
    project = load_project(write_plugin(tmp_path, subjects={"acme_label": r"(^|/)org\.example\.acme$"}))
    subjects = project.subject_patterns()
    assert {"identity", "metadata", "manifest", "acme_label"} <= set(subjects)
    url = "self#jumbf=/c2pa/urn:c2pa:x/c2pa.assertions/org.example.acme"
    crjson = {"manifests": [{"validationResults": {"failure": [{"code": "assertion.cbor.invalid", "url": url}]}}]}
    case = {"subject": "acme_label", "expect_failure": ["assertion.cbor.invalid"]}
    assert check_case(case, crjson, subjects) == []


def test_plugin_rubric_has_core_statements_first(tmp_path):
    project = load_project(write_plugin(tmp_path))
    metadata, statements = build.assemble(project.profiles[0], project)
    ids = [s["id"] for s in statements]
    assert ids[-1] == "acme:has_metadata"
    assert ids[:-1] == [s["id"] for s in build.assemble(project.profiles[0].extends[0])[1]]
    assert metadata["rubric_metadata"]["issuer"] == "org.example.acme"
    assert "_metadata" in metadata["expressions"]


def test_cli_lint_and_evaluate(tmp_path, capsys):
    assert cli.main(["lint-plugin", EXAMPLE]) == 0
    bad = write_plugin(tmp_path, overrides={"metadata:validation_no_failures": "warn"})
    assert cli.main(["lint-plugin", bad]) == 1
    capsys.readouterr()

    valid = os.path.join(EXAMPLE, "fixtures", "crjson", "example-music", "valid.crjson.json")
    assert cli.main(["evaluate", "music-1.0", valid, "--plugin", EXAMPLE]) == 0
    missing = valid.replace("valid", "isrc_missing")
    assert cli.main(["evaluate", "org.example.music:music-1.0", missing, "--plugin", EXAMPLE]) == 1
    # The core profile alone doesn't know about ISRCs.
    assert cli.main(["evaluate", "cawg:metadata-1.1", missing]) == 0


def test_cli_build_plugin(tmp_path, capsys):
    assert cli.main(["build", "--plugin", EXAMPLE, "--out", str(tmp_path)]) == 0
    with open(os.path.join(EXAMPLE, "build", "music-1.0.rubric.yml")) as f:
        assert (tmp_path / "music-1.0.rubric.yml").read_text() == f.read()
