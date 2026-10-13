"""cawg-suite: build and evaluate CAWG rubrics, check validators, and work with plugins.

    cawg-suite list [--plugin P]                      profiles and their statements
    cawg-suite build [--plugin P] [--out DIR]         build the core or a plugin's rubrics
    cawg-suite evaluate PROFILE|RUBRIC CRJSON [--plugin P]
    cawg-suite check-validator CRJSON_DIR [--project P] [--baseline B] [--json]
    cawg-suite lint-plugin P                          check a plugin's guardrails

PROFILE is a core profile (identity-1.3 or cawg:identity-1.3) or, with --plugin,
one of the plugin's profiles. P is a cawg-plugin.yml or its directory.
"""

import argparse
import json
import os
import sys

from . import __version__, build, validator
from .evaluator import evaluate, evaluate_rubric
from .manifest import ManifestError, check_plugin, load_project, load_suite


def _plugin(path):
    project = load_project(path)
    if project.kind != "plugin":
        raise ManifestError(project.path, ["not a plugin manifest (cawg-plugin.yml)"])
    return project


def _find_profile(name, project=None):
    owner, _, pid = name.rpartition(":")
    if project is not None and owner in ("", project.name):
        for p in project.profiles:
            if p.id == pid:
                return p, project
    if owner in ("", "cawg") and pid in load_suite().profiles:
        return load_suite().profiles[pid], None
    known = [f"cawg:{k}" for k in load_suite().profiles]
    if project is not None:
        known += [p.qualified_id for p in project.profiles]
    raise SystemExit(f"unknown profile {name!r} (known: {', '.join(known)})")


def cmd_list(args):
    project = _plugin(args.plugin) if args.plugin else None
    profiles = [(p, None) for p in load_suite().profiles.values()]
    if project:
        profiles += [(p, project) for p in project.profiles]
    for profile, owner in profiles:
        _, statements = build.assemble(profile, owner)
        extends = f" extends {', '.join(p.qualified_id for p in profile.extends)}" if profile.extends else ""
        print(f"{profile.qualified_id}: {profile.name}{extends}")
        for s in statements:
            severity = "fail" if s.get("failIfMatched") else "warn" if s.get("warnIfMatched") else "bool"
            mark = " (tightened)" if s["id"] in profile.overrides else ""
            print(f"  [{severity}] {s['id']}{mark}")
    return 0


def cmd_build(args):
    if not args.plugin:
        build.build_core()
        from .validate_rubric import validate_text
        failed = False
        for profile in load_suite().profiles.values():
            for problem in validate_text(build.rendered(None, profile), profile.id):
                print(f"{profile.id}: {problem}", file=sys.stderr)
                failed = True
        return 1 if failed else 0
    build.build_plugin(args.plugin, args.out)
    return 0


def cmd_evaluate(args):
    with open(args.crjson) as f:
        data = json.load(f)
    if os.path.isfile(args.profile):
        report = evaluate(args.profile, data, debug=args.debug)
    else:
        project = _plugin(args.plugin) if args.plugin else None
        profile, owner = _find_profile(args.profile, project)
        metadata, statements = build.assemble(profile, owner)
        report = evaluate_rubric(metadata, statements, data, debug=args.debug)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if any(report["false"].values()) else 0


def cmd_lint(args):
    project = _plugin(args.plugin)
    problems = check_plugin(project)
    for p in problems:
        print(f"  - {p}", file=sys.stderr)
    if problems:
        print(f"{project.path}: {len(problems)} problem(s)", file=sys.stderr)
        return 1
    print(f"{project.name} {project.version}: OK ({len(project.profiles)} profile(s))")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="cawg-suite", description=__doc__.split("\n")[0])
    parser.add_argument("--version", action="version", version=f"cawg-test-suite {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="List profiles and their statements")
    p.add_argument("--plugin")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("build", help="Build the core rubrics, or a plugin's rubrics")
    p.add_argument("--plugin")
    p.add_argument("--out", help="Output directory for plugin rubrics (default: the plugin's build_dir)")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("evaluate", help="Evaluate crJSON against a profile or a built rubric")
    p.add_argument("profile", help="Profile ID (e.g. identity-1.3) or path to a built rubric")
    p.add_argument("crjson")
    p.add_argument("--plugin")
    p.add_argument("--debug", action="store_true")
    p.set_defaults(func=cmd_evaluate)

    p = sub.add_parser("check-validator", help="Check a validator's crJSON against validator cases")
    validator.add_arguments(p)
    p.set_defaults(func=lambda a: validator.run_cli(a))

    p = sub.add_parser("lint-plugin", help="Check a plugin manifest against the guardrails")
    p.add_argument("plugin")
    p.set_defaults(func=cmd_lint)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ManifestError as e:
        print(e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
