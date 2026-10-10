# TODO

Open items for cawg-test-suite. Add new items here. Remove items, or move them to **Done**, as they're resolved.

## Spec PRs and issues (upstream)

- [ ] **decentralized-identity/cawg-identity-assertion#273**: `network_traffic_blocked` vs `network_traffic_required`. Open; waiting on review.
- [ ] **decentralized-identity/cawg-identity-assertion#287**: ICA JSON schema `$ref` fix plus alignment with the spec (role, social_media `uri`, `referenced_assertions.url`). Open; waiting on review.
  - [ ] Follow up on the question raised there: is `provider` required for `cawg.web_site`? The text says yes, but the example and schema say no.
- [ ] **decentralized-identity/cawg-identity-assertion#288**: `cawg.crypto_wallet` example uses `username` instead of `address`. Open; waiting on review.
- [ ] **decentralized-identity/cawg-metadata-assertion#14**: the media identifier example has trailing commas (invalid JSON). Open; waiting on review.
- [ ] **decentralized-identity/cawg-training-and-data-mining-assertion#11**: one PR, three commits (open; waiting on review):
  - CDDL sockets `$training-mining-entries-map` / `$training-mining-map-entry` are undefined, so the CDDL rejects every assertion (confirmed with `cddl` 0.10.7)
  - the CBOR diagnostic example is missing the braces around `entries`
  - the prose says `constraints_info`, but the CDDL says `constraint_info`
- [ ] **cawg-training-and-data-mining-assertion (not filed)**: the spec still links C2PA 2.0 for label syntax. The metadata and identity specs now reference 2.3/2.4.
- [ ] **cawg-identity-assertion issue (not filed)**: §7.2 says the status `url` MUST be the assertion label, but C2PA §15.2 and c2pa-rs use a JUMBF URI. Needs a working-group decision. The suite accepts both.
- [ ] **cawg-identity-assertion (minor, not filed)**: both ICA schemas share the same `$id` (`https://cawg.io/schemas/v1/creator-identity-assertion.json`).
- [ ] **cawg-identity-assertion (minor, not filed)**: the repo's "Validate Schemas and Examples" workflow exits 0 when validation fails, so broken schemas and examples don't fail CI.
- [ ] **cawg-identity-assertion (minor, not filed)**: X.509 trust model says "No certificate policy or trust anchors are required for `id-kp-documentSigning`". Unclear whether that means any documentSigning certificate counts as trusted.

## c2pa-rs and other implementations

These are deviations found by the validator cases; they're listed in `validator_tests/baselines/c2pa-rs-0.91.2.yml`. None are reported upstream yet.

- [ ] `cawg.identity.cbor.invalid` is not surfaced in crJSON for malformed CBOR.
- [ ] `cawg.identity.well-formed` is reported alongside `cawg.identity.*` failures (5 cases).
- [ ] `cawg.ica.invalid_issuer` is reported where the spec (and c2pa-rs's own test) expects `cawg.ica.did_unsupported_method`.
- [ ] `cawg.ica.untrusted_issuer` is reported as informational, but the spec classifies it as a failure.
- [ ] Identity references into an ingredient claim are reported as `cawg.identity.assertion.mismatch`. §7.1 step 2 allows them (`identity/references_ingredient_assertion` from the generator branch). Because of this, `hard_binding_incorrect` is never reached either.
- [ ] ICA: empty `verifiedIdentities` and a verified identity without `provider.name` are reported as `cawg.ica.invalid_verifiable_credential`. §8.1.5 requires `cawg.ica.verified_identities.missing` / `.invalid`.
- [ ] ICA: a `cawg.crypto_wallet` entry without `address`, and an unsupported `credentialStatus` method, both pass as `cawg.ica.credential_valid`. Expected: `verified_identities.invalid` and `revocation.unsupported`.
- [ ] c2pa-rs's own `ica_example_identities()` (`sdk/src/identity/tests/fixtures/claim_aggregation/ica_credential_example.rs`) copies the spec's crypto_wallet example without `address`. All bundled `ica_validation/*.jpg` fixtures inherit it.
- [ ] Interim trust model: certificate-policy OIDs are not enforced. A mailbox-validated certificate chained to a configured anchor is reported `cawg.x509.credential.trusted` (`x509_interim_mailbox_policy`).
- [ ] `cawg.identity.well-formed` is also reported alongside X.509 rejections (`cawg.x509.signature.outside_validity`, `cawg.x509.credential.untrusted`).
- [ ] With two identity assertions, both sets of statuses use url `.../cawg.identity`; `cawg.identity__1` gets none of its own (`identity_multiple_assertions`).
- [ ] `cawg.x509.algorithm.unsupported` is reported with url `Cose_Sign1` instead of the assertion label (§7.2).
- [ ] crJSON inconsistencies:
  - `pad1` is written as a byte array.
  - Hashes in `referenced_assertions` keep a trailing `'` that claim hashes don't.
  - ICA crJSON omits the VC's `@context`, `type`, `issuanceDate` and `c2paAsset`.
- [ ] Adobe's ICA assets (`adobe_connected_identities`, `ims_multiple_manifests`) write a legacy `c2pa.training-mining` assertion alongside `cawg.training-mining`. Probably deliberate for compatibility; worth confirming with Adobe.
- [ ] Re-run the suite against a newer c2pa-rs (upstream `main` or the next release). The tool builds against upstream `main` via `--config patch.crates-io.c2pa.path=...`, but the results were never compared. Update the baseline if anything is fixed.

## Coverage gaps in this suite

- [ ] Extend the c2pa-rs generator branch (`cawg/conformance-fixtures`) with the remaining gaps below, then re-import (README "Generated identity fixtures").

- [ ] Identity: still no fixtures (even on the generator branch) for:
  - X.509 time stamp codes
  - OCSP/revocation, `cawg.identity.credential_revoked`; c2pa-rs has OCSP test material in `sdk/tests/fixtures/crypto/ocsp/`
  - ICA revocation beyond `revocation.unsupported`
  - the interim trust model's 31 March 2027 cutoff
- [ ] The interim trust fixtures (`x509/interim_*`) are only meaningful until 2027-03-31 unless they carry a trusted time stamp.
- [ ] Identity: most c2pa-rs ICA test assets show a certificate rather than the VC in crJSON, so the ICA rubric checks only run on the hand-built fixtures and the two real-world assets.
- [ ] Metadata: the "JSON content type box" requirement can't be checked from crJSON (it doesn't record JSON vs CBOR).
- [ ] Metadata: remote `@context` documents are not fetched. `terms_defined_in_context` skips them.
- [ ] Training and data mining: no validator expectations for the invalid assets (bad `use`, undefined `cawg.*` key, missing `entries`); the spec defines no status codes. Revisit if CAWG adds any.
- [ ] Training and data mining: decide whether a missing `entries` map stays a failure. The 1.1 CDDL requires it, but the note says it SHOULD be used; currently it's a failure.
- [ ] Not yet covered at all:
  - Organizational Identity Profile 1.0
  - Consent and Endorsement assertions (drafts)
  - Identity 1.3 drafts (+vc-vp, +vlei, +governance)

## Housekeeping

- [ ] Rename the local folder `~/Github/cawg-conformance` to `cawg-test-suite`, to match the GitHub repo.
- [ ] Keep `cawg_rubric/` engine code in sync with c2pa-org/conformance `asset-rubrics/` (adapted from `b6d5a1b`).
- [ ] When the metadata spec 1.2 is ratified, promote the 1.2-draft warnings to the rules the final text makes normative, and rename the rubric.

## Done

- [x] Identity Assertion 1.3 rubric, validator cases and fixtures.
- [x] Metadata Assertion 1.1 rubric (plus 1.2-draft warnings), validator cases, and signed assets via `make-assets`.
- [x] c2pa-rs generator branch `cawg/conformance-fixtures` (pushed to mrappard/c2pa-rs-text-support). 16 identity / X.509 / ICA fixtures imported, with 16 validator cases and the minted CAWG trust anchor.
- [x] Training and Data Mining Assertion 1.1 rubric, validator cases, and signed assets (`make-assets training-mining`).
- [x] Repo published as Cognitive-Proof/cawg-test-suite and renamed from "CAWG Conformance".
