"""Reusable conformance checks for the core suite and for plugins.

checks(project) yields (name, check) pairs. Each check returns a list of
problems; an empty list means it passed. The pytest plugin
(cawg_rubric.pytest_plugin) turns each pair into a test item, so the core suite
and every plugin are tested the same way:

  - lint                 the plugin's guardrails hold (plugins only)
  - built[<profile>]     the committed built rubric is up to date
  - unit[<id>]-pos/-neg  each statement passes its -pos unit fixture and
                         reports its -neg fixture at its severity
  - snapshot[<file>]     reports on the reference crJSON match the snapshots
  - validator-*          validator cases are well formed, every asset has one,
                         and the reference validator matches its baseline
"""

import glob
import json
import os

from . import build, validator
from .evaluator import evaluate_rubric, outcome_of
from .manifest import check_plugin


def rubrics(project):
    """[(profile, metadata, statements)] for every profile the project tests (cached)."""
    if "rubrics" not in project._cache:
        project._cache["rubrics"] = [(p, *build.assemble(p, project)) for p in project.profiles]
    return project._cache["rubrics"]


def _split(stmt_id):
    return stmt_id.split(":", 1) if ":" in stmt_id else ("general", stmt_id)


def unit_statements(project):
    """[(profile, metadata, statements, stmt)] for statements that need unit fixtures.

    Core: every statement. Plugin: its own statements and the core statements it
    tightens (the -neg fixture shows the tightening takes effect).
    """
    seen, out = set(), []
    for profile, metadata, statements in rubrics(project):
        for stmt in statements:
            sid = stmt["id"]
            if sid in seen:
                continue
            mine = (project.kind == "core"
                    or _split(sid)[0] == project.statement_prefix
                    or sid in profile.overrides)
            if mine:
                seen.add(sid)
                out.append((profile, metadata, statements, stmt))
    return out


def expected_outcome(stmt):
    return "warning" if stmt.get("warnIfMatched") else "false"


def _load_json(path):
    with open(path) as f:
        return json.load(f)


def check_unit_pos(project, metadata, statements, stmt):
    category, rule = _split(stmt["id"])
    path = os.path.join(project.tests["unit_fixtures"], category, f"{rule}-pos.json")
    if not os.path.exists(path):
        return [f"missing unit fixture {os.path.relpath(path, project.root)}"]
    report = evaluate_rubric(metadata, statements, _load_json(path))
    # A -pos fixture passes the whole profile, with no warnings in its own category.
    problems = [f"{c}:{e['trait']} is false: {e['reportText']}"
                for c, entries in report["false"].items() for e in entries]
    problems += [f"{category}:{e['trait']} warns: {e['reportText']}"
                 for e in report["warning"].get(category, [])]
    return problems


def check_unit_neg(project, metadata, statements, stmt):
    category, rule = _split(stmt["id"])
    path = os.path.join(project.tests["unit_fixtures"], category, f"{rule}-neg.json")
    if not os.path.exists(path):
        return [f"missing unit fixture {os.path.relpath(path, project.root)}"]
    report = evaluate_rubric(metadata, statements, _load_json(path))
    expected = expected_outcome(stmt)
    actual = outcome_of(report, rule, category)
    if actual != expected:
        return [f"{stmt['id']} is {actual!r} on its -neg fixture, expected {expected!r}"]
    entry = next(e for e in report[expected][category] if e["trait"] == rule)
    if entry["reportText"].startswith("Error"):
        return [f"{stmt['id']}: {entry['reportText']}"]
    return []


def summarize(report):
    """Outcome per category:trait; report text is left out so wording edits don't churn snapshots."""
    out = {}
    for outcome in ("true", "false", "warning"):
        for category, entries in report[outcome].items():
            for e in entries:
                out[f"{category}:{e['trait']}"] = {"outcome": outcome, "matches": e.get("matches", [])}
    return out


def crjson_files(project):
    root = project.tests.get("crjson_root")
    if not root:
        return []
    return sorted(glob.glob(os.path.join(root, "**", "*.crjson.json"), recursive=True))


def check_snapshot(project, path, update=False):
    data = _load_json(path)
    actual = {}
    for _, metadata, statements in rubrics(project):
        actual.update(summarize(evaluate_rubric(metadata, statements, data)))
    actual = dict(sorted(actual.items()))
    snapshot = path.replace(".crjson.json", ".rubric.json")
    if update or not os.path.exists(snapshot):
        with open(snapshot, "w") as f:
            json.dump(actual, f, indent=2)
            f.write("\n")
    expected = _load_json(snapshot)
    if actual == expected:
        return []
    changed = sorted(k for k in set(actual) | set(expected) if actual.get(k) != expected.get(k))
    return [f"{k}: snapshot {expected.get(k)} != actual {actual.get(k)}" for k in changed]


def check_built(project, profile):
    path = build.target_path(project, profile)
    expected = build.rendered(project, profile)
    command = "cawg-suite build" + (f" --plugin {project.root}" if project.kind == "plugin" else "")
    rel = os.path.relpath(path, project.root)
    if not os.path.exists(path):
        return [f"{rel} is missing; run `{command}`"]
    with open(path, encoding="utf-8") as f:
        if f.read() != expected:
            return [f"{rel} is out of date; run `{command}`"]
    from .validate_rubric import validate_text
    return validate_text(expected, profile.id)


def _cases(project):
    return validator.load_cases(project.case_files())


def check_case_ids_unique(project):
    ids = [c["id"] for c in _cases(project)]
    return [f"duplicate case id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]


def check_case_assets_exist(project):
    root = project.tests["assets_root"]
    return [f"case {c['id']}: no asset {c['asset']}" for c in _cases(project)
            if not os.path.exists(os.path.join(root, c["asset"]))]


def check_case_subjects(project):
    subjects = project.subject_patterns()
    return [f"case {c['id']}: unknown subject {c['subject']!r}" for c in _cases(project)
            if c["subject"] not in subjects]


def check_every_asset_has_case(project):
    root = project.tests["assets_root"]
    on_disk = {os.path.relpath(os.path.join(d, f), root)
               for d, _, files in os.walk(root) for f in files if not f.startswith(".")}
    on_disk -= set(project.tests.get("rubric_only_assets") or [])
    with_case = {c["asset"] for c in _cases(project)}
    return [f"asset without a validator case: {a}" for a in sorted(on_disk - with_case)]


def check_baseline(project):
    results = validator.run(project.tests["crjson_root"], project.case_files(),
                            project.subject_patterns())
    failed = {case["id"] for case, problems in results if problems}
    known = validator.load_known_failures(project.tests["baseline"])
    problems = []
    for case, case_problems in results:
        if case["id"] in failed - known:
            problems.append(f"new failure {case['id']}: {'; '.join(case_problems)}")
    problems += [f"baseline failure now passes (update the baseline): {i}" for i in sorted(known - failed)]
    return problems


def checks(project, update_snapshots=False):
    """Yield (name, check) for every conformance check of a project."""
    if project.kind == "plugin":
        yield "lint", lambda: check_plugin(project)

    for profile in project.profiles:
        if build.target_path(project, profile):
            yield f"built[{profile.id}]", lambda p=profile: check_built(project, p)

    if project.tests.get("unit_fixtures"):
        for _, metadata, statements, stmt in unit_statements(project):
            args = (project, metadata, statements, stmt)
            yield f"unit[{stmt['id']}]-pos", lambda a=args: check_unit_pos(*a)
            yield f"unit[{stmt['id']}]-neg", lambda a=args: check_unit_neg(*a)

    for path in crjson_files(project):
        name = os.path.relpath(path, project.tests["crjson_root"])
        yield f"snapshot[{name}]", lambda p=path: check_snapshot(project, p, update_snapshots)

    if project.case_files():
        yield "validator-case-ids-unique", lambda: check_case_ids_unique(project)
        yield "validator-case-subjects", lambda: check_case_subjects(project)
        if project.tests.get("assets_root"):
            yield "validator-case-assets-exist", lambda: check_case_assets_exist(project)
            yield "validator-every-asset-has-a-case", lambda: check_every_asset_has_case(project)
        if project.tests.get("baseline") and project.tests.get("crjson_root"):
            yield "validator-baseline", lambda: check_baseline(project)
