#!/usr/bin/env python3
"""Check that public functions and classes in a directory have docstrings.

Usage: python3 bin/check_docstrings.py <directory>

Exits 0 if all public symbols have docstrings, 1 otherwise.
A "public" function or class is one whose name does not start with ``_``.
"""

import ast
import sys
from pathlib import Path


def check_file(path: Path) -> list[str]:
    """Return missing-docstring messages for public functions/classes in path."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return [f"{path}: SyntaxError: {exc}"]

    missing = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name.startswith("_"):
                continue
            if not (node.body and isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, ast.Constant) and
                    isinstance(node.body[0].value.value, str)):
                missing.append(f"{path}:{node.lineno}: {node.name} missing docstring")
    return missing


def main() -> None:
    """Entry point: check all .py files in the given directory."""
    if len(sys.argv) < 2:
        print("Usage: check_docstrings.py <directory>", file=sys.stderr)
        sys.exit(1)

    target = Path(sys.argv[1])
    if not target.exists():
        sys.exit(0)  # no bin/ directory means nothing to check

    this_file = Path(__file__).resolve()
    failures: list[str] = []
    for py_file in sorted(target.rglob("*.py")):
        if py_file.resolve() == this_file:
            continue
        failures.extend(check_file(py_file))

    if failures:
        for line in failures:
            print(line, file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
