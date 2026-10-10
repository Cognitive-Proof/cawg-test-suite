"""Every rubric's report on each generated crJSON fixture matches the committed snapshot.

Regenerate snapshots after an intended rubric or fixture change with:
    UPDATE_SNAPSHOTS=1 ./run_tests.sh tests/test_rubric_fixtures.py
"""
import glob
import json
import os

import pytest

from cawg_rubric.evaluator import evaluate
from conftest import FIXTURES, RUBRICS

CRJSON_DIR = os.path.join(FIXTURES, "crjson")
CRJSON_FILES = sorted(glob.glob(os.path.join(CRJSON_DIR, "**", "*.crjson.json"), recursive=True))


def summarize(report):
    """Outcome per category:trait; report text is left out so wording edits don't churn snapshots."""
    out = {}
    for outcome in ("true", "false", "warning"):
        for category, entries in report[outcome].items():
            for e in entries:
                out[f"{category}:{e['trait']}"] = {"outcome": outcome, "matches": e.get("matches", [])}
    return out


@pytest.mark.parametrize("path", CRJSON_FILES, ids=lambda p: os.path.relpath(p, CRJSON_DIR))
def test_rubric_snapshot(path):
    with open(path) as f:
        data = json.load(f)
    actual = {}
    for rubric in RUBRICS.values():
        actual.update(summarize(evaluate(rubric, data)))
    actual = dict(sorted(actual.items()))
    snapshot = path.replace(".crjson.json", ".rubric.json")
    if os.environ.get("UPDATE_SNAPSHOTS") or not os.path.exists(snapshot):
        with open(snapshot, "w") as f:
            json.dump(actual, f, indent=2)
            f.write("\n")
    with open(snapshot) as f:
        assert actual == json.load(f)
