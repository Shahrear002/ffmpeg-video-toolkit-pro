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
    failures = []
    current_block = []
    in_block = False
    for line in lines:
        if line.startswith("FAIL:") or line.startswith("ERROR:"):
            if current_block:
                failures.append("\n".join(current_block))
            current_block = [line]
            in_block = True
        elif in_block:
            if line.startswith("===") or line.startswith("FAILED ("):
                in_block = False
                failures.append("\n".join(current_block))
                current_block = []
            elif not line.startswith("---"):
                current_block.append(line)
    if current_block:
        failures.append("\n".join(current_block))

    for fail in failures:
        msg = fail.replace("\r", " ").replace("\n", " -> ")
        print(f"::error title=Test Failure::{msg[:1500]}")

if __name__ == "__main__":
    main()
