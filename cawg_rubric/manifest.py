"""Load the core suite manifest, the core test configuration and plugin manifests.

A *project* is something the suite can test:
  - the core suite (`cawg-tests.yml` at the repository root), whose profiles are
    the ones in `cawg_rubric/suite.yml`;
  - a plugin (`cawg-plugin.yml` in the plugin's repository), whose profiles
    extend core profiles.

Plugins may add statements, tighten core statements (warning -> failure) and
add validator cases and subjects. They may never weaken or remove a core
statement, so an asset that passes a plugin profile also passes the CAWG
profiles it extends. check_plugin() enforces this; see docs/plugins.md.
"""

import glob
import json
import os
import re
from dataclasses import dataclass, field

import yaml

from . import __version__

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
SUITE_MANIFEST = os.path.join(PACKAGE_DIR, "suite.yml")
PLUGIN_SCHEMA = os.path.join(PACKAGE_DIR, "schema", "plugin.schema.json")

PLUGIN_FILENAME = "cawg-plugin.yml"
CORE_TESTS_FILENAME = "cawg-tests.yml"

# Namespaces no plugin may use as its statement prefix, besides the core prefixes.
RESERVED_PREFIXES = {"cawg", "c2pa"}

TEST_KEYS = ("validator_cases", "assets_root", "unit_fixtures", "crjson_root",
             "baseline", "rubric_only_assets")


class ManifestError(Exception):
    """A manifest is invalid. `problems` lists every problem found."""

    def __init__(self, path, problems):
        self.path = path
        self.problems = list(problems)
        super().__init__(f"{path}:\n" + "\n".join(f"  - {p}" for p in self.problems))


@dataclass
class Profile:
    id: str
    name: str
    owner: str                      # "cawg" or the plugin name
    composables: list               # absolute paths
    target: str = None              # absolute path of the committed built rubric, if any
    extends: list = field(default_factory=list)    # Profile objects
    overrides: dict = field(default_factory=dict)  # statement ID -> "fail"

    @property
    def qualified_id(self):
        return f"{self.owner}:{self.id}"


@dataclass
class Suite:
    """The core CAWG profiles (cawg_rubric/suite.yml)."""
    statement_prefixes: list
    globals_path: str
    profiles: dict                  # id -> Profile
    subjects: dict                  # name -> regex string


@dataclass
class Project:
    kind: str                       # "core" or "plugin"
    name: str
    version: str
    path: str                       # the manifest file
    root: str                       # directory of the manifest
    profiles: list                  # Profiles this project tests
    subjects: dict                  # name -> regex string (core subjects included)
    tests: dict                     # TEST_KEYS, paths made absolute
    statement_prefix: str = None    # plugins only
    globals_path: str = None        # plugin globals file, if any
    issuer: str = None
    date: str = None
    build_dir: str = None
    requires: str = None
    raw: dict = field(default_factory=dict)
    _cache: dict = field(default_factory=dict, repr=False)

    def subject_patterns(self):
        return {k: re.compile(v) for k, v in self.subjects.items()}

    def case_files(self):
        files = []
        for pattern in self.tests.get("validator_cases") or []:
            files.extend(sorted(glob.glob(pattern)))
        return files


def _load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f) or {}


_SUITE = None


def load_suite():
    """Return the core Suite (cached)."""
    global _SUITE
    if _SUITE is None:
        doc = _load_yaml(SUITE_MANIFEST)
        profiles = {}
        for p in doc["profiles"]:
            profiles[p["id"]] = Profile(
                id=p["id"], name=p["name"], owner=doc["name"],
                composables=[os.path.join(PACKAGE_DIR, c) for c in p["composables"]],
                target=os.path.join(PACKAGE_DIR, p["target"]))
        _SUITE = Suite(
            statement_prefixes=list(doc["statement_prefixes"]),
            globals_path=os.path.join(PACKAGE_DIR, doc["globals"]),
            profiles=profiles,
            subjects=dict(doc["subjects"]))
    return _SUITE


def _resolve_tests(doc, root):
    tests = {}
    for key in TEST_KEYS:
        if key not in doc:
            continue
        value = doc[key]
        if key == "validator_cases":
            value = [os.path.join(root, v) for v in value]
        elif key != "rubric_only_assets":
            value = os.path.join(root, value)
        tests[key] = value
    return tests


def find_manifest(path):
    """Accept a manifest file or a directory containing cawg-plugin.yml / cawg-tests.yml."""
    path = os.path.abspath(path)
    if os.path.isdir(path):
        for name in (PLUGIN_FILENAME, CORE_TESTS_FILENAME):
            candidate = os.path.join(path, name)
            if os.path.exists(candidate):
                return candidate
        raise ManifestError(path, [f"no {PLUGIN_FILENAME} or {CORE_TESTS_FILENAME} in this directory"])
    if not os.path.exists(path):
        raise ManifestError(path, ["file not found"])
    return path


def load_project(path):
    """Load a core test configuration or a plugin manifest. Raises ManifestError."""
    path = find_manifest(path)
    if os.path.basename(path) == CORE_TESTS_FILENAME:
        return load_core_project(path)
    return load_plugin(path)


def load_core_project(path):
    suite = load_suite()
    root = os.path.dirname(os.path.abspath(path))
    doc = _load_yaml(path)
    problems = _schema_problems(doc, "#/$defs/tests")
    if problems:
        raise ManifestError(path, problems)
    return Project(
        kind="core", name="cawg", version=__version__, path=path, root=root,
        profiles=list(suite.profiles.values()), subjects=dict(suite.subjects),
        tests=_resolve_tests(doc, root), raw=doc)


def _schema_problems(doc, ref=None):
    import jsonschema

    with open(PLUGIN_SCHEMA) as f:
        schema = json.load(f)
    if ref:
        schema = {"$ref": ref, **{k: v for k, v in schema.items() if k in ("$schema", "$defs")}}
    validator = jsonschema.Draft202012Validator(schema)
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}"
            for e in sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))]


def load_plugin(path):
    """Load and schema-validate a plugin manifest. Guardrails run in check_plugin()."""
    suite = load_suite()
    root = os.path.dirname(os.path.abspath(path))
    doc = _load_yaml(path)
    problems = _schema_problems(doc)
    if problems:
        raise ManifestError(path, problems)

    profiles = []
    for p in doc["profiles"]:
        extends = []
        for ref in p.get("extends", []):
            owner, _, pid = ref.partition(":")
            if owner != "cawg" or pid not in suite.profiles:
                problems.append(f"profile {p['id']}: extends unknown profile {ref!r} "
                                f"(known: {', '.join('cawg:' + k for k in suite.profiles)})")
                continue
            extends.append(suite.profiles[pid])
        profiles.append(Profile(
            id=p["id"], name=p["name"], owner=doc["name"],
            composables=[os.path.join(root, c) for c in p.get("composables", [])],
            extends=extends, overrides=dict(p.get("overrides") or {})))
    if problems:
        raise ManifestError(path, problems)

    subjects = dict(suite.subjects)
    for name, regex in (doc.get("subjects") or {}).items():
        subjects.setdefault(name, regex)

    return Project(
        kind="plugin", name=doc["name"], version=str(doc["version"]), path=path, root=root,
        profiles=profiles, subjects=subjects, tests=_resolve_tests(doc, root),
        statement_prefix=doc["statement_prefix"],
        globals_path=os.path.join(root, doc["globals"]) if doc.get("globals") else None,
        issuer=doc.get("issuer", doc["name"]), date=doc.get("date"),
        build_dir=os.path.join(root, doc["build_dir"]) if doc.get("build_dir") else None,
        requires=doc["requires"], raw=doc)


def check_requires(requires, version=__version__):
    """Return a problem string if `requires` does not accept this suite version."""
    from packaging.requirements import InvalidRequirement, Requirement

    try:
        req = Requirement(requires)
    except InvalidRequirement as e:
        return f"requires: {e}"
    if req.name != "cawg-test-suite":
        return f"requires: must name cawg-test-suite, not {req.name!r}"
    if not req.specifier.contains(version, prereleases=True):
        return f"requires: {requires!r} does not accept the installed cawg-test-suite {version}"
    return None


def check_plugin(project):
    """Return every guardrail violation in a loaded plugin (empty list = OK).

    Building the plugin's rubrics is part of the check, so problems in
    composables and overrides are found too.
    """
    from . import build

    suite = load_suite()
    problems = []

    problem = check_requires(project.requires)
    if problem:
        problems.append(problem)

    prefix = project.statement_prefix
    if prefix in suite.statement_prefixes or prefix in RESERVED_PREFIXES:
        problems.append(f"statement_prefix: {prefix!r} is reserved for the core suite")

    for name in project.raw.get("subjects") or {}:
        if name in suite.subjects:
            problems.append(f"subjects: {name!r} redefines a core subject")

    ids = [p.id for p in project.profiles]
    for pid in sorted({i for i in ids if ids.count(i) > 1}):
        problems.append(f"profiles: duplicate profile id {pid!r}")

    if project.globals_path:
        core = build.load_globals(suite.globals_path)
        try:
            mine = build.load_globals(project.globals_path)
        except (OSError, yaml.YAMLError) as e:
            problems.append(f"globals: {e}")
            mine = {"variables": {}, "expressions": {}}
        if os.path.exists(project.globals_path) and _load_yaml(project.globals_path).get("include"):
            problems.append("globals: include is not supported; the core globals are always available")
        for kind in ("variables", "expressions"):
            for name in sorted(set(mine[kind]) & set(core[kind])):
                problems.append(f"globals: {name!r} redefines a core {kind[:-1]}; use a plugin-specific name")

    for profile in project.profiles:
        problems.extend(build.profile_problems(project, profile))
    return problems
