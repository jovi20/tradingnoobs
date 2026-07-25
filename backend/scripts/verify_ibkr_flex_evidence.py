#!/usr/bin/env python3
"""Report whether IBKR Flex provider evidence passes the release gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app_config.ibkr_flex_provider_evidence import (  # noqa: E402
    EVIDENCE_PATH,
    FIXTURE_ROOT,
    IbkrProviderEvidenceError,
    read_provider_evidence_manifest,
    verify_provider_evidence,
)


def build_readiness_report(
    *,
    manifest_path: Path,
    fixture_root: Path,
) -> tuple[dict[str, Any], int]:
    """Build a non-mutating, machine-readable provider evidence report."""
    try:
        manifest = read_provider_evidence_manifest(manifest_path)
    except IbkrProviderEvidenceError as exc:
        return (
            {
                "schema_version": 1,
                "adapter_kind": "IBKR_FLEX_XML_V1",
                "gate_status": "BLOCKED",
                "manifest_status": "INVALID",
                "reasons": list(exc.reasons),
            },
            1,
        )

    common = {
        "schema_version": 1,
        "adapter_kind": manifest.adapter_kind,
        "manifest_status": manifest.status,
        "field_contract_declared": manifest.field_contract is not None,
        "query_template_artifact_declared": bool(
            manifest.query_template_relative_path
            and manifest.query_template_sha256
        ),
        "official_source_count": len(manifest.official_sources),
        "fixture_count": len(manifest.fixtures),
    }
    try:
        verified = verify_provider_evidence(
            manifest,
            fixture_root=fixture_root,
        )
    except IbkrProviderEvidenceError as exc:
        return (
            {
                **common,
                "gate_status": "BLOCKED",
                "reasons": list(exc.reasons),
            },
            1,
        )
    return (
        {
            **common,
            "gate_status": "PASS",
            "query_template_sha256": verified.query_template_sha256,
            "reasons": [],
        },
        0,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=EVIDENCE_PATH,
        help="Provider evidence manifest JSON.",
    )
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=FIXTURE_ROOT,
        help="Root containing query template, official, and fixture artifacts.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Indent the JSON readiness report.",
    )
    args = parser.parse_args(argv)

    report, exit_code = build_readiness_report(
        manifest_path=args.manifest,
        fixture_root=args.fixture_root,
    )
    print(
        json.dumps(
            report,
            ensure_ascii=True,
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
