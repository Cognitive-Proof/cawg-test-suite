"""Each rubric statement passes on its -pos fixture and is caught by its -neg fixture."""
import json
import os

import pytest

from cawg_rubric.evaluator import evaluate, load_rubric, outcome_of
from conftest import FIXTURES, RUBRICS

UNIT_DIR = os.path.join(FIXTURES, "unit")


def _rules():
    for category, rubric in RUBRICS.items():
        _, statements = load_rubric(rubric)
        for s in statements:
            stmt_category, rule = s["id"].split(":", 1)
            assert stmt_category == category, f"{s['id']} is in the {category} rubric"
            yield category, rule, s


RULES = list(_rules())
IDS = [f"{c}:{r}" for c, r, _ in RULES]


def _load(category, name):
    with open(os.path.join(UNIT_DIR, category, name)) as f:
        return json.load(f)


def test_every_rule_has_fixtures():
    missing = [f"{c}:{r}" for c, r, _ in RULES
               if not os.path.exists(os.path.join(UNIT_DIR, c, f"{r}-pos.json"))
               or not os.path.exists(os.path.join(UNIT_DIR, c, f"{r}-neg.json"))]
    assert not missing, f"rules without unit fixtures: {missing}"


@pytest.mark.parametrize("category,rule,stmt", RULES, ids=IDS)
def test_positive_fixture_is_clean(category, rule, stmt):
    report = evaluate(RUBRICS[category], _load(category, f"{rule}-pos.json"))
    problems = [(o, e["trait"], e["reportText"]) for o in ("false", "warning")
                for e in report[o].get(category, [])]
    assert not problems


@pytest.mark.parametrize("category,rule,stmt", RULES, ids=IDS)
def test_negative_fixture_is_caught(category, rule, stmt):
    report = evaluate(RUBRICS[category], _load(category, f"{rule}-neg.json"))
    expected = "warning" if stmt.get("warnIfMatched") else "false"
    assert outcome_of(report, rule, category) == expected
    entry = next(e for e in report[expected][category] if e["trait"] == rule)
    assert not entry["reportText"].startswith("Error"), entry["reportText"]
