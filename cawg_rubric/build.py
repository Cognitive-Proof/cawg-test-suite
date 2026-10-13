"""Assemble composable statement files into built CAWG rubrics.

Adapted from the C2PA Conformance Task Force rubric builder
(https://github.com/c2pa-org/conformance-public,
asset-rubrics/build_conformance_rubrics.py at commit f22ce0a), used under
CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Spec-version variable
injection was removed; globals loading, used-globals filtering and ID-based
deduplication are unchanged. See NOTICE.

Usage: python -m cawg_rubric.build
"""

import copy
import os
import re
import sys

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUBRICS_DIR = os.path.join(REPO_ROOT, "rubrics")
COMPOSABLES_DIR = os.path.join(RUBRICS_DIR, "composables")

RECIPES = [
    {
        "target": "cawg-identity-1.3.rubric.yml",
        "name": "CAWG Identity Assertion 1.3 Rubric",
        "files": [
            "identity-1.3-structure.yml",
            "identity-1.3-x509.yml",
            "identity-1.3-ica.yml",
            "identity-1.3-validation.yml",
        ],
    },
    {
        "target": "cawg-metadata-1.1.rubric.yml",
        "name": "CAWG Metadata Assertion 1.1 Rubric (with 1.2-draft recommendations)",
        "files": [
            "metadata-1.1.yml",
            "metadata-1.2-draft.yml",
        ],
    },
    {
        "target": "cawg-training-mining-1.1.rubric.yml",
        "name": "CAWG Training and Data Mining Assertion 1.1 Rubric",
        "files": [
            "training-mining-1.1.yml",
        ],
    },
]


# Custom representer to preserve literal block style for long or multiline strings (expressions)
def str_presenter(dumper, data):
    if len(data.splitlines()) > 1 or len(data) > 80:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


yaml.add_representer(str, str_presenter)


def load_globals(filepath, _visited=None):
    """Load variables and expressions from a globals file, recursively following include: lists."""
    if _visited is None:
        _visited = set()
    filepath = os.path.abspath(filepath)
    if filepath in _visited:
        return {'variables': {}, 'expressions': {}}
    _visited.add(filepath)

    with open(filepath, 'r') as f:
        doc = yaml.safe_load(f)

    result = {
        'variables':   dict(doc.get('variables',   {}) or {}),
        'expressions': dict(doc.get('expressions', {}) or {}),
    }

    base_dir = os.path.dirname(filepath)
    for name in (doc.get('include') or []):
        included = load_globals(os.path.join(base_dir, name), _visited)
        # Included file provides the base; current file's keys win on conflict.
        result['variables']   = {**included['variables'],   **result['variables']}
        result['expressions'] = {**included['expressions'], **result['expressions']}

    return result


def filter_used_globals(statements, all_globals):
    """
    Scan statement expressions and return only the variables/expressions
    that are actually referenced, following transitive expression dependencies.
    """
    used_vars = set()
    used_exprs = set()
    for stmt in statements:
        if not isinstance(stmt, dict):
            continue
        expr = stmt.get('expression', '')
        if not isinstance(expr, str):
            continue
        used_vars.update(re.findall(r'\$[A-Za-z_]\w*', expr))
        used_exprs.update(re.findall(r'_[A-Za-z_]\w*(?=\()', expr))

    # Transitively include expressions called by already-included expressions.
    frontier = set(used_exprs)
    while frontier:
        next_frontier = set()
        for name in frontier:
            body = all_globals['expressions'].get(name, '')
            if not isinstance(body, str):
                continue
            used_vars.update(re.findall(r'\$[A-Za-z_]\w*', body))
            for dep in re.findall(r'_[A-Za-z_]\w*(?=\()', body):
                if dep not in used_exprs:
                    next_frontier.add(dep)
            used_exprs.update(re.findall(r'_[A-Za-z_]\w*(?=\()', body))
        frontier = next_frontier

    variables   = {k: v for k, v in all_globals['variables'].items()   if k in used_vars}
    expressions = {k: v for k, v in all_globals['expressions'].items() if k in used_exprs}
    return variables, expressions


def load_component_file(filename):
    print(f"  Loading {filename} ...")
    with open(os.path.join(COMPOSABLES_DIR, filename), 'r') as f:
        statements = []
        for d in yaml.safe_load_all(f):
            if isinstance(d, list):
                statements.extend(d)
            elif isinstance(d, dict) and "id" in d:
                statements.append(d)
        return statements


def get_version():
    with open(os.path.join(RUBRICS_DIR, 'VERSION'), 'r') as f:
        return f.read().strip()


def assemble_rubric(target_filename, name, version, files, all_globals):
    print(f"Generating Rubric: {target_filename}")

    statements_map = {}
    for f in files:
        for s in load_component_file(f):
            if isinstance(s, dict) and "id" in s:
                # Later files override earlier files (deduplication by ID).
                statements_map[s["id"]] = s
    all_statements = list(statements_map.values())

    variables, expressions = filter_used_globals(all_statements, copy.deepcopy(all_globals))

    metadata = {
        "rubric_metadata": {
            "name": name,
            "issuer": "CAWG Test Suite",
            "date": "2026-10-10T00:00:00Z",
            "version": version,
            "language": "en",
        }
    }
    if variables:
        metadata["variables"] = variables
    if expressions:
        metadata["expressions"] = expressions

    with open(os.path.join(RUBRICS_DIR, target_filename), 'w', encoding='utf-8') as f:
        f.write("# GENERATED by `python -m cawg_rubric.build` - edit rubrics/composables/ instead.\n")
        yaml.dump(metadata, f, sort_keys=False, width=1000, allow_unicode=True)
        f.write("\n---\n\n")
        yaml.dump(all_statements, f, sort_keys=False, width=1000, allow_unicode=True)
    print(f"  Wrote rubrics/{target_filename} ({len(all_statements)} statements)\n")


def main():
    all_globals = load_globals(os.path.join(COMPOSABLES_DIR, 'globals.yml'))
    version = get_version()
    for r in RECIPES:
        assemble_rubric(r["target"], r["name"], version, r["files"], all_globals)
    return 0


if __name__ == "__main__":
    sys.exit(main())
