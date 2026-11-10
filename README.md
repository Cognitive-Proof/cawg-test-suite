# cawg-test-suite

An open conformance test suite for the [Creator Assertions Working Group (CAWG)](https://cawg.io/)
specifications: the identity, metadata and training-and-data-mining assertions that
extend [C2PA](https://c2pa.org/) Content Credentials.

The CAWG specifications don't come with test cases. This suite turns their
requirements into checks you can run against your own implementation. It works
whether your product **writes** CAWG assertions (a generator) or **reads and
validates** them (a validator). Industry groups can build their own conformance
profiles on top of it as [plugins](#extending-the-suite-with-plugins).

> **Status: early (0.2.0).** This is an independent project. It is not an official
> CAWG, DIF or C2PA conformance program. Expect changes as the specifications and
> the suite evolve. Spec questions and disagreements with the suite are welcome as
> [issues](https://github.com/Cognitive-Proof/cawg-test-suite/issues).

## What's covered

| Specification | Generator checks (rubric) | Validator cases |
| --- | --- | --- |
| [Identity Assertion 1.3](https://cawg.io/identity/1.3/): X.509 (`cawg.x509.cose`) and identity claims aggregation (`cawg.identity_claims_aggregation`) | 26 statements: [`cawg-identity-1.3.rubric.yml`](cawg_rubric/rubrics/cawg-identity-1.3.rubric.yml) | 62 cases: [`identity-1.3-cases.yml`](validator_tests/identity-1.3-cases.yml) |
| [Metadata Assertion 1.1](https://cawg.io/metadata/1.1/), with 1.2-draft recommendations as warnings | 9 statements: [`cawg-metadata-1.1.rubric.yml`](cawg_rubric/rubrics/cawg-metadata-1.1.rubric.yml) | 10 cases: [`metadata-1.1-cases.yml`](validator_tests/metadata-1.1-cases.yml) |
| [Training and Data Mining Assertion 1.1](https://cawg.io/training-and-data-mining/1.1/) | 11 statements: [`cawg-training-mining-1.1.rubric.yml`](cawg_rubric/rubrics/cawg-training-mining-1.1.rubric.yml) | 6 cases: [`training-mining-1.1-cases.yml`](validator_tests/training-mining-1.1-cases.yml) |

[docs/coverage.md](docs/coverage.md) lists what every statement and case checks, and
what can't be checked.

## How it works

Everything runs on **crJSON**, the JSON report format of the C2PA conformance
program. Any C2PA validator that can produce crJSON can be tested.

- **Generators:** produce an asset, get its crJSON, and evaluate it against a
  rubric. Rubrics use the same YAML + [json-formula](https://opensource.adobe.com/json-formula/)
  format as the C2PA Asset Rubrics, so the same tooling runs both.
- **Validators:** run your validator over the signed test assets in
  [`fixtures/assets/`](fixtures/assets/). Each case says which `cawg.*` status codes
  must, or must not, appear.

The test assets include valid and deliberately broken examples of each assertion.
They are signed with the c2pa-rs test credentials, and include certificates minted
for the trust-model cases. The assets in `fixtures/assets/testfiles/` come from
[CAWG-Testfiles](docs/coverage.md#cawg-testfiles-assets), which has its own CAWG test root
and identity claims aggregation issuer.

## Quick start

Requires Python 3.10 or later.

```bash
git clone https://github.com/Cognitive-Proof/cawg-test-suite.git
cd cawg-test-suite
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
./run_tests.sh
```

This installs the `cawg-suite` command.

### Test a generator

Produce crJSON for your asset with any C2PA validator, then:

```bash
.venv/bin/cawg-suite evaluate identity-1.3 my-asset.crjson.json
```

Use `metadata-1.1` or `training-mining-1.1` for the other assertions, or pass
the path of a built rubric. `cawg-suite list` shows every profile and its
statements. The report groups every statement under `true`, `false` or
`warning`, and the exit status is 1 if any statement is `false`.

### Test a validator

Run your validator over every asset in [`fixtures/assets/`](fixtures/assets/), and
write its crJSON to a directory with the same layout (`.jpg` becomes `.crjson.json`).
Then:

```bash
.venv/bin/cawg-suite check-validator path/to/your-output
```

Run it from the repository root, where `cawg-tests.yml` lists the cases.

For the X.509 trust-model cases, configure both
[`tools/crjson-gen/generated_trust_anchor.pem`](tools/crjson-gen/generated_trust_anchor.pem)
and [`tools/crjson-gen/testfiles_trust_anchor.pem`](tools/crjson-gen/testfiles_trust_anchor.pem)
as CAWG trust anchors in your validator. Also trust the ICA issuer DID listed under
`trusted_ica_issuers` in [`cawg_test_settings.toml`](tools/crjson-gen/cawg_test_settings.toml).

## Extending the suite with plugins

CAWG sets the baseline everyone shares. A plugin lets an industry body,
platform or consortium publish a stricter profile on top of it, in its own
repository. A plugin can:
- add its own checks, e.g. "every recording has an ISRC"
- turn CAWG warnings into failures
- add its own signed test assets and validator cases

A plugin can't weaken or disable a CAWG check, and this is enforced. So an
asset that passes a plugin profile also passes CAWG.

[`examples/plugins/example-music/`](examples/plugins/example-music/) is a complete
plugin for a fictional music profile. Copy it to start your own. The guide
is [docs/plugins.md](docs/plugins.md).

```bash
cawg-suite lint-plugin examples/plugins/example-music
cawg-suite evaluate music-1.0 my-song.crjson.json --plugin examples/plugins/example-music
```

## Results: c2pa-rs

The reference results in [`fixtures/crjson/`](fixtures/crjson/) come from
[c2pa-rs](https://github.com/contentauth/c2pa-rs) 0.91.2.
- It passes **49 of 78** validator cases. Every original metadata and
  training-mining case passes; it can't read two of the CAWG-Testfiles metadata assets.
- Each failure is listed with its reason in
  [`validator_tests/baselines/c2pa-rs-0.91.2.yml`](validator_tests/baselines/c2pa-rs-0.91.2.yml).
- CI requires that baseline to match exactly.

Fixes for those failures have been proposed upstream:

| PR | Fix |
| --- | --- |
| [contentauth/c2pa-rs#2836](https://github.com/contentauth/c2pa-rs/pull/2836) | Report each identity assertion under its own label |
| [contentauth/c2pa-rs#2837](https://github.com/contentauth/c2pa-rs/pull/2837) | Don't report `well-formed` for an assertion that failed validation |
| [contentauth/c2pa-rs#2838](https://github.com/contentauth/c2pa-rs/pull/2838) | Report `cawg.ica.did_unsupported_method` |
| [contentauth/c2pa-rs#2839](https://github.com/contentauth/c2pa-rs/pull/2839) | Report `cawg.ica.verified_identities.missing` / `.invalid` |
| [contentauth/c2pa-rs#2840](https://github.com/contentauth/c2pa-rs/pull/2840) | Report `cawg.ica.revocation.unsupported` |
| [contentauth/c2pa-rs#2841](https://github.com/contentauth/c2pa-rs/pull/2841) | Report X.509 statuses against the identity assertion |
| [contentauth/c2pa-rs#2842](https://github.com/contentauth/c2pa-rs/pull/2842) | Report `cawg.identity.cbor.invalid` instead of failing to load the manifest |
| [contentauth/c2pa-rs#2843](https://github.com/contentauth/c2pa-rs/pull/2843) | Resolve references into ingredient claims; report `hard_binding_incorrect` |
| [contentauth/c2pa-rs#2844](https://github.com/contentauth/c2pa-rs/pull/2844) | Enforce type-specific verified-identity fields; regenerate the ICA fixtures |
| [contentauth/c2pa-rs#3052](https://github.com/contentauth/c2pa-rs/pull/3052) | Decode `did:jwk` identifiers as unpadded base64url |
| [contentauth/c2pa-rs#3053](https://github.com/contentauth/c2pa-rs/pull/3053) | Report `cawg.ica.signer_payload.mismatch` when `c2paAsset` covers fewer assertions |
| [contentauth/c2pa-rs#3054](https://github.com/contentauth/c2pa-rs/pull/3054) | Reject an empty or blank `role` array |
| [contentauth/c2pa-rs#3055](https://github.com/contentauth/c2pa-rs/pull/3055) | Read metadata assertions with a JSON-LD `@context` array or no `@context` |
| [contentauth/c2pa-rs#3056](https://github.com/contentauth/c2pa-rs/pull/3056) | Report `cawg.identity.trusted` for a trusted named actor (stacked on #2837) |

With the first eight applied, c2pa-rs passes 59 of the original 61 cases, and #2844 fixes one
more. The remaining case, the interim trust model's certificate policies, is raised in
[contentauth/c2pa-rs#2845](https://github.com/contentauth/c2pa-rs/issues/2845).

The CAWG-Testfiles cases found five more c2pa-rs bugs, fixed by #3052 to #3056. With all of
these merged onto current c2pa-rs `main`, every CAWG-Testfiles case passes.

## Findings in the specifications

Turning the specs into tests surfaced a number of spec bugs and ambiguities. They
have been reported upstream:

| Specification | Reported |
| --- | --- |
| Identity Assertion | Status-code name mismatch ([#273](https://github.com/decentralized-identity/cawg-identity-assertion/pull/273)) · broken ICA JSON schemas ([#287](https://github.com/decentralized-identity/cawg-identity-assertion/pull/287)) · crypto-wallet example missing `address` ([#288](https://github.com/decentralized-identity/cawg-identity-assertion/pull/288)) · scope of identity-assertion failures ([#289](https://github.com/decentralized-identity/cawg-identity-assertion/issues/289)) · `well-formed` vs `credential.untrusted` ([#290](https://github.com/decentralized-identity/cawg-identity-assertion/issues/290)) · status `url` format ([#291](https://github.com/decentralized-identity/cawg-identity-assertion/issues/291)) |
| Metadata Assertion | Invalid JSON in the media-identifier example ([#14](https://github.com/decentralized-identity/cawg-metadata-assertion/pull/14)) |
| Training and Data Mining Assertion | CDDL that matches no assertion, a broken example, and `constraint_info` naming ([#11](https://github.com/decentralized-identity/cawg-training-and-data-mining-assertion/pull/11)) |

Where the spec is ambiguous, the suite says how it decides. For example, it accepts
either a label or a JUMBF URI as a status `url`, and accepts
`cawg.ica.untrusted_issuer` in any category, because an untrusted ICA issuer
shouldn't fail the whole C2PA Manifest. See [docs/coverage.md](docs/coverage.md).

## Roadmap

- **Draft specs we're tracking:** identity 1.3 [+vlei](https://cawg.io/identity/1.3-draft+vlei/),
  [+vc-vp](https://cawg.io/identity/1.3-draft+vc-vp/) and
  [+governance](https://cawg.io/identity/1.3-draft+governance/).
- **Specs not yet covered:** the Organizational Identity Profile and the Consent and
  Endorsement drafts.
- **Coverage gaps:** X.509 time stamps and revocation, and ICA revocation lists.

The full list is in [TODO.md](TODO.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- development setup
- adding rubric statements and validator cases
- regenerating fixtures

To build a profile on top of the suite rather than change it, see
[docs/plugins.md](docs/plugins.md).

Results from other validators are especially welcome.

## License

Licensed under either of the [MIT License](LICENSE-MIT) or the
[Apache License, Version 2.0](LICENSE-APACHE), at your option.

Third-party material keeps its own licence; see [NOTICE](NOTICE):
- Test images, certificates and keys from c2pa-rs (MIT).
- The rubric evaluator, builder, rubric validator and schema, adapted from the C2PA
  Conformance Task Force's [conformance-public](https://github.com/c2pa-org/conformance-public)
  repository (CC BY 4.0).

CAWG, C2PA, Content Credentials and related names belong to their respective
owners. Their use here doesn't imply endorsement.
