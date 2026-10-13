# Coverage

What each rubric statement checks, what the rubrics can't check, and what the
validator cases cover. Spec references are to the CAWG specification versions
named in each heading.

Statements marked *warn* report a warning rather than a failure.

## Identity Assertion 1.3

Statement IDs are `identity:<name>`. Statements marked *warn* report a warning
rather than a failure.

| Statement | Spec | Checks |
| --- | --- | --- |
| `identity_assertion_present` | §5.1 | At least one `cawg.identity` assertion exists |
| `assertion_label` | §5.1, §5.3 | Label is `cawg.identity` or `cawg.identity__N` |
| `required_fields` | §5.2 | `signer_payload` (with `referenced_assertions` and `sig_type`), `signature` and `pad1` are present |
| `referenced_assertions_nonempty` | §5.1.1 | `referenced_assertions` has at least one entry |
| `referenced_assertions_resolve` | §5.1.1, §7.1 | Every reference matches a label and hash listed in a claim in the store |
| `referenced_assertions_in_own_claim` (warn) | §5.1.1 | References resolve within the assertion's own claim |
| `no_duplicate_references` | §5.1.1, §7.1 | No assertion is referenced twice |
| `exactly_one_hard_binding` | §5.1.1, §7.1 | Exactly one hard-binding reference |
| `hard_binding_is_claims` | §5.1.1, §7.1 | The hard binding is the one in the assertion's own claim |
| `no_self_reference` | §5.1.1 | The assertion does not reference itself |
| `sig_type_known` (warn) | §5.1, §8 | `sig_type` is defined in 1.3 |
| `role_wellformed` | §5.1.2 | `role`, if present, is a non-empty array of non-empty strings |
| `role_cawg_namespace` (warn) | §5.1.2, §5.3 | `cawg.*` roles are ones the spec defines |
| `pads_zero` | §6.2, §7.1 | `pad1` and `pad2` are all zero bytes |
| `no_removed_fields` (warn) | §5.1 | No `expected_partial_claim`, `expected_claim_generator` or `expected_countersigners` |
| `x509_signature_decodable` | §8.2.1 | `cawg.x509.cose` signature is a COSE signature with a certificate |
| `x509_algorithm_allowed` | §8.2.1, §8.2.2 | Algorithm is in the C2PA §13.2 list |
| `ica_credential_visible` (warn) | §8.1.2 | The ICA credential is visible in crJSON (otherwise the ICA checks are skipped) |
| `ica_algorithm_allowed` | §8.1.4, §8.1.5 | Algorithm is in the C2PA §13.2 list |
| `ica_issuer_did` | §8.1.4, §8.1.5 | Issuer is a DID |
| `ica_valid_from_present` | §8.1.2.4 | `validFrom` / `issuanceDate` is present |
| `ica_verified_identities_nonempty` | §8.1.2.5 | `verifiedIdentities` is a non-empty array |
| `ica_verified_identity_required_fields` | §8.1.2.5 | Each entry has `type`, `provider.name` and `verifiedAt` |
| `ica_verified_identity_type_fields` | §8.1.2.5 | `name` / `username` / `address` / `uri` is present for the document, social media, wallet and web site types |
| `validation_no_failures` | §7.2, §8.1.5, §8.2.2 | The validator reported no `cawg.*` failure codes |
| `validation_status_reported` (warn) | §7.2 | The validator reported `cawg.identity.well-formed` or `cawg.identity.trusted` |

### Not covered by the rubric

- **Signatures and trust.** Rubrics read crJSON. They cannot verify signatures,
  certificate chains, time stamps or revocation. Those are validator
  responsibilities, covered by the validator cases.
- **ICA credential fields that crJSON leaves out.** crJSON exposes only
  `issuer`, `validFrom`, `validUntil` and `verifiedIdentities` from the
  credential. `@context`, `type`, `issuanceDate` and
  `credentialSubject.c2paAsset` cannot be checked.
- **Byte-level placeholder sizing** (§6.2).

## Metadata Assertion 1.1

Statement IDs are `metadata:<name>`. The metadata spec has no numbered sections, so references use
section names. 1.2-draft statements are warnings only.

| Statement | Spec | Checks |
| --- | --- | --- |
| `metadata_assertion_present` | 1.1 Assertion definition | At least one `cawg.metadata` assertion exists |
| `assertion_label` | 1.1 Assertion definition | Label is `cawg.metadata` or `cawg.metadata__N` |
| `json_ld_object` | 1.1; C2PA metadata common requirements | Content is a JSON object |
| `context_present` | 1.1; C2PA metadata common requirements | `@context` is present (object, URL string, or array of those) |
| `terms_defined_in_context` (warn) | 1.1; C2PA metadata common requirements | Every top-level field uses a prefix or term from `@context`, or is an absolute IRI. JSON-LD drops fields that fail this. Skipped for remote-only contexts |
| `context_iris_absolute` (warn) | 1.1 | Namespace IRIs in `@context` are absolute |
| `validation_no_failures` | 1.1 (C2PA Appendix B SHALL NOT apply) | The validator reported no failure codes for the metadata assertion |
| `gathered_referenced_by_identity` (warn) | 1.2-draft Use with identity assertion | Gathered metadata is referenced by an identity assertion in the same manifest |
| `urn_values_wellformed` (warn) | 1.2-draft Use with media industry identifiers | Top-level `urn:` values have the form `urn:<nid>:<nss>` |

Not covered:
- **JSON vs CBOR storage.** crJSON doesn't record whether the assertion was a JSON content box, as the spec requires.
- **Remote `@context` documents.** These aren't fetched.
- **Vocabulary choice.** The 1.2 draft recommends established namespaces such as Dublin Core; that's a judgement call, not a check.

## Training and Data Mining Assertion 1.1

Statement IDs are `training-mining:<name>`. The spec has no numbered sections, so references use
section names.

| Statement | Spec | Checks |
| --- | --- | --- |
| `tdm_assertion_present` | Assertion definition | At least one `cawg.training-mining` assertion exists |
| `assertion_label` | Overview | Label is `cawg.training-mining` or `cawg.training-mining__N` |
| `entries_present` | Schema and example | The assertion is a map containing an `entries` map. The 1.0 CDDL omitted `entries`, and 1.1 says it SHOULD be used; this suite follows the 1.1 CDDL and treats it as required |
| `entries_nonempty` | Overview | `entries` has one or more entries |
| `use_values_valid` | Overview; Schema | Every entry's `use` is `allowed`, `notAllowed` or `constrained` |
| `constraint_info_wellformed` | Schema | `constraint_info`, if present, is a non-empty string |
| `cawg_keys_defined` | Overview | `cawg.*` entry keys are the four defined ones; the prefix is reserved |
| `custom_keys_label_syntax` | Overview; C2PA Namespacing | Custom keys are entity-specific labels: two or more components matching `[a-zA-Z0-9][a-zA-Z0-9_-]*` |
| `constraints_info_spelling` (warn) | Overview vs Schema | No entry uses `constraints_info`, the prose spelling of `constraint_info` |
| `legacy_c2pa_names` (warn) | Overview (notice to implementers) | No C2PA 1.x `c2pa.training-mining` label or `c2pa.*` entry keys |
| `validation_no_failures` | Assertion definition | The validator reported no failure codes for the assertion |

Not covered:
- **Consumer behaviour.** Treating `constrained` as `notAllowed` can't be checked from crJSON.
- **IANA TLD check.** Whether a custom key's first component is a valid IANA top-level domain isn't checked.
- **String length.** The `max-tstr-length` bound on `constraint_info` isn't checked.

Both real-world Adobe ICA assets carry a legacy `c2pa.training-mining` assertion alongside
`cawg.training-mining`, so they get the `legacy_c2pa_names` warning.

## Validator cases

Each case names an asset and the codes that must, or must not, appear for it.
A case file sets which status entries a case looks at (`subject`): the identity
assertion, the metadata assertion, or the whole manifest.

[`identity-1.3-cases.yml`](../validator_tests/identity-1.3-cases.yml) has 49 cases:
- 13 for identity assertion structure and the validation procedure (§5, §7.1, §7.2)
- 7 for X.509 signatures and the trust model (§8.2)
- 29 for ICA validation (§8.1.5)

Every identity case also checks one consistency rule: a validator must not
report `cawg.identity.well-formed` or `cawg.identity.trusted` for an assertion
that also has a `cawg.*` failure. §7.2 defines those success codes as "validated",
and §7.1, §8.1.5 and §8.2.2 failures reject the assertion. The one exception is
`cawg.x509.credential.untrusted`. §7.2 defines `well-formed` as "validated, no root of
trust identified", which is exactly an untrusted chain, so the spec is ambiguous there.

16 of the identity cases use assets from the c2pa-rs generator branch (see
[Generated identity fixtures](../CONTRIBUTING.md#generated-identity-fixtures)). Their X.509 trust-model cases
depend on `tools/crjson-gen/generated_trust_anchor.pem`, which `cawg_test_settings.toml`
includes as a CAWG trust anchor. Configure a validator under test the same way.

[`metadata-1.1-cases.yml`](../validator_tests/metadata-1.1-cases.yml) has 8 cases. The
metadata spec defines no status codes, so these check that metadata never causes
a failure:
- Fields outside the `c2pa.metadata` allowed list must not be rejected.
- Gathered metadata, multiple instances, undefined prefixes and media
  identifiers must all validate.
- An identity assertion that attests to the metadata must validate.

[`training-mining-1.1-cases.yml`](../validator_tests/training-mining-1.1-cases.yml) has 4 cases. The
spec defines no status codes either, so these check that valid assertions never cause a failure:
all four keys, a custom key, a constrained entry, and identity attestation. The invalid
training-mining assets exist only for the generator rubric.
