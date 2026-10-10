# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this repo is

Conformance test code and examples for CAWG specifications. Right now that is only the
Identity Assertion 1.3. There are no program or policy documents here.

- Rubrics (`rubrics/`) check generator output (crJSON) with YAML + json-formula, in the same
  format as the C2PA Asset Rubrics (c2pa-org/conformance `asset-rubrics/`).
- Validator cases (`validator_tests/`) check that a validator's crJSON carries the expected
  `cawg.*` status codes for each asset in `fixtures/assets/`.

## Commands

```bash
./build_rubrics.sh        # composables -> rubrics/*.rubric.yml, then schema validation
./run_tests.sh            # pytest (args pass through)
.venv/bin/python -m cawg_rubric.evaluator rubrics/cawg-identity-1.3.rubric.yml <file.crjson.json>
.venv/bin/python validator_tests/check_validator.py <crjson-dir> [--baseline ...]
.venv/bin/python fixtures/unit/make_unit_fixtures.py
cargo run --release --manifest-path tools/crjson-gen/Cargo.toml -- fixtures/assets fixtures/crjson
UPDATE_SNAPSHOTS=1 ./run_tests.sh tests/test_rubric_fixtures.py
```

## Conventions

- Never hand-edit `rubrics/*.rubric.yml`, `fixtures/unit/*.json` or `fixtures/crjson/`. They are
  generated, and CI checks the first two are up to date.
- Statement IDs are `identity:<snake_case>`. Every statement has `specSection` and
  `reportText` (`true` and `false` keys only; the schema allows nothing else). Statements return the
  offending `ref` values (`<manifest label>/<assertion label>`) with `failIfMatched` or `warnIfMatched`.
- Every statement needs a `<rule>-pos.json` / `<rule>-neg.json` pair. `tests/test_rubric_units.py`
  enforces this.
- json-formula gotchas:
  - `"text"` is a string literal, and `'claim.v2'` quotes an identifier.
  - Named expressions get their arguments only through the global `$args` array.
  - Inside `[? ]`, `@` is the element and you cannot reach the crJSON root. Pass data through
    `$args`, or attach it to the entry first (see `_withStoreRefKeys` in `globals.yml`).
  - There is no `flatten()`. Use `[]`.
  - `[a, b][][?x]` filters each element rather than the flattened list. Default nulls with
    `|| \`[]\`` instead.
- crJSON writers are inconsistent. c2pa-rs 0.91.2 writes `pad1` as a byte array, and the hashes in
  `referenced_assertions` keep a closing `'` that claim hashes don't. Compare through `_hashKey` and
  `_padNonZero`.
- `cawg_rubric/` is adapted from the C2PA evaluator (commit b6d5a1b). Keep the engine section
  (`create_json_formula_engine`, `_infer_arities`) in sync with upstream rather than diverging.
