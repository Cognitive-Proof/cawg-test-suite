#!/usr/bin/env python3
"""Regenerate the hand-built crJSON unit fixtures under this directory.

Each rubric statement <category>:<rule> gets, in <category>/:
  <rule>-pos.json  minimal crJSON on which every statement of that rubric passes
  <rule>-neg.json  the same crJSON with one defect that the rule must catch

Usage: python fixtures/unit/make_unit_fixtures.py
"""

import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

MANIFEST = "urn:c2pa:00000000-0000-4000-8000-000000000001"
INGREDIENT = "urn:c2pa:00000000-0000-4000-8000-000000000002"

H_DATA = "b64'ZGF0YWhhc2hkYXRhaGFzaGRhdGFoYXNoZGF0YWhhc2g='"
H_ACTIONS = "b64'YWN0aW9uc2FjdGlvbnNhY3Rpb25zYWN0aW9uc2FjdGk='"
H_IDENTITY = "b64'aWRlbnRpdHlpZGVudGl0eWlkZW50aXR5aWRlbnRpdHk='"
H_ING_DATA = "b64'aW5ncmVkaWVudGluZ3JlZGllbnRpbmdyZWRpZW50aW4='"
H_ING_ACTIONS = "b64'aW5nYWN0aW9uc2luZ2FjdGlvbnNpbmdhY3Rpb25zaW4='"


def ref(label, h, manifest=None):
    if manifest:
        return {"url": f"self#jumbf=/c2pa/{manifest}/c2pa.assertions/{label}", "hash": h}
    return {"url": f"self#jumbf=c2pa.assertions/{label}", "hash": h}


def status(code, label="cawg.identity", manifest=MANIFEST):
    return {"code": code, "url": f"self#jumbf=/c2pa/{manifest}/c2pa.assertions/{label}"}


X509_SIGNATURE = {
    "algorithm": "es256",
    "certificateInfo": {
        "serialNumber": "01",
        "issuer": {"O": "Example CA", "CN": "Example Issuing CA"},
        "subject": {"O": "Example Org", "CN": "Example Signer"},
        "validity": {"notBefore": "2026-01-01T00:00:00+00:00",
                     "notAfter": "2027-01-01T00:00:00+00:00"},
    },
}

ICA_SIGNATURE = {
    "algorithm": "ed25519",
    "issuer": "did:web:ica.example.com",
    "validFrom": "2026-01-01T00:00:00Z",
    "verifiedIdentities": [{
        "type": "cawg.social_media",
        "username": "example",
        "uri": "https://social.example.com/example",
        "provider": {"id": "https://social.example.com", "name": "Example Social"},
        "method": "cawg.federated_login",
        "verifiedAt": "2026-01-01T00:00:00Z",
    }],
    "credentialType": "IdentityClaimsAggregation",
}


def base(sig_type="cawg.x509.cose"):
    signature = X509_SIGNATURE if sig_type == "cawg.x509.cose" else ICA_SIGNATURE
    success = [status("cawg.identity.well-formed")]
    if sig_type == "cawg.identity_claims_aggregation":
        success.insert(0, status("cawg.ica.credential_valid"))
    return {
        "@context": {"@vocab": "https://contentcredentials.org/crjson"},
        "jsonGenerator": {"name": "cawg-test-suite unit fixture", "version": "0.1.0"},
        "manifests": [{
            "label": MANIFEST,
            "assertions": {
                "c2pa.hash.data": {"alg": "sha256", "hash": H_DATA, "pad": "b64''"},
                "c2pa.actions.v2": {"actions": [{"action": "c2pa.created"}]},
                "cawg.identity": {
                    "signer_payload": {
                        "referenced_assertions": [
                            ref("c2pa.actions.v2", H_ACTIONS),
                            ref("c2pa.hash.data", H_DATA),
                        ],
                        "sig_type": sig_type,
                        "role": ["cawg.creator"],
                    },
                    "signature": copy.deepcopy(signature),
                    "pad1": "b64'AAAAAAAAAA=='",
                    "pad2": "b64''",
                },
            },
            "claim.v2": {
                "instanceID": "xmp:iid:00000000-0000-4000-8000-000000000003",
                "claim_generator_info": {"name": "unit fixture"},
                "alg": "sha256",
                "signature": f"self#jumbf=/c2pa/{MANIFEST}/c2pa.signature",
                "created_assertions": [
                    ref("c2pa.actions.v2", H_ACTIONS),
                    ref("c2pa.hash.data", H_DATA),
                ],
                "gathered_assertions": [ref("cawg.identity", H_IDENTITY)],
            },
            "signature": {"algorithm": "es256"},
            "validationResults": {"success": success, "informational": [], "failure": []},
        }],
    }


def with_ingredient(doc):
    """Add an ingredient manifest whose claim lists its own hard binding and actions."""
    doc["manifests"].append({
        "label": INGREDIENT,
        "assertions": {
            "c2pa.hash.data": {"alg": "sha256", "hash": H_ING_DATA, "pad": "b64''"},
            "c2pa.actions.v2": {"actions": [{"action": "c2pa.created"}]},
        },
        "claim.v2": {
            "created_assertions": [
                ref("c2pa.actions.v2", H_ING_ACTIONS),
                ref("c2pa.hash.data", H_ING_DATA),
            ],
            "gathered_assertions": [],
        },
        "signature": {"algorithm": "es256"},
        "validationResults": {"success": [], "informational": [], "failure": []},
    })
    return doc


def ia(doc):
    return doc["manifests"][0]["assertions"]["cawg.identity"]


def sp(doc):
    return ia(doc)["signer_payload"]


def refs(doc):
    return sp(doc)["referenced_assertions"]


def vi(doc):
    return ia(doc)["signature"]["verifiedIdentities"][0]


def m(fn, sig_type="cawg.x509.cose"):
    """Build a negative fixture by applying fn to a fresh base document."""
    doc = base(sig_type)
    result = fn(doc)
    return result if result is not None else doc


ICA = "cawg.identity_claims_aggregation"


def rename_identity(doc, new_label):
    manifest = doc["manifests"][0]
    manifest["assertions"][new_label] = manifest["assertions"].pop("cawg.identity")
    for entries in manifest["validationResults"].values():
        for entry in entries:
            entry["url"] = entry["url"].replace("/cawg.identity", "/" + new_label)


# rule -> (positive fixture, negative fixture)
IDENTITY_CASES = {
    "identity_assertion_present": (
        base(),
        m(lambda d: d["manifests"][0]["assertions"].pop("cawg.identity") and None)),
    "assertion_label": (
        m(lambda d: rename_identity(d, "cawg.identity__1")),
        m(lambda d: rename_identity(d, "cawg.identity__x"))),
    "required_fields": (
        base(),
        m(lambda d: ia(d).pop("pad1") and None)),
    "referenced_assertions_nonempty": (
        base(),
        m(lambda d: sp(d).update(referenced_assertions=[]))),
    "referenced_assertions_resolve": (
        base(),
        m(lambda d: refs(d)[0].update(hash="b64'bm90LWluLWFueS1jbGFpbS1ub3QtaW4tYW55LWM='"))),
    "referenced_assertions_in_own_claim": (
        with_ingredient(base()),
        m(lambda d: with_ingredient(d) and refs(d).insert(
            0, ref("c2pa.actions.v2", H_ING_ACTIONS, INGREDIENT)))),
    "no_duplicate_references": (
        base(),
        m(lambda d: refs(d).append(ref("c2pa.actions.v2", H_ACTIONS)))),
    "exactly_one_hard_binding": (
        base(),
        m(lambda d: refs(d).pop() and None)),
    "hard_binding_is_claims": (
        with_ingredient(base()),
        m(lambda d: with_ingredient(d) and refs(d).__setitem__(
            1, ref("c2pa.hash.data", H_ING_DATA, INGREDIENT)))),
    "no_self_reference": (
        base(),
        m(lambda d: refs(d).append(ref("cawg.identity", H_IDENTITY)))),
    "sig_type_known": (
        base(),
        m(lambda d: sp(d).update(sig_type="com.example.signature"))),
    "role_wellformed": (
        base(),
        m(lambda d: sp(d).update(role=["cawg.creator", ""]))),
    "role_cawg_namespace": (
        m(lambda d: sp(d).update(role=["cawg.editor", "com.example.reviewer"])),
        m(lambda d: sp(d).update(role=["cawg.author"]))),
    "pads_zero": (
        m(lambda d: ia(d).update(pad1=[0, 0, 0, 0], pad2="b64'AAA='")),
        m(lambda d: ia(d).update(pad1="b64'AAAB'"))),
    "no_removed_fields": (
        base(),
        m(lambda d: sp(d).update(expected_partial_claim={"alg": "sha256", "hash": H_DATA}))),
    "x509_signature_decodable": (
        base(),
        m(lambda d: ia(d).update(signature="b64'0oRDoQEmoFkB'"))),
    "x509_algorithm_allowed": (
        base(),
        m(lambda d: ia(d)["signature"].update(algorithm="rs256"))),
    "ica_credential_visible": (
        base(ICA),
        m(lambda d: ia(d).update(signature=copy.deepcopy(X509_SIGNATURE)), ICA)),
    "ica_algorithm_allowed": (
        base(ICA),
        m(lambda d: ia(d)["signature"].pop("algorithm") and None, ICA)),
    "ica_issuer_did": (
        m(lambda d: ia(d)["signature"].update(issuer={"id": "did:web:ica.example.com",
                                                      "name": "Example ICA"}), ICA),
        m(lambda d: ia(d)["signature"].update(issuer="https://ica.example.com"), ICA)),
    "ica_valid_from_present": (
        base(ICA),
        m(lambda d: ia(d)["signature"].pop("validFrom") and None, ICA)),
    "ica_verified_identities_nonempty": (
        base(ICA),
        m(lambda d: ia(d)["signature"].update(verifiedIdentities=[]), ICA)),
    "ica_verified_identity_required_fields": (
        base(ICA),
        m(lambda d: vi(d)["provider"].pop("name") and None, ICA)),
    "ica_verified_identity_type_fields": (
        m(lambda d: ia(d)["signature"]["verifiedIdentities"].extend([
            {"type": "cawg.web_site", "uri": "https://example.com",
             "provider": {"name": "Example DNS"}, "verifiedAt": "2026-01-01T00:00:00Z"},
            {"type": "cawg.crypto_wallet", "address": "0x0000000000000000000000000000000000000000",
             "provider": {"name": "Example Wallet"}, "verifiedAt": "2026-01-01T00:00:00Z"},
            {"type": "cawg.document_verification", "name": "Example Person",
             "provider": {"name": "Example KYC"}, "verifiedAt": "2026-01-01T00:00:00Z"},
        ]), ICA),
        m(lambda d: vi(d).pop("username") and None, ICA)),
    "validation_no_failures": (
        base(),
        m(lambda d: d["manifests"][0]["validationResults"]["failure"].append(
            status("cawg.identity.pad.invalid")))),
    "validation_status_reported": (
        base(),
        m(lambda d: d["manifests"][0]["validationResults"].update(success=[]))),
}


H_METADATA = "b64'bWV0YWRhdGFtZXRhZGF0YW1ldGFkYXRhbWV0YWRhdGE='"

METADATA_VALUE = {
    "@context": {
        "dc": "http://purl.org/dc/elements/1.1/",
        "photoshop": "http://ns.adobe.com/photoshop/1.0/",
    },
    "dc:title": "Harbour at dawn",
    "dc:creator": ["Example Photographer"],
    "photoshop:City": "Halifax",
}


def mbase(gathered=False, identity_refs=False):
    """crJSON with one cawg.metadata assertion (created, or gathered).

    identity_refs: the identity assertion also references cawg.metadata.
    """
    doc = base()
    manifest = doc["manifests"][0]
    manifest["assertions"]["cawg.metadata"] = copy.deepcopy(METADATA_VALUE)
    claim = manifest["claim.v2"]
    target = claim["gathered_assertions"] if gathered else claim["created_assertions"]
    target.insert(0, ref("cawg.metadata", H_METADATA))
    if identity_refs:
        refs(doc).insert(0, ref("cawg.metadata", H_METADATA))
    return doc


def md(doc, label="cawg.metadata"):
    return doc["manifests"][0]["assertions"][label]


def mm(fn, **kwargs):
    doc = mbase(**kwargs)
    result = fn(doc)
    return result if result is not None else doc


def rename_metadata(doc, new_label):
    manifest = doc["manifests"][0]
    manifest["assertions"][new_label] = manifest["assertions"].pop("cawg.metadata")
    for entry in manifest["claim.v2"]["created_assertions"]:
        entry["url"] = entry["url"].replace("/cawg.metadata", "/" + new_label)


METADATA_CASES = {
    "metadata_assertion_present": (
        mbase(),
        base()),
    "assertion_label": (
        mm(lambda d: rename_metadata(d, "cawg.metadata__1")),
        mm(lambda d: rename_metadata(d, "cawg.metadata.ingredient"))),
    "json_ld_object": (
        mbase(),
        mm(lambda d: d["manifests"][0]["assertions"].update({"cawg.metadata": ["not", "an", "object"]}))),
    "context_present": (
        mm(lambda d: md(d).update({"@context": [
            "https://example.com/remote-context.jsonld",
            {"dc": "http://purl.org/dc/elements/1.1/",
             "photoshop": "http://ns.adobe.com/photoshop/1.0/"}]})),
        mm(lambda d: md(d).pop("@context") and None)),
    "terms_defined_in_context": (
        mm(lambda d: md(d).update({"http://purl.org/dc/terms/rights": "CC-BY-4.0"})),
        mm(lambda d: md(d).update({"exif:GPSLatitude": "39,21.102N"}))),
    "context_iris_absolute": (
        mm(lambda d: md(d)["@context"].update({
            "iptc": {"@id": "http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/"},
            "media": "urn:example:media:"})),
        mm(lambda d: md(d)["@context"].update({"photoshop": "ns/photoshop/1.0/"}))),
    "validation_no_failures": (
        mbase(),
        mm(lambda d: d["manifests"][0]["validationResults"]["failure"].append(
            status("assertion.metadata.disallowed", "cawg.metadata")))),
    "gathered_referenced_by_identity": (
        mbase(gathered=True, identity_refs=True),
        mbase(gathered=True)),
    "urn_values_wellformed": (
        mm(lambda d: md(d).update({"dc:identifier": [
            "The Great Train Robbery", "urn:eidr:10.5240/7791-8534-2C23-9030-8610-5"]})),
        mm(lambda d: md(d).update({"dc:identifier": "urn:eidr"}))),
}


def write_cases(category, cases):
    out_dir = os.path.join(HERE, category)
    os.makedirs(out_dir, exist_ok=True)
    for name in os.listdir(out_dir):
        if name.endswith(".json"):
            os.remove(os.path.join(out_dir, name))
    for rule, (pos, neg) in cases.items():
        for suffix, doc in (("pos", pos), ("neg", neg)):
            with open(os.path.join(out_dir, f"{rule}-{suffix}.json"), "w") as f:
                json.dump(doc, f, indent=2)
                f.write("\n")
    print(f"Wrote {2 * len(cases)} fixtures to {out_dir}")


def main():
    write_cases("identity", IDENTITY_CASES)
    write_cases("metadata", METADATA_CASES)


if __name__ == "__main__":
    main()
