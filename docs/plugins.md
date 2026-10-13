# Plugins: building your own conformance profile

CAWG sets the baseline that everyone shares. An industry body, a platform or a
consortium will often need more than that. For example, a music body might want:
- every recording to carry an ISRC in its `cawg.metadata` assertion
- the publisher's identity assertion to vouch for that metadata
- some CAWG recommendations treated as hard requirements

A **plugin** is a conformance profile that does this on top of the CAWG
profiles in this suite. It lives in its own repository and depends on a pinned
version of cawg-test-suite. It reuses the suite's rubric format, helpers, test
harness and validator checker.

The fastest way to start is to copy
[`examples/plugins/example-music/`](../examples/plugins/example-music/). It is
a complete plugin for a fictional music profile, and CI tests it on every
change to the suite.

## What a plugin can and can't do

A plugin **can**:
- **add statements** (checks) under its own prefix, e.g. `music:isrc_present`
- **tighten** a CAWG warning into a failure, e.g. make
  `metadata:urn_values_wellformed` fail instead of warn
- **add validator cases**, with its own signed assets, reference crJSON and
  validator baselines
- **add subjects**, so validator cases can look at the statuses of its own
  assertion types (e.g. `com.example.label`)

A plugin **can't** weaken, disable or replace a CAWG statement. This is
enforced, so "passes the plugin profile" always implies "passes the CAWG
profiles it extends". Specifically:
- Every plugin statement must use the plugin's `statement_prefix`. The core
  prefixes (`identity`, `metadata`, `training-mining`) and the `cawg` and
  `c2pa` namespaces are reserved. A plugin therefore can't redefine a core
  statement by reusing its ID.
- Overrides can only target statements of the profiles the plugin extends.
  The only allowed value is `fail`, and only on a `warnIfMatched` statement.
  Overriding a failure, a true/false statement or an unknown ID is an error.
- Plugin helpers and variables can't redefine a core helper or variable.
- Plugin subjects can't redefine a core subject.
- `requires` must accept the installed cawg-test-suite version.

`cawg-suite lint-plugin` checks all of these, and so do `cawg-suite build`
and the plugin's test run.

## Repository layout

```
cawg-plugin.yml          the manifest
requirements.txt         cawg-test-suite, pinned
pytest.ini               addopts = -p cawg_rubric.pytest_plugin
rubrics/globals.yml      optional: extra helpers and variables
rubrics/<profile>.yml    your statements
build/                   optional: built rubrics, committed
fixtures/unit/           <category>/<rule>-pos.json and -neg.json
fixtures/assets/         optional: signed test assets
fixtures/crjson/         optional: reference crJSON for the assets
validator_tests/         optional: *-cases.yml and baselines/
```

## The manifest: `cawg-plugin.yml`

The full schema is
[`cawg_rubric/schema/plugin.schema.json`](../cawg_rubric/schema/plugin.schema.json).

```yaml
name: org.example.music            # reverse-domain identifier
version: 0.1.0                     # your plugin's version
issuer: Example Music Profile      # optional; recorded in built rubrics (default: name)
requires: "cawg-test-suite>=0.2,<0.3"
statement_prefix: music            # every statement you add is music:<name>
globals: rubrics/globals.yml       # optional
build_dir: build                   # optional; see "Built rubrics"

profiles:
  - id: music-1.0
    name: Example Music Profile 1.0
    extends: [cawg:identity-1.3, cawg:metadata-1.1]
    composables: [rubrics/music-1.0.yml]
    overrides:                     # optional; tighten only
      metadata:gathered_referenced_by_identity: fail

subjects:                          # optional; extra validator-case subjects
  music_label: '(^|/)org\.example\.music\.label(__\d+)?$'

# Test configuration. Every key is optional.
validator_cases: [validator_tests/*-cases.yml]
assets_root: fixtures/assets
unit_fixtures: fixtures/unit
crjson_root: fixtures/crjson
baseline: validator_tests/baselines/c2pa-rs-0.91.2.yml
rubric_only_assets: [example-music/isrc_missing.jpg]
```

The core profiles you can extend are `cawg:identity-1.3`, `cawg:metadata-1.1`
and `cawg:training-mining-1.1`. `cawg-suite list` prints every profile and its
statements.

A plugin profile's rubric has three parts, in this order:
1. the statements of every profile it extends, with overrides applied
2. the plugin's own statements
3. the core globals plus the plugin's globals

## Writing statements

Statements use the same YAML and
[json-formula](https://opensource.adobe.com/json-formula/) format as the core
rubrics and the C2PA Asset Rubrics:

```yaml
- id: music:isrc_wellformed
  description: Every ISRC is 12 characters (CC-XXX-YY-NNNNN).
  specSection: "Example Music Profile 1.0 §2.1"
  failIfMatched: true
  expression: |
    _metadata()[?type(value) == "object" && length(_musicBadIsrcs(@)) > `0`].ref
  reportText:
    'true':
      en: "All ISRCs are well formed"
    'false':
      en: "Metadata assertions with malformed ISRCs: {{matches}}"
```

The conventions are the same as in the core suite:
- Return the offending entries' `ref` (`<manifest label>/<assertion label>`)
  with `failIfMatched` or `warnIfMatched`, or write a true/false expression.
- `reportText` has only `true` and `false` keys.
- Give every statement a `specSection` in your own specification.

The json-formula quirks listed in [CLAUDE.md](../CLAUDE.md) apply to plugins
too. The main ones:
- Named expressions get their arguments only through `$args`.
- Inside a filter, the crJSON root isn't reachable.
- A filter after a flatten (`[a][][?x]`) applies to each element; pass the
  flattened list to a helper instead.

### Core helpers you can use

The core globals are always available. These helpers and the entry shapes they
return are part of the public API:

| Helper | Returns |
| --- | --- |
| `_identities()` | every identity assertion in the store: `{ref, label, manifest, value, claimRefKeys, storeRefKeys, results}` |
| `_metadata()` | every metadata assertion: `{ref, label, manifest, value, gatheredLabels, identityRefLabels, results}` |
| `_tdm()` | every training-and-data-mining assertion: `{ref, label, manifest, value, results}` |
| `_refs(identity)` | an identity entry's `referenced_assertions` (`[]` if absent) |
| `_refLabelsOf(signerPayloadHolders)` | labels referenced by a list of identity assertion values |
| `_statusFor(entry, statuses)` | the status entries in `statuses` that point at `entry` |
| `_labelFromUrl(url)`, `_baseLabel(label)` | the assertion label of a JUMBF URI; a label without its `__N` suffix |
| `_refKey(hashedUri)` | a `"<label>\|<hash>"` comparison key |
| `_tdmEntries(entry)`, `_tdmKeys(entry)` | a TDM entry's `entries` as pairs, or its keys |
| `_isEntityLabel(text)` | whether `text` is a valid C2PA entity-specific label |

The public variables are `$known_sig_types`, `$recommended_roles`,
`$hard_binding_labels`, `$tdm_defined_keys` and `$tdm_use_values`. Other
globals are internal and may change in any release.

Start your own helper and variable names with a plugin-specific prefix
(`_music…`, `$music_…`). Otherwise a helper added to the core in a later
release could clash with yours.

## Testing a plugin

With `-p cawg_rubric.pytest_plugin` in `pytest.ini`, plain `pytest` collects
`cawg-plugin.yml` and runs every check:

| Test | What it checks |
| --- | --- |
| `lint` | the guardrails above |
| `built[<profile>]` | the committed built rubric is up to date and schema-valid (only when `build_dir` is set) |
| `unit[<id>]-pos` | the statement's `-pos` fixture passes the **whole profile**: no failure anywhere, and no warning in the statement's category |
| `unit[<id>]-neg` | the statement reports its `-neg` fixture at its severity (failure, or warning) |
| `snapshot[<file>]` | the profile's report on each reference crJSON matches its `.rubric.json` snapshot |
| `validator-*` | case IDs are unique, subjects exist, assets exist, every asset has a case, and the reference validator matches the baseline |

Unit fixtures are needed for every statement you add and for every core
statement you tighten. The `-neg` fixture of a tightened statement must now
fail, which shows the override takes effect.

Run `UPDATE_SNAPSHOTS=1 pytest` to write snapshots after an intended change.

Checks are skipped when their test configuration key is missing. For example,
with no `validator_cases`, no validator checks run.

## Built rubrics

`cawg-suite evaluate` and the tests assemble a plugin's rubrics in memory, so
nothing has to be built. Set `build_dir` and run `cawg-suite build --plugin .`
if you also want standalone rubric files:
- to publish, or to use with other rubric tools
- to review the effect of a cawg-test-suite upgrade as a diff

The tests then require the committed files to be up to date.

## Test assets and validator cases

A plugin can add signed test assets and validator cases. Make the assets with
any C2PA tooling. The example's assets come from this repository's
`make-assets` tool:

```bash
cargo run --release --manifest-path tools/crjson-gen/Cargo.toml --bin make-assets -- \
  examples/plugins/example-music/fixtures/assets example-music
```

Make the reference crJSON with `crjson-gen`, or with any validator that writes
crJSON.

Validator cases use the same keys as the core cases; see the top of
[`validator_tests/identity-1.3-cases.yml`](../validator_tests/identity-1.3-cases.yml).
Plugins can't define new status codes, so cases can only check codes that
validators already report. Usually this means a plugin's validator cases check
that its assets are valid Content Credentials, while its requirements are
checked by its rubric.

## Command line

```bash
cawg-suite list --plugin .                                    # profiles and statements
cawg-suite lint-plugin .                                      # guardrails
cawg-suite build --plugin .                                   # into build_dir
cawg-suite evaluate music-1.0 asset.crjson.json --plugin .    # exit 1 if any statement fails
cawg-suite check-validator out/ --project . --baseline validator_tests/baselines/mine.yml
```

## Versioning and stability

The plugin API is:
- the core profile IDs and statement IDs, and their severities
- the core subjects
- the public helpers and variables listed above, and their entry shapes
- the manifest schema
- the `cawg-suite` command line and the pytest plugin

While cawg-test-suite is 0.x, anything that could break a plugin raises the
minor version (0.2 → 0.3). Examples:
- removing or renaming a statement or public helper
- changing an entry shape
- making a warning a failure

Patch releases (0.2.0 → 0.2.1) only fix bugs and add statements. Pin
`requires` and your dependency to one minor version, as the example does.

Adding a core statement can still change your plugin's results, because
your profile includes every statement of the profiles it extends. The
`built[...]` and `snapshot[...]` tests show the change when you upgrade.
