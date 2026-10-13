# Contributing

Issues and pull requests are welcome. These are especially useful:
- a missing requirement
- a case where the suite disagrees with the spec
- results from a validator other than c2pa-rs

## Development setup

You need Python 3.10 or later. Rust 1.96 is needed only to regenerate fixtures.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./build_rubrics.sh   # composables -> rubrics/*.rubric.yml, then schema validation
./run_tests.sh       # pytest; extra arguments are passed through
```

CI runs on every push. It checks that the built rubrics and unit fixtures are
up to date, then runs the tests.

## Adding or changing a rubric statement

1. Edit or add a statement in `rubrics/composables/<spec>-*.yml`. Shared helpers go in `globals.yml`.
   A new spec also needs a recipe in `cawg_rubric/build.py` and an entry in `tests/conftest.py`.
2. Run `./build_rubrics.sh`. This rebuilds and schema-validates the rubric.
3. Add a `-pos` / `-neg` pair to `fixtures/unit/make_unit_fixtures.py`, then run
   `.venv/bin/python fixtures/unit/make_unit_fixtures.py`.
4. Run `./run_tests.sh`. If outcomes changed on purpose, refresh snapshots with
   `UPDATE_SNAPSHOTS=1 ./run_tests.sh tests/test_rubric_fixtures.py`.

Statement conventions:
- IDs are `<spec>:<snake_case>`.
- Each statement has a `specSection` and a `reportText` with only `true` and `false` keys.
- Offending assertions are returned as `<manifest label>/<assertion label>`, using `failIfMatched` or `warnIfMatched`.

[CLAUDE.md](CLAUDE.md) lists the json-formula quirks the rubrics work around.

## Adding a validator case

Add the case to the relevant `validator_tests/<spec>-cases.yml`. The keys are
described at the top of `identity-1.3-cases.yml`. Each case should name the spec
section it comes from.

If c2pa-rs fails the new case, add it to `validator_tests/baselines/c2pa-rs-0.91.2.yml`
with a reason. CI requires the baseline to match exactly.

## Regenerating fixtures

Rebuild crJSON from the assets (needs Rust 1.96; `tools/crjson-gen/rust-toolchain.toml` pins it):

```bash
cargo run --release --manifest-path tools/crjson-gen/Cargo.toml -- fixtures/assets fixtures/crjson
UPDATE_SNAPSHOTS=1 ./run_tests.sh tests/test_rubric_fixtures.py
```

Then update `validator_tests/baselines/` if the reference validator's results changed.

The metadata and training-mining assets are signed offline by `make-assets` with
the c2pa-rs test certificates. Signatures and IDs change on every run, so only
rebuild a group when one of its recipes changes:

```bash
cargo run --release --manifest-path tools/crjson-gen/Cargo.toml --bin make-assets -- fixtures/assets training-mining
```

c2pa-rs refuses to sign a metadata assertion without `@context`, so that case
only has a hand-built unit fixture.

### Generated identity fixtures

`fixtures/assets/{identity,x509,ica}/` come from an ignored test on the c2pa-rs branch
[`cawg/conformance-fixtures`](https://github.com/mrappard/c2pa-rs-text-support/tree/cawg/conformance-fixtures)
(commit `e52bd0a`, in `sdk/src/identity/tests/conformance_fixtures/`). It uses
test-only hooks in the identity assertion builder to produce invalid assertions,
and mints certificates for the trust-model cases. To regenerate:

```bash
CAWG_FIXTURES_OUT=/tmp/cawg-fixtures cargo +1.96.0 test -p c2pa --lib \
  generate_cawg_conformance_fixtures -- --ignored --nocapture
```

Then:
1. Copy `{identity,x509,ica}/*.jpg` into `fixtures/assets/`.
2. Copy `index.json` to `validator_tests/c2pa-rs-generated-index.json`.
3. Replace `tools/crjson-gen/generated_trust_anchor.pem` with the new `x509/trust_anchor.pem`.
   Also replace the matching certificate at the end of the CAWG `trust_anchors` in
   `cawg_test_settings.toml`. The generator makes a new root on every run.
4. Rebuild crjson-gen and regenerate the crJSON.

## Licensing of contributions

This project is licensed under MIT OR Apache-2.0. Unless you explicitly state
otherwise, any contribution you submit for inclusion is licensed the same way,
without any additional terms or conditions.

Only add third-party material whose licence allows it, and list it in
[NOTICE](NOTICE) with its source and licence. Don't copy material from private
repositories or unpublished drafts.
