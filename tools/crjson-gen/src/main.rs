//! Generate crJSON for every asset under an input directory.
//!
//! Usage: crjson-gen <assets-dir> <out-dir> [settings.toml]
//!
//! Each `<assets-dir>/<sub>/<name>.<ext>` is written to
//! `<out-dir>/<sub>/<name>.crjson.json`. Settings default to the bundled
//! `cawg_test_settings.toml`, which trusts the c2pa-rs test certificate roots.

use std::{
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
};

use c2pa::{Context, Reader};

const DEFAULT_SETTINGS: &str = include_str!("../cawg_test_settings.toml");

fn collect(dir: &Path, out: &mut Vec<PathBuf>) -> std::io::Result<()> {
    for entry in fs::read_dir(dir)? {
        let path = entry?.path();
        if path.is_dir() {
            collect(&path, out)?;
        } else if path.file_name().is_some_and(|n| !n.to_string_lossy().starts_with('.')) {
            out.push(path);
        }
    }
    Ok(())
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 3 {
        eprintln!("usage: {} <assets-dir> <out-dir> [settings.toml]", args[0]);
        return ExitCode::FAILURE;
    }
    let assets = PathBuf::from(&args[1]);
    let out_dir = PathBuf::from(&args[2]);
    let settings = match args.get(3) {
        Some(p) => fs::read_to_string(p).expect("read settings"),
        None => DEFAULT_SETTINGS.to_string(),
    };
    let context = Context::new()
        .with_settings(settings.as_str())
        .expect("valid settings")
        .into_shared();

    let mut files = Vec::new();
    collect(&assets, &mut files).expect("read assets dir");
    files.sort();

    let mut failed = false;
    for file in files {
        let rel = file.strip_prefix(&assets).unwrap();
        let mut target = out_dir.join(rel);
        target.set_extension("crjson.json");

        let result = Reader::from_shared_context(&context)
            .with_file(&file)
            .and_then(|r| r.to_crjson_value());
        match result {
            Ok(value) => {
                fs::create_dir_all(target.parent().unwrap()).unwrap();
                let mut text = serde_json::to_string_pretty(&value).unwrap();
                text.push('\n');
                fs::write(&target, text).unwrap();
                println!("wrote {}", target.display());
            }
            Err(e) => {
                eprintln!("error reading {}: {e}", file.display());
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
