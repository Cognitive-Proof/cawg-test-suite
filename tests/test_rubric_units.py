"""Each rubric statement passes on its -pos fixture and is caught by its -neg fixture."""
import json
import os

import pytest

from cawg_rubric.evaluator import evaluate, load_rubric, outcome_of
from conftest import FIXTURES, RUBRIC

UNIT_DIR = os.path.join(FIXTURES, "unit")
_, STATEMENTS = load_rubric(RUBRIC)
RULES = {s["id"].split(":", 1)[1]: s for s in STATEMENTS}


def _load(name):
    with open(os.path.join(UNIT_DIR, name)) as f:
        return json.load(f)


def test_every_rule_has_fixtures():
    missing = [r for r in RULES
               if not os.path.exists(os.path.join(UNIT_DIR, f"{r}-pos.json"))
               or not os.path.exists(os.path.join(UNIT_DIR, f"{r}-neg.json"))]
    assert not missing, f"rules without unit fixtures: {missing}"


@pytest.mark.parametrize("rule", sorted(RULES))
def test_positive_fixture_is_clean(rule):
    report = evaluate(RUBRIC, _load(f"{rule}-pos.json"))
    problems = [(o, e["trait"], e["reportText"]) for o in ("false", "warning")
                for e in report[o].get("identity", [])]
    assert not problems


@pytest.mark.parametrize("rule", sorted(RULES))
def test_negative_fixture_is_caught(rule):
    report = evaluate(RUBRIC, _load(f"{rule}-neg.json"))
    expected = "warning" if RULES[rule].get("warnIfMatched") else "false"
    assert outcome_of(report, rule) == expected
    entry = next(e for e in report[expected]["identity"] if e["trait"] == rule)
    assert not entry["reportText"].startswith("Error"), entry["reportText"]
