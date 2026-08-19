import ast
import re
from pathlib import Path


def test_every_named_function_has_a_human_oriented_contract() -> None:
    """Verify the user-required documentation contract for every named function.

    Inputs:
        None; scans production Python source beneath the repository package.
    Functionality:
        Requires each named function to document inputs, achieved functionality, outputs,
        failures, and callback behavior whenever it accepts a callback-like argument.
    Outputs:
        None; the test passes when every function has a complete readable contract.
    Failures:
        Fails with file, line, function, and missing sections for incomplete documentation.
    """
    source_root = Path(__file__).parents[1] / "src" / "ai_learning_audiobook"
    required_sections = {"Inputs:", "Functionality:", "Outputs:", "Failures:"}
    failures: list[str] = []

    for source_path in sorted(source_root.glob("*.py")):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            docstring = ast.get_docstring(node) or ""
            missing = sorted(section for section in required_sections if section not in docstring)
            argument_names = {argument.arg for argument in (*node.args.args, *node.args.kwonlyargs)}
            if {"callback", "call_next"} & argument_names and "Callback contract:" not in docstring:
                missing.append("Callback contract:")
            if missing:
                relative = source_path.relative_to(source_root.parent)
                failures.append(
                    f"{relative}:{node.lineno} {node.name} missing {', '.join(missing)}"
                )

    browser_source = (source_root / "web.py").read_text(encoding="utf-8")
    for match in re.finditer(r"(?:async\s+)?function\s+(\w+)\s*\(", browser_source):
        documentation = browser_source[max(0, match.start() - 500) : match.start()]
        missing = sorted(section for section in required_sections if section not in documentation)
        if missing:
            failures.append(f"web.py {match.group(1)} missing {', '.join(missing)}")

    assert failures == []
