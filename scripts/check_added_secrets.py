#!/usr/bin/env python3
"""Fail when added Git diff lines match frozen credential patterns."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


RULESET_VERSION = "added-secrets-v1"
RULES = (
    (
        "PRIVATE_KEY_PEM",
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        0,
    ),
    (
        "CREDENTIALED_URL",
        r"https?://[^\s/:@]+:[^\s/@]+@",
        re.IGNORECASE,
    ),
    (
        "KNOWN_PROVIDER_TOKEN",
        r"(?:AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}|sk-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|sk_live_[A-Za-z0-9]{16,})",
        0,
    ),
    (
        "LITERAL_BEARER_OR_JWT",
        r"(?:Bearer\s+[A-Za-z0-9._~+/-]{20,}={0,2}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,})",
        re.IGNORECASE,
    ),
    (
        "LONG_SENSITIVE_ASSIGNMENT",
        r"\b(?:api[_-]?key|api[_-]?secret|access[_-]?token|auth[_-]?token|password|passwd|private[_-]?key|secret)\b\s*[:=]\s*[\"'][A-Za-z0-9+/=_-]{20,}[\"']",
        re.IGNORECASE,
    ),
)
COMPILED_RULES = tuple((name, re.compile(pattern, flags)) for name, pattern, flags in RULES)
RULESET_SHA256 = hashlib.sha256(
    json.dumps(RULES, separators=(",", ":")).encode("utf-8")
).hexdigest()
HUNK_PATTERN = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str


def run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "git command failed"
        raise RuntimeError(message)
    return completed.stdout


def resolve_repo() -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError("not inside a Git repository")
    return Path(completed.stdout.strip())


def scan_diff(diff: str) -> tuple[int, list[Finding]]:
    current_path = "<unknown>"
    target_line = 0
    added_lines = 0
    findings: list[Finding] = []

    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_path = line[6:]
            continue
        hunk_match = HUNK_PATTERN.match(line)
        if hunk_match:
            target_line = int(hunk_match.group(1))
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added_lines += 1
            content = line[1:]
            for rule_name, rule in COMPILED_RULES:
                if rule.search(content):
                    findings.append(Finding(current_path, target_line, rule_name))
            target_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            continue
        elif not line.startswith("\\"):
            target_line += 1

    return added_lines, findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="Base commit SHA")
    parser.add_argument("--head", required=True, help="Checkpoint commit SHA")
    args = parser.parse_args()

    try:
        repo = resolve_repo()
        base = run_git(repo, "rev-parse", "--verify", f"{args.base}^{{commit}}").strip()
        head = run_git(repo, "rev-parse", "--verify", f"{args.head}^{{commit}}").strip()
        diff = run_git(
            repo,
            "diff",
            "--no-ext-diff",
            "--unified=0",
            "--diff-filter=ACMR",
            base,
            head,
            "--",
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    added_lines, findings = scan_diff(diff)
    summary = (
        f"ruleset={RULESET_VERSION} ruleset_sha256={RULESET_SHA256} "
        f"base={base} head={head} added_lines={added_lines}"
    )
    if findings:
        print(f"FAIL {summary}")
        for finding in findings:
            print(f"{finding.path}:{finding.line} rule={finding.rule}")
        return 1

    print(f"PASS {summary} findings=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
