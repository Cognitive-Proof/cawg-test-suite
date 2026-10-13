"""Checks of the json-formula behaviour that the CAWG rubrics rely on.

These pin down engine features (and quirks) used in rubrics/composables/, so a
change in json-formula-py or in cawg_rubric.evaluator shows up here rather than
as a confusing rubric failure.
"""
import os

import pytest

from cawg_rubric.evaluator import create_json_formula_engine, evaluate

ENGINE_RUBRIC = os.path.join(os.path.dirname(__file__), "data", "engine-features.rubric.yml")

# Variables and named expressions, in the same shape as a built rubric's
# information block.
METADATA = {
    "variables": {
        "$allowed": ["alpha", "beta"],
        "$limit": 3,
    },
    "expressions": {
        # Arguments arrive as the global array $args.
        "_double": "$args[0] * 2",
        "_firstSegment": 'split($args[0], "/")[0]',
        # A named expression calling another one.
        "_doubleFirst": "_double($args[0][0])",
        # $args stays readable inside a filter, where @ is rebound.
        "_largerThan": "$args[0][?@ > $args[1]]",
    },
}

DATA = {
    "items": [{"name": "alpha", "n": 1}, {"name": "gamma", "n": 5}],
    "nested": {"claim.v2": {"label": "c2pa.claim"}},
    "lists": [[1, 2], [3]],
    "word": "a/b/c",
}


@pytest.fixture(scope="module")
def search():
    engine, variables = create_json_formula_engine(METADATA)
    return lambda expr, data=DATA: engine.search(expr, data, globals=variables)


def test_variables(search):
    assert search('contains($allowed, "beta")') is True
    assert search("$limit + 1") == 4


def test_named_expressions_receive_args(search):
    assert search("_double(`21`)") == 42
    assert search("_firstSegment(word)") == "a"
    assert search("_doubleFirst(`[5, 6]`)") == 10


def test_args_inside_filter(search):
    assert search("_largerThan(`[1, 4, 9]`, `3`)") == [4, 9]


def test_string_literals_and_quoted_identifiers(search):
    # "text" is a string literal; 'name' quotes an identifier with dots.
    assert search('"claim.v2"') == "claim.v2"
    assert search("nested.'claim.v2'.label") == "c2pa.claim"


def test_filter_projection_and_flatten(search):
    assert search('items[?name != "alpha"].name') == ["gamma"]
    assert search("lists[]") == [1, 2, 3]
    assert search("items[*].n") == [1, 5]


def test_functions_used_by_rubrics(search):
    assert search('startsWith("cawg.identity__1", "cawg.identity")') is True
    assert search('substitute("b64\'AA==\'", "A", "")') == "b64'=='"
    assert search('split("ab-c", "")') == ["a", "b", "-", "c"]
    assert search('left("abc", 1)') == "a"
    assert search("keys(nested)") == ["claim.v2"]
    assert search("entries(nested)") == [["claim.v2", {"label": "c2pa.claim"}]]
    assert search("map(items, &n)") == [1, 5]
    assert search("unique(`[1, 1, 2]`)") == [1, 2]


def test_known_quirks(search):
    # [*][1] does not index each element; use map(x, &@[1]) instead.
    assert search("map(entries(nested), &@[0])") == ["claim.v2"]
    # A filter after a flatten applies to each element, not the flattened list.
    assert search("[`[1, 2]`, `[3]`][][?@ > `1`]") != [2, 3]


def test_statement_outcomes():
    report = evaluate(ENGINE_RUBRIC, DATA)
    outcome = {e["trait"]: o for o in ("true", "false", "warning")
               for e in report[o]["engine"]}
    assert outcome == {
        "boolean_true": "true",
        "boolean_false": "false",
        "fail_if_matched_clean": "true",
        "fail_if_matched_hit": "false",
        "warn_if_matched_hit": "warning",
    }
    hit = next(e for e in report["false"]["engine"] if e["trait"] == "fail_if_matched_hit")
    assert hit["matches"] == ["gamma"]
    assert hit["reportText"] == "Unexpected names: gamma"
