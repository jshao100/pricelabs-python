#!/usr/bin/env python3
"""Check that all public functions and classes in the given directory have docstrings."""

import ast
import sys
from pathlib import Path


def check_file(path: Path) -> list[str]:
    """Return a list of violation messages for public functions/classes missing docstrings.

    Args:
        path: Path to a Python source file.

    Returns:
        List of strings describing each missing-docstring violation.
    """
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [f"{path}: SyntaxError: {exc}"]

    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if node.name.startswith("_"):
            continue
        first = node.body[0] if node.body else None
        has_docstring = isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
        if not has_docstring:
            violations.append(f"{path}:{node.lineno}: '{node.name}' is missing a docstring")
    return violations


def main(directories: list[str]) -> int:
    """Check all Python files in the given directories for missing docstrings.

    Args:
        directories: Paths to directories to scan.

    Returns:
        Exit code: 0 if no violations, 1 otherwise.
    """
    all_violations: list[str] = []
    for dir_path in directories:
        p = Path(dir_path)
        if not p.is_dir():
            continue
        for py_file in sorted(p.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            all_violations.extend(check_file(py_file))

    if all_violations:
        for v in all_violations:
            print(v)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
