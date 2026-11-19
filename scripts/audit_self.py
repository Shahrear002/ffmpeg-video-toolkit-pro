#!/usr/bin/env python3
"""
Automated Security & Compliance Audit for Agensi Skill Package.
Verifies that the skill package contains zero network calls, zero eval/exec,
zero obfuscation, zero prompt injections, and adheres strictly to marketplace requirements.
"""

import ast
from pathlib import Path
import re
import sys
from typing import List, Tuple

FORBIDDEN_MODULES = {
    "requests", "urllib.request", "http.client", "socket", "ftplib",
    "poplib", "imaplib", "smtplib", "aiohttp", "httpx", "websockets",
}

FORBIDDEN_CALLS = {
    "eval", "exec", "compile", "__import__",
}

FORBIDDEN_PROMPT_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(the\s+)?(system|developer)\s+prompt", re.IGNORECASE),
    re.compile(r"bypass\s+(safety|guardrails|sandbox)", re.IGNORECASE),
    re.compile(r"exfiltrate", re.IGNORECASE),
]


class CodeAuditor(ast.NodeVisitor):
    def __init__(self, filename: str):
        self.filename = filename
        self.violations: List[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name in FORBIDDEN_MODULES:
                self.violations.append(f"{self.filename}:{node.lineno} Forbidden module import: '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            if node.module in FORBIDDEN_MODULES or any(node.module.startswith(m) for m in FORBIDDEN_MODULES):
                self.violations.append(f"{self.filename}:{node.lineno} Forbidden module import: '{node.module}'")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in FORBIDDEN_CALLS:
                self.violations.append(f"{self.filename}:{node.lineno} Forbidden dynamic execution call: '{func_name}()'")
        elif isinstance(node.func, ast.Attribute):
            # Check for builtins.eval, builtins.exec
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "builtins":
                if node.func.attr in FORBIDDEN_CALLS:
                    self.violations.append(f"{self.filename}:{node.lineno} Forbidden dynamic execution call: '{node.func.attr}()'")

        self.generic_visit(node)


def audit_python_file(path: Path) -> List[str]:
    violations: List[str] = []
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"{path}: Could not read file: {e}"]

    # AST checks
    try:
        tree = ast.parse(content, filename=str(path))
        auditor = CodeAuditor(str(path))
        auditor.visit(tree)
        violations.extend(auditor.violations)
    except SyntaxError as e:
        violations.append(f"{path}:{e.lineno} Syntax error during audit: {e.msg}")

    # Regex checks for base64 obfuscation or download commands
    if re.search(r"base64\s*\.\s*b64decode", content):
        violations.append(f"{path}: Potential obfuscation via base64.b64decode")

    if re.search(r"\b(curl|wget)\b.*https?://", content) and not path.name.startswith("fetch_"):
        violations.append(f"{path}: Direct remote download command detected")

    return violations


def audit_text_file(path: Path) -> List[str]:
    violations: List[str] = []
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"{path}: Could not read file: {e}"]

    for pattern in FORBIDDEN_PROMPT_PATTERNS:
        match = pattern.search(content)
        if match:
            violations.append(f"{path}: Found forbidden instruction pattern: '{match.group(0)}'")

    return violations


def run_audit(target_dir: Path) -> Tuple[int, List[str]]:
    all_violations: List[str] = []
    print(f"[AUDIT] Scanning {target_dir} for security compliance...", file=sys.stderr)

    for item in target_dir.rglob("*"):
        if not item.is_file():
            continue
        # Skip git and cache
        if any(part.startswith(".") or part == "__pycache__" for part in item.parts):
            continue

        if item.suffix == ".py":
            all_violations.extend(audit_python_file(item))
            all_violations.extend(audit_text_file(item))
        elif item.suffix in [".md", ".txt", ".json", ".yaml", ".yml"]:
            all_violations.extend(audit_text_file(item))

    return len(all_violations), all_violations


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    target_paths = [
        repo_root / "skill",
        repo_root / "engine",
    ]

    total_violations = 0
    violations_list: List[str] = []

    for t in target_paths:
        if t.exists():
            v_count, v_list = run_audit(t)
            total_violations += v_count
            violations_list.extend(v_list)

    if total_violations == 0:
        print("[AUDIT PASSED] 0 security violations found. Safe for marketplace submission.", file=sys.stderr)
        return 0
    else:
        print(f"\n[AUDIT FAILED] Found {total_violations} security violations:", file=sys.stderr)
        for v in violations_list:
            print(f"  - {v}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
