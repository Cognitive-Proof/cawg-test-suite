"""CAWG rubric evaluator.

Evaluates a built rubric (YAML + json-formula) against crJSON and returns a
report grouped by outcome (true / false / warning) and statement category.

Adapted from the C2PA Conformance Task Force asset-rubric evaluator
(c2pa-org/conformance, asset-rubrics/c2pa_conformance_rubric_evaluator.py at
commit b6d5a1b). The json-formula engine setup is unchanged; the C2PA-specific
provenance DAG, signal pruning and spec-version handling were removed.
"""

import argparse
import json
import re
import sys

import yaml
from json_formula import JsonFormula
from json_formula.data_types import TYPE_ANY


def get_sort_priority(val):
    if val == "true" or val is True:
        return 0
    if val == "warn":
        return 1
    return 2  # "false", False, or None


def _infer_arities(expressions):
    """Infer the arity of each named expression from call sites and from $args body references.

    Two complementary passes:
    1. Call-site scanning: scans every expression body for calls like `name(a, b)` and
       records the maximum argument count seen.
    2. Body reference scanning: if an expression body uses $args[N], it must accept at least
       N+1 args ($args[0]=arg0, $args[1]=arg1, ..., $args[N]=argN).  Handles expressions that
       are only called from statement expressions outside the expressions dict.
    """
    arities = {name: 0 for name in expressions}

    for func_name in expressions:
        escaped = re.escape(func_name)
        call_pattern = re.compile(r'\b' + escaped + r'\s*\(')
        for expr_val in expressions.values():
            expr_str = str(expr_val) if expr_val is not None else ''
            for match in call_pattern.finditer(expr_str):
                rest = expr_str[match.end():]
                if rest.startswith(')'):
                    count = 0
                else:
                    depth = 1
                    count = 1
                    for c in rest:
                        if c == '(':
                            depth += 1
                        elif c == ')':
                            depth -= 1
                            if depth == 0:
                                break
                        elif c == ',' and depth == 1:
                            count += 1
                arities[func_name] = max(arities[func_name], count)

    for name, expr_val in expressions.items():
        expr_str = str(expr_val) if expr_val is not None else ''
        # $args[0] is the first positional arg, $args[1] the second, etc.
        # So if the body references $args[N], the expression needs at least N+1 args
        # (arg 0 becomes @; arg 1 → $args[0]; … arg N+1 → $args[N]).
        max_idx = max((int(i) for i in re.findall(r'\$args\[(\d+)\]', expr_str)), default=-1)
        if max_idx >= 0:
            arities[name] = max(arities[name], max_idx + 1)
        elif re.search(r'\$args\b', expr_str):
            arities[name] = max(arities[name], 1)

    return arities


def create_json_formula_engine(metadata, debug=False):
    """Create a JsonFormula engine with variables and named expressions from rubric metadata.

    Named expressions (_exprName) are registered as custom functions using the following
    argument-passing convention:

      - All positional args → injected as a single array global `$args` before evaluation,
        so $args[0] is the first arg, $args[1] is the second arg, etc.
      - `@` (data context) inside the body is the call-site's ambient data — unchanged.

    Zero-argument expressions evaluate with the call-site's `@` unchanged.

    Arity is inferred automatically via two passes (see _infer_arities):
      1. Call-site scanning across all expression bodies — finds calls like `_foo(a, b)`.
      2. Body scanning — if an expression body references `$args[N]`, it needs at least N+1 args.

    The `$args` array global is the correct way to pass values into an expression.
    `$args` is a global and is NOT shadowed by filter projections `[?...]`, so
    `$args[0]`, `$args[1]`, etc. remain readable at any nesting depth.  Inside
    `[?condition]`, `@` is rebound to the current array element; use `$args[N]` to
    reference call arguments.  See `_startsWithAny` and `_manifest_createdWithDst`
    for examples.
    """
    variables = dict(metadata.get('variables') or {})
    expressions = dict(metadata.get('expressions') or {})

    debug_list = []

    # Infer arity of each expression from call sites in all other expression bodies.
    expr_arities = _infer_arities(expressions)

    # Automatically detect all global variables (any identifier starting with '$') across expression bodies
    dollar_vars = set(variables.keys())
    for expr_val in expressions.values():
        if expr_val is not None:
            dollar_vars.update(re.findall(r'\$[a-zA-Z0-9_]+', str(expr_val)))

    # Compile all expression ASTs (parsing only — no runtime needed at this stage).
    compile_helper = JsonFormula(debug=[])
    allowed_names = list(dollar_vars) + list(expressions.keys())


    compiled_asts = {}
    for name, expr_val in expressions.items():
        expr_str = str(expr_val).strip() if expr_val is not None else ''
        try:
            compiled_asts[name] = compile_helper.compile(expr_str, allowed_names)
        except Exception as e:
            if debug:
                print(f"Warning: Failed to compile expression '{name}': {e}", file=sys.stderr)
            compiled_asts[name] = None

    def make_expr_fn(ast, name, arity):
        if arity == 0:
            def fn(args, data, interpreter):
                if ast is None:
                    raise Exception(f"Expression '{name}' failed to compile")
                return interpreter.search(ast, data)
            return fn
        else:
            # All args become $args array; @ (data context) is the call-site ambient data.
            def fn(args, data, interpreter):
                if ast is None:
                    raise Exception(f"Expression '{name}' failed to compile")
                ctx = data
                extra = list(args)
                saved = interpreter.globals.get('$args')
                interpreter.globals['$args'] = extra
                try:
                    return interpreter.search(ast, ctx)
                finally:
                    if saved is None:
                        interpreter.globals.pop('$args', None)
                    else:
                        interpreter.globals['$args'] = saved
            return fn

    def make_signature(arity):
        if arity == 0:
            return []
        return [{'types': [TYPE_ANY]} for _ in range(arity)]

    custom_functions = {
        name: {
            'func': make_expr_fn(compiled_asts[name], name, expr_arities[name]),
            'signature': make_signature(expr_arities[name]),
        }
        for name in compiled_asts
    }

    engine = JsonFormula(debug=debug_list, custom_functions=custom_functions)
    return engine, variables


def load_rubric(rubric_path):
    """Return (metadata, statements) from a multi-document rubric YAML file."""
    with open(rubric_path, 'r') as f:
        docs = list(yaml.safe_load_all(f))
    if not docs:
        raise ValueError(f"Empty rubric file: {rubric_path}")
    metadata = docs[0] if isinstance(docs[0], dict) else {}
    statements = []
    for doc in docs[1:]:
        if isinstance(doc, list):
            statements.extend(doc)
        elif isinstance(doc, dict) and "block" not in doc:
            statements.append(doc)
    if not statements:
        raise ValueError(f"No statements found in rubric: {rubric_path}")
    return metadata, statements


def _state_for(val, fail_if_matched, warn_if_matched):
    """Map an expression result to (state, matches)."""
    if fail_if_matched or warn_if_matched:
        if isinstance(val, list) and len(val) > 0:
            return ("false" if fail_if_matched else "warn"), val
        return "true", []
    if isinstance(val, list):
        return ("true" if len(val) > 0 else "false"), []
    if isinstance(val, bool):
        return ("true" if val else "false"), []
    if isinstance(val, (int, float)):
        return ("true" if val > 0 else "false"), []
    return ("true" if val is not None else "false"), []


def _report_text(report_text_dict, state, matches):
    key = state
    if key == "warn" and "warn" not in report_text_dict:
        key = "false"
    val_obj = report_text_dict.get(key, report_text_dict.get("default", ""))
    text = val_obj.get("en", "") if isinstance(val_obj, dict) else str(val_obj)
    if matches:
        text = text.replace("{{matches}}", ", ".join(
            m if isinstance(m, str) else json.dumps(m, ensure_ascii=False) for m in matches))
    return text


def evaluate(rubric_path, data, debug=False):
    """Evaluate crJSON `data` (a dict) against the rubric and return the report dict."""
    metadata, statements = load_rubric(rubric_path)
    engine, variables = create_json_formula_engine(metadata, debug=debug)

    results = []
    for stmt in statements:
        if not isinstance(stmt, dict) or not stmt.get("expression"):
            continue
        stmt_id = stmt.get("id") or "general:unnamed"
        category, trait = stmt_id.split(":", 1) if ":" in stmt_id else ("general", stmt_id)
        entry = {"trait": trait, "specSection": stmt.get("specSection")}
        try:
            val = engine.search(stmt["expression"].strip(), data, globals=variables)
            state, matches = _state_for(val, stmt.get("failIfMatched", False),
                                        stmt.get("warnIfMatched", False))
            entry["reportText"] = _report_text(stmt.get("reportText", {}), state, matches)
            if matches:
                entry["matches"] = matches
        except Exception as e:  # report expression errors rather than abort the run
            if debug:
                import traceback
                traceback.print_exc()
            state = None
            entry["reportText"] = f"Error: {e}"
        if entry["specSection"] is None:
            entry.pop("specSection")
        results.append((category, state, entry))

    results.sort(key=lambda r: (get_sort_priority(r[1]), r[2]["trait"]))
    categories = sorted({c for c, _, _ in results}) or ["general"]
    report = {
        "rubricName": metadata.get("rubric_metadata", {}).get("name", "Unknown"),
        "rubricVersion": metadata.get("rubric_metadata", {}).get("version", "Unknown"),
        "true": {c: [] for c in categories},
        "false": {c: [] for c in categories},
        "warning": {c: [] for c in categories},
    }
    for category, state, entry in results:
        outcome = {"true": "true", "warn": "warning"}.get(state, "false")
        report[outcome][category].append(entry)
    return report


def outcome_of(report, trait, category="identity"):
    """Return 'true', 'false', 'warning' or None for a trait in a report."""
    for outcome in ("true", "false", "warning"):
        if any(r["trait"] == trait for r in report[outcome].get(category, [])):
            return outcome
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate crJSON against a CAWG rubric")
    parser.add_argument("rubric", help="Path to the built rubric YAML file")
    parser.add_argument("crjson", help="Path to the crJSON file")
    parser.add_argument("--debug", action="store_true", help="Print expression errors")
    args = parser.parse_args(argv)
    with open(args.crjson) as f:
        data = json.load(f)
    report = evaluate(args.rubric, data, debug=args.debug)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if any(report["false"].values()) else 0


if __name__ == "__main__":
    sys.exit(main())
