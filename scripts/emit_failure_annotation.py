#!/usr/bin/env python3
import os
import re
import sys

def main():
    log_file = "test_results.log"
    if not os.path.exists(log_file):
        print("No test_results.log found.")
        return

    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    lines = content.splitlines()
    error_lines = []
    capture = False
    for line in lines:
        if any(line.startswith(prefix) for prefix in ["FAIL:", "ERROR:"]):
            capture = True
            error_lines.append(line)
        elif capture:
            if line.startswith("---") or line.startswith("===") or line.strip() == "":
                capture = False
            else:
                error_lines.append(line)

    if not error_lines:
        error_lines = [l for l in lines if "AssertionError" in l or "Error" in l or "exceeded" in l]

    summary = " | ".join(error_lines[:20]) if error_lines else "Tests failed with exit code 1"
    # Format for GitHub Actions workflow command
    # Replace newlines with space to keep annotation valid
    summary = summary.replace("\r", " ").replace("\n", " ")
    print(f"::error title=Test Failure Summary::{summary[:1500]}")

if __name__ == "__main__":
    main()
