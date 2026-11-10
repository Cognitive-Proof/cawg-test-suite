# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this repo is

Conformance test code and examples for CAWG specifications: Identity Assertion 1.3, Metadata
Assertion 1.1 (with 1.2-draft recommendations as warnings), and Training and Data Mining 1.1. There are no program
or policy documents here.

- Rubrics (`cawg_rubric/rubrics/`) check generator output (crJSON) with YAML + json-formula, in the same
  format as the C2PA Asset Rubrics (c2pa-org/conformance-public `asset-rubrics/`).
- Validator cases (`validator_tests/<spec>-cases.yml`) check that a validator's crJSON carries the
  expected status codes for each asset in `fixtures/assets/`. A file-level `subject` (identity,
  metadata, manifest) picks which status entries are checked.
- Profiles, subjects and their composables are declared in `cawg_rubric/suite.yml`; the core test
  configuration (cases, assets, fixtures, baseline) is `cawg-tests.yml`.
- Plugins (`docs/plugins.md`) are separate repos with a `cawg-plugin.yml` that extend core profiles:
  they may add statements under their own prefix and tighten warnings to failures, never weaken.
  `cawg_rubric/manifest.py` loads manifests and enforces the guardrails; `cawg_rubric/testing.py`
  holds the checks that `cawg_rubric/pytest_plugin.py` collects for both the core and plugins.
  `examples/plugins/example-music/` is a fictional example; don't name real organisations there.

## Commands

```bash
./build_rubrics.sh        # composables -> cawg_rubric/rubrics/*.rubric.yml, then schema validation
./run_tests.sh            # pytest tests/ + cawg-tests.yml checks (args pass through)
(cd examples/plugins/example-music && ../../../.venv/bin/python -m pytest)   # example plugin
.venv/bin/cawg-suite evaluate <profile-id> <file.crjson.json> [--plugin DIR]
.venv/bin/cawg-suite check-validator <crjson-dir> [--project DIR] [--baseline ...]
.venv/bin/cawg-suite build --plugin examples/plugins/example-music
.venv/bin/python fixtures/unit/make_unit_fixtures.py
cargo run --release --manifest-path tools/crjson-gen/Cargo.toml --bin crjson-gen -- fixtures/assets fixtures/crjson
cargo run --release --manifest-path tools/crjson-gen/Cargo.toml --bin make-assets -- fixtures/assets [group]
UPDATE_SNAPSHOTS=1 ./run_tests.sh cawg-tests.yml
```

## Generated identity fixtures

`fixtures/assets/{identity,x509,ica}/` come from the c2pa-rs branch `cawg/conformance-fixtures`
(https://github.com/mrappard/c2pa-rs-text-support/tree/cawg/conformance-fixtures).
The X.509 trust-model cases depend on `tools/crjson-gen/generated_trust_anchor.pem` also being in
the CAWG `trust_anchors` of `tools/crjson-gen/cawg_test_settings.toml`; the generator mints a new root
on every run, so replace both together. See CONTRIBUTING.md "Generated identity fixtures".

## CAWG-Testfiles assets

`fixtures/assets/testfiles/` comes from the CAWG-Testfiles generator (same layout and file names).
It needs `tools/crjson-gen/testfiles_trust_anchor.pem` in the CAWG `trust_anchors` and its did:jwk
issuer in `trusted_ica_issuers` of `cawg_test_settings.toml`. Cases for these assets are `tf_*`.

## Conventions

- `TODO.md` is the running list of open items (upstream PRs/issues, c2pa-rs deviations, coverage
  gaps). Update it whenever you find, file or resolve something.

- Never hand-edit `cawg_rubric/rubrics/*.rubric.yml`, `fixtures/unit/*.json`, `fixtures/crjson/` or a
  plugin's `build/`. They are generated, and the tests/CI check they are up to date.
- Statement IDs are `<spec>:<snake_case>` (`identity:`, `metadata:`, `training-mining:`).
  Statement IDs, subjects and the public helpers listed in docs/plugins.md are the plugin API:
  breaking one needs a minor version bump (`cawg_rubric/__init__.py`). Every statement has `specSection` and
  `reportText` (`true` and `false` keys only; the schema allows nothing else). Statements return the
  offending `ref` values (`<manifest label>/<assertion label>`) with `failIfMatched` or `warnIfMatched`.
- Every statement needs a `fixtures/unit/<spec>/<rule>-pos.json` / `-neg.json` pair. The
  `unit[...]` checks collected from `cawg-tests.yml` enforce this.
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
