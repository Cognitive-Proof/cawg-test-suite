#!/usr/bin/env python3
"""Regenerate the hand-built crJSON unit fixtures for the example music profile.

Each statement the plugin adds or tightens gets, in <category>/:
  <rule>-pos.json  minimal crJSON on which the whole music-1.0 profile passes
  <rule>-neg.json  the same crJSON with one defect that the rule must catch

Usage: python fixtures/unit/make_unit_fixtures.py
"""

import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

MANIFEST = "urn:c2pa:00000000-0000-4000-8000-0000000000a1"

H_DATA = "b64'ZGF0YWhhc2hkYXRhaGFzaGRhdGFoYXNoZGF0YWhhc2g='"
H_ACTIONS = "b64'YWN0aW9uc2FjdGlvbnNhY3Rpb25zYWN0aW9uc2FjdGk='"
H_IDENTITY = "b64'aWRlbnRpdHlpZGVudGl0eWlkZW50aXR5aWRlbnRpdHk='"
H_METADATA = "b64'bWV0YWRhdGFtZXRhZGF0YW1ldGFkYXRhbWV0YWRhdGE='"


def ref(label, h):
    return {"url": f"self#jumbf=c2pa.assertions/{label}", "hash": h}


def status(code, label):
    return {"code": code, "url": f"self#jumbf=/c2pa/{MANIFEST}/c2pa.assertions/{label}"}


def base():
    """A recording whose publisher's identity assertion attests its metadata."""
    return {
        "@context": {"@vocab": "https://contentcredentials.org/crjson"},
        "jsonGenerator": {"name": "example-music unit fixture", "version": "0.1.0"},
        "manifests": [{
            "label": MANIFEST,
            "assertions": {
                "c2pa.hash.data": {"alg": "sha256", "hash": H_DATA, "pad": "b64''"},
                "c2pa.actions.v2": {"actions": [{"action": "c2pa.created"}]},
                "cawg.metadata": {
                    "@context": {"dc": "http://purl.org/dc/elements/1.1/"},
                    "dc:title": "Example Song",
                    "dc:creator": ["Example Artist"],
                    "dc:identifier": ["urn:isrc:ZZ-XA1-26-00001"],
                },
                "cawg.identity": {
                    "signer_payload": {
                        "referenced_assertions": [
                            ref("cawg.metadata", H_METADATA),
                            ref("c2pa.hash.data", H_DATA),
                        ],
                        "sig_type": "cawg.x509.cose",
                        "role": ["cawg.publisher"],
                    },
                    "signature": {
                        "algorithm": "es256",
                        "certificateInfo": {
                            "serialNumber": "01",
                            "issuer": {"O": "Example CA", "CN": "Example Issuing CA"},
                            "subject": {"O": "Example Records", "CN": "Example Records Publishing"},
                            "validity": {"notBefore": "2026-01-01T00:00:00+00:00",
                                         "notAfter": "2027-01-01T00:00:00+00:00"},
                        },
                    },
                    "pad1": "b64''",
                    "pad2": "b64''",
                },
            },
            "claim.v2": {
                "instanceID": "xmp:iid:00000000-0000-4000-8000-0000000000a3",
                "claim_generator_info": {"name": "unit fixture"},
                "alg": "sha256",
                "signature": f"self#jumbf=/c2pa/{MANIFEST}/c2pa.signature",
                "created_assertions": [
                    ref("c2pa.actions.v2", H_ACTIONS),
                    ref("c2pa.hash.data", H_DATA),
                ],
                "gathered_assertions": [
                    ref("cawg.metadata", H_METADATA),
                    ref("cawg.identity", H_IDENTITY),
                ],
            },
            "signature": {"algorithm": "es256"},
            "validationResults": {
                "success": [status("cawg.identity.well-formed", "cawg.identity")],
                "informational": [],
                "failure": [],
            },
        }],
    }


def md(doc):
    return doc["manifests"][0]["assertions"]["cawg.metadata"]


def sp(doc):
    return doc["manifests"][0]["assertions"]["cawg.identity"]["signer_payload"]


def m(fn):
    """Apply fn to a fresh base document."""
    doc = base()
    result = fn(doc)
    return result if result is not None else doc


def unreferenced(doc):
    sp(doc)["referenced_assertions"].pop(0)


CASES = {
    "music": {
        "isrc_present": (
            base(),
            m(lambda d: md(d).update({"dc:identifier": ["Example Song"]}))),
        "isrc_wellformed": (
            # A single string and an unhyphenated code are fine too.
            m(lambda d: md(d).update({"dc:identifier": "urn:isrc:ZZXA12600001"})),
            m(lambda d: md(d).update({"dc:identifier": ["urn:isrc:ZZ-XA1-26-001"]}))),
        "title_present": (
            base(),
            m(lambda d: md(d).pop("dc:title") and None)),
        "publisher_attests_metadata": (
            base(),
            m(lambda d: sp(d).update({"role": ["cawg.creator"]}))),
    },
    # Core statements this profile tightens from warnings to failures.
    "metadata": {
        "gathered_referenced_by_identity": (
            base(),
            m(unreferenced)),
        "urn_values_wellformed": (
            base(),
            m(lambda d: md(d)["dc:identifier"].append("urn:isrc"))),
    },
}


def main():
    for category, cases in CASES.items():
        out_dir = os.path.join(HERE, category)
        os.makedirs(out_dir, exist_ok=True)
        for name in os.listdir(out_dir):
            if name.endswith(".json"):
                os.remove(os.path.join(out_dir, name))
        for rule, (pos, neg) in cases.items():
            for suffix, doc in (("pos", pos), ("neg", neg)):
                with open(os.path.join(out_dir, f"{rule}-{suffix}.json"), "w") as f:
                    json.dump(copy.deepcopy(doc), f, indent=2)
                    f.write("\n")
        print(f"Wrote {2 * len(cases)} fixtures to {out_dir}")


if __name__ == "__main__":
    main()
