//! Build signed test assets for CAWG assertions that c2pa-rs can write directly
//! (metadata, training and data mining).
//!
//! Usage: make-assets <assets-dir> [group]
//!
//! Each recipe belongs to a group and is written to `<assets-dir>/<group>/`.
//! Pass a group (`metadata`, `training-mining`) to rebuild only that group.
//!
//! Each recipe signs `source/no_manifest.jpg` with the c2pa-rs test
//! certificates in `signing_settings.toml`. Recipes with `identity: true` also
//! get a CAWG X.509 identity assertion whose referenced assertions are the
//! recipe's `references` (the hard binding is always added by c2pa-rs).
//!
//! A metadata assertion without `@context` cannot be built: c2pa-rs refuses to
//! sign it. That case is covered by the hand-built unit fixtures only.
//!
//! Signatures, instance IDs and thumbnails differ on every run, so the assets
//! committed under fixtures/assets/ are the source of truth. Re-run this only
//! when a recipe changes, then regenerate the crJSON with crjson-gen.

use std::{fs, path::PathBuf, process::ExitCode};

use c2pa::{Builder, Context};
use serde_json::{json, Value};

const SETTINGS: &str = include_str!("../../signing_settings.toml");
const SOURCE: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/source/no_manifest.jpg");

struct Recipe {
    group: &'static str,
    name: &'static str,
    identity: bool,
    references: &'static [&'static str],
    assertions: Value,
}

fn metadata(created: bool, data: Value) -> Value {
    json!({ "label": "cawg.metadata", "kind": "Json", "created": created, "data": data })
}

/// The image example from the CAWG metadata assertion specification.
fn spec_image_example() -> Value {
    json!({
        "@context": {
            "exif": "http://ns.adobe.com/exif/1.0/",
            "exifEX": "http://cipa.jp/exif/2.32/",
            "tiff": "http://ns.adobe.com/tiff/1.0/",
            "Iptc4xmpCore": "http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/",
            "Iptc4xmpExt": "http://iptc.org/std/Iptc4xmpExt/2008-02-29/",
            "dc": "http://purl.org/dc/elements/1.1/",
            "photoshop": "http://ns.adobe.com/photoshop/1.0/"
        },
        "photoshop:DateCreated": "Aug 31, 2022",
        "Iptc4xmpExt:DigitalSourceType": "https://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture",
        "exif:GPSVersionID": "2.2.0.0",
        "exif:GPSLatitude": "39,21.102N",
        "exif:GPSLongitude": "74,26.5737W",
        "exif:GPSAltitudeRef": 0,
        "exif:GPSAltitude": "100963/29890",
        "exif:GPSTimeStamp": "2019-09-22T18:22:57Z",
        "tiff:Make": "CameraCompany",
        "tiff:Model": "Shooter S1",
        "dc:creator": ["Example Photographer"]
    })
}

/// Fields that are not on the c2pa.metadata allowed list (C2PA Appendix B).
fn outside_allowlist() -> Value {
    json!({
        "@context": {
            "dc": "http://purl.org/dc/elements/1.1/",
            "xmpRights": "http://ns.adobe.com/xap/1.0/rights/",
            "example": "https://example.com/ns/media/1.0/"
        },
        "dc:title": "Harbour at dawn",
        "dc:contributor": ["Example Editor"],
        "xmpRights:UsageTerms": "Editorial use only",
        "example:assignmentId": "A-2026-0042"
    })
}

/// The media industry identifier example from the 1.2 draft (trailing commas removed).
fn media_identifiers() -> Value {
    json!({
        "@context": { "dc": "http://purl.org/dc/elements/1.1/" },
        "dc:contributor": ["Edwin Stanton Porter", "urn:doi:10.23/EF98-D5B3-1931-90A8-F50C"],
        "dc:identifier": ["The Great Train Robbery", "urn:eidr:10.5240/7791-8534-2C23-9030-8610-5"],
        "dc:date": "1903-12-01",
        "dc:type": "MovingImage"
    })
}

/// A cawg.training-mining assertion (CBOR, which is the c2pa-rs default kind).
fn training_mining(created: bool, data: Value) -> Value {
    json!({ "label": "cawg.training-mining", "created": created, "data": data })
}

fn tdm_all_entries() -> Value {
    json!({ "entries": {
        "cawg.data_mining": { "use": "allowed" },
        "cawg.ai_inference": { "use": "allowed" },
        "cawg.ai_generative_training": { "use": "notAllowed" },
        "cawg.ai_training": { "use": "notAllowed" }
    }})
}

fn tdm_constrained() -> Value {
    json!({ "entries": {
        "cawg.ai_generative_training": { "use": "notAllowed" },
        "cawg.data_mining": {
            "use": "constrained",
            "constraint_info": "https://example.com/policies/data-mining"
        }
    }})
}

fn training_mining_recipes() -> Vec<Recipe> {
    let tdm = |name, identity, references, assertions| Recipe {
        group: "training-mining",
        name,
        identity,
        references,
        assertions,
    };
    vec![
        tdm("all_entries", false, &[], json!([training_mining(true, tdm_all_entries())])),
        tdm("constrained_identity_attested", true, &["cawg.training-mining"],
            json!([training_mining(false, tdm_constrained())])),
        tdm("custom_key", false, &[], json!([training_mining(true, json!({ "entries": {
            "cawg.ai_training": { "use": "allowed" },
            "com.example.ai_fine_tuning": { "use": "notAllowed" }
        }}))])),
        tdm("invalid_use_value", false, &[], json!([training_mining(true, json!({ "entries": {
            "cawg.ai_training": { "use": "sometimes" }
        }}))])),
        tdm("undefined_cawg_key", false, &[], json!([training_mining(true, json!({ "entries": {
            "cawg.ai_fine_tuning": { "use": "notAllowed" }
        }}))])),
        tdm("missing_entries", false, &[], json!([training_mining(true, json!({
            "cawg.ai_training": { "use": "notAllowed" },
            "cawg.ai_generative_training": { "use": "notAllowed" }
        }))])),
        tdm("constraints_info_spelling", false, &[], json!([training_mining(true, json!({ "entries": {
            "cawg.data_mining": { "use": "constrained", "constraints_info": "Contact the rights holder" }
        }}))])),
        tdm("legacy_c2pa_label", false, &[], json!([{
            "label": "c2pa.training-mining",
            "data": { "entries": {
                "c2pa.ai_training": { "use": "notAllowed" },
                "c2pa.ai_generative_training": { "use": "notAllowed" }
            }}
        }])),
    ]
}

fn recipes() -> Vec<Recipe> {
    let mut all = metadata_recipes();
    all.extend(training_mining_recipes());
    all
}

fn metadata_recipes() -> Vec<Recipe> {
    vec![
        Recipe {
            group: "metadata",
            name: "created",
            identity: false,
            references: &[],
            assertions: json!([metadata(true, spec_image_example())]),
        },
        Recipe {
            group: "metadata",
            name: "outside_c2pa_allowlist",
            identity: false,
            references: &[],
            assertions: json!([metadata(true, outside_allowlist())]),
        },
        Recipe {
            group: "metadata",
            name: "gathered_with_identity",
            identity: true,
            references: &["cawg.metadata"],
            assertions: json!([metadata(false, outside_allowlist())]),
        },
        Recipe {
            group: "metadata",
            name: "gathered_without_identity",
            identity: false,
            references: &[],
            assertions: json!([metadata(false, outside_allowlist())]),
        },
        Recipe {
            group: "metadata",
            name: "media_identifiers",
            identity: true,
            references: &["cawg.metadata"],
            assertions: json!([metadata(false, media_identifiers())]),
        },
        Recipe {
            group: "metadata",
            name: "multiple_instances",
            identity: false,
            references: &[],
            assertions: json!([
                metadata(true, spec_image_example()),
                metadata(true, media_identifiers())
            ]),
        },
        Recipe {
            group: "metadata",
            name: "undefined_prefix",
            identity: false,
            references: &[],
            assertions: json!([metadata(true, json!({
                "@context": { "dc": "http://purl.org/dc/elements/1.1/" },
                "dc:title": "Defined prefix",
                "photoshop:City": "Undefined prefix"
            }))]),
        },
    ]
}

fn settings_for(recipe: &Recipe) -> String {
    let (base, cawg) = SETTINGS
        .split_once("\n[cawg_x509_signer]\n")
        .expect("settings contain a [cawg_x509_signer] section");
    if !recipe.identity {
        return base.to_string();
    }
    let refs = recipe
        .references
        .iter()
        .map(|r| format!("\"{r}\""))
        .collect::<Vec<_>>()
        .join(", ");
    let cawg = cawg.replace(
        "referenced_assertions = [\"cawg.training-mining\"]",
        &format!("referenced_assertions = [{refs}]"),
    );
    format!("{base}\n[cawg_x509_signer]\n{cawg}")
}

fn main() -> ExitCode {
    let Some(out_dir) = std::env::args().nth(1).map(PathBuf::from) else {
        eprintln!("usage: make-assets <assets-dir> [group]");
        return ExitCode::FAILURE;
    };
    let only_group = std::env::args().nth(2);

    let mut failed = false;
    for recipe in recipes() {
        if only_group.as_deref().is_some_and(|g| g != recipe.group) {
            continue;
        }
        let group_dir = out_dir.join(recipe.group);
        fs::create_dir_all(&group_dir).expect("create output dir");
        let dest = group_dir.join(format!("{}.jpg", recipe.name));
        let _ = fs::remove_file(&dest);
        let definition = json!({
            "claim_generator_info": [{ "name": "cawg-test-suite make-assets", "version": "0.1.0" }],
            "title": format!("{}.jpg", recipe.name),
            "assertions": recipe.assertions,
        });
        let result = Context::new()
            .with_settings(settings_for(&recipe).as_str())
            .map(Context::into_shared)
            .and_then(|ctx| Builder::from_shared_context(&ctx).with_definition(definition.to_string()))
            .and_then(|mut builder| builder.save_to_file(SOURCE, &dest));
        match result {
            Ok(_) => println!("wrote {}", dest.display()),
            Err(e) => {
                eprintln!("could not build {}: {e}", recipe.name);
                failed = true;
            }
        }
    }
    if failed {
        ExitCode::FAILURE
    } else {
        ExitCode::SUCCESS
    }
}
