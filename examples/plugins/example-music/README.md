# Example music profile (a cawg-test-suite plugin)

A **fictional** conformance profile for recorded music, built on top of the
CAWG profiles in [cawg-test-suite](https://github.com/Cognitive-Proof/cawg-test-suite).
It shows what an industry body could do with a plugin. It does not represent
any real organisation's requirements.

Copy this directory into a new repository to start your own plugin. The full
guide is [docs/plugins.md](../../../docs/plugins.md).

## What the profile requires

`music-1.0` extends `cawg:identity-1.3` and `cawg:metadata-1.1`. On top of every
CAWG statement, it adds:

| Statement | Severity | Requirement |
| --- | --- | --- |
| `music:isrc_present` | true/false | A `cawg.metadata` assertion has an ISRC (`urn:isrc:…`) in `dc:identifier` |
| `music:isrc_wellformed` | failure | Every ISRC has the ISO 3901 shape `CC-XXX-YY-NNNNN` |
| `music:title_present` | warning | Metadata with an ISRC also has `dc:title` |
| `music:publisher_attests_metadata` | failure | An identity assertion with the `cawg.publisher` role references every metadata assertion |

It also tightens two CAWG recommendations into requirements:
`metadata:gathered_referenced_by_identity` and `metadata:urn_values_wellformed`
are failures in this profile instead of warnings.

## Layout

```
cawg-plugin.yml               the manifest: profiles, overrides, test configuration
rubrics/globals.yml           helper expressions (_music…)
rubrics/music-1.0.yml         the profile's statements
build/music-1.0.rubric.yml    built rubric (generated; CAWG statements included)
fixtures/unit/                -pos / -neg crJSON for each statement (make_unit_fixtures.py)
fixtures/assets/              signed test assets
fixtures/crjson/              c2pa-rs crJSON for the assets, with rubric snapshots
validator_tests/              validator cases and the c2pa-rs baseline
```

## Running it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest                                              # every check
.venv/bin/cawg-suite evaluate music-1.0 my.crjson.json --plugin .
.venv/bin/cawg-suite build --plugin .                         # after editing rubrics/
```

The assets were made with cawg-test-suite's `make-assets` tool
(`make-assets fixtures/assets example-music`) and its crJSON with `crjson-gen`.

## Licence

Like cawg-test-suite, this example is licensed under MIT OR Apache-2.0. The
test assets are signed with the c2pa-rs test certificates (MIT); see the
cawg-test-suite NOTICE.
