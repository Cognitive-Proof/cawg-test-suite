# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this repo is

Conformance test code and examples for CAWG specifications: Identity Assertion 1.3, Metadata
Assertion 1.1 (with 1.2-draft recommendations as warnings), and Training and Data Mining 1.1. There are no program
or policy documents here.

- Rubrics (`rubrics/`) check generator output (crJSON) with YAML + json-formula, in the same
  format as the C2PA Asset Rubrics (c2pa-org/conformance-public `asset-rubrics/`).
- Validator cases (`validator_tests/<spec>-cases.yml`) check that a validator's crJSON carries the
  expected status codes for each asset in `fixtures/assets/`. A file-level `subject` (identity,
  metadata, manifest) picks which status entries are checked.

## Commands

```bash
./build_rubrics.sh        # composables -> rubrics/*.rubric.yml, then schema validation
./run_tests.sh            # pytest (args pass through)
.venv/bin/python -m cawg_rubric.evaluator rubrics/cawg-<spec>.rubric.yml <file.crjson.json>
.venv/bin/python validator_tests/check_validator.py <crjson-dir> [--baseline ...]
.venv/bin/python fixtures/unit/make_unit_fixtures.py
cargo run --release --manifest-path tools/crjson-gen/Cargo.toml -- fixtures/assets fixtures/crjson
cargo run --release --manifest-path tools/crjson-gen/Cargo.toml --bin make-assets -- fixtures/assets [group]
UPDATE_SNAPSHOTS=1 ./run_tests.sh tests/test_rubric_fixtures.py
```

## Generated identity fixtures

`fixtures/assets/{identity,x509,ica}/` come from the c2pa-rs branch `cawg/conformance-fixtures`
(https://github.com/mrappard/c2pa-rs-text-support/tree/cawg/conformance-fixtures).
The X.509 trust-model cases depend on `tools/crjson-gen/generated_trust_anchor.pem` also being in
the CAWG `trust_anchors` of `tools/crjson-gen/cawg_test_settings.toml`; the generator mints a new root
on every run, so replace both together. See CONTRIBUTING.md "Generated identity fixtures".

## Conventions

- `TODO.md` is the running list of open items (upstream PRs/issues, c2pa-rs deviations, coverage
  gaps). Update it whenever you find, file or resolve something.

- Never hand-edit `rubrics/*.rubric.yml`, `fixtures/unit/*.json` or `fixtures/crjson/`. They are
  generated, and CI checks the first two are up to date.
- Statement IDs are `<spec>:<snake_case>` (`identity:`, `metadata:`, `training-mining:`), and the prefix must match the
  rubric's category in `tests/conftest.py`. Every statement has `specSection` and
  `reportText` (`true` and `false` keys only; the schema allows nothing else). Statements return the
  offending `ref` values (`<manifest label>/<assertion label>`) with `failIfMatched` or `warnIfMatched`.
- Every statement needs a `fixtures/unit/<spec>/<rule>-pos.json` / `-neg.json` pair. `tests/test_rubric_units.py`
  enforces this.
- json-formula gotchas:
  - `"text"` is a string literal, and `'claim.v2'` quotes an identifier.
  - Named expressions get their arguments only through the global `$args` array.
  - Inside `[? ]`, `@` is the element and you cannot reach the crJSON root. Pass data through
    `$args`, or attach it to the entry first (see `_withStoreRefKeys` in `globals.yml`).
  - There is no `flatten()`. Use `[]`.
  - `x[*][1]` and `x[*].keys(@)` do not apply per element. Use `map(x, &@[1])` / `map(x, &keys(@))`.
  - `[a, b][][?x]` filters each element rather than the flattened list. Default nulls with
    `|| \`[]\`` instead.
- crJSON writers are inconsistent. c2pa-rs 0.91.2 writes `pad1` as a byte array, and the hashes in
  `referenced_assertions` keep a closing `'` that claim hashes don't. Compare through `_hashKey` and
  `_padNonZero`.
- `cawg_rubric/` is adapted from the C2PA evaluator in c2pa-org/conformance-public (commit f22ce0a,
  CC BY 4.0). Keep the engine section (`create_json_formula_engine`, `_infer_arities`) in sync with
  upstream rather than diverging, and keep the attribution in NOTICE and the file headers.
- Licensing: original work is MIT OR Apache-2.0 (LICENSE-MIT, LICENSE-APACHE). Anything copied in
  from elsewhere must have a compatible licence and be listed in NOTICE. Never copy from private
  repositories.
