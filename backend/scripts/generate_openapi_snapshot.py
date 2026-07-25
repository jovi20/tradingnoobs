#!/usr/bin/env python3
"""Generate or verify the JOURNAL_BASELINE OpenAPI snapshot."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
SNAPSHOT_PATH = BACKEND_ROOT / "openapi" / "journal-baseline.openapi.json"


def _load_schema() -> dict:
    os.environ["RELEASE_PROFILE"] = "JOURNAL_BASELINE"
    os.environ["DEPLOYMENT_CAPABILITY_ALLOWLIST"] = ""
    os.environ["AUTO_CREATE_SCHEMA"] = "false"
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))

    from main import create_app

    return create_app("JOURNAL_BASELINE").openapi()


def _render_schema() -> str:
    return json.dumps(
        _load_schema(),
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail instead of writing when the checked-in snapshot differs.",
    )
    args = parser.parse_args()

    rendered = _render_schema()
    if args.check:
        if not SNAPSHOT_PATH.exists():
            print(f"OpenAPI snapshot is missing: {SNAPSHOT_PATH}", file=sys.stderr)
            return 1
        if SNAPSHOT_PATH.read_text(encoding="utf-8") != rendered:
            print(
                "JOURNAL_BASELINE OpenAPI snapshot is stale; run "
                f"{sys.executable} {Path(__file__).relative_to(REPO_ROOT)}",
                file=sys.stderr,
            )
            return 1
        print(f"OpenAPI snapshot is current: {SNAPSHOT_PATH.relative_to(REPO_ROOT)}")
        return 0

    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(rendered, encoding="utf-8")
    print(f"Wrote {SNAPSHOT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
