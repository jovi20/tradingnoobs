#!/usr/bin/env python3
"""Create privacy-reviewed IBKR Flex fixture candidates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app_config.ibkr_flex_evidence_redaction import (  # noqa: E402
    IbkrEvidenceRedactionError,
    redact_ibkr_flex_statements,
)
from app_config.ibkr_flex_provider_evidence import (  # noqa: E402
    IbkrFlexFieldContract,
)


def _load_contract(path: Path) -> IbkrFlexFieldContract:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "field_contract" in payload:
        payload = payload["field_contract"]
    if not isinstance(payload, dict):
        raise ValueError("Field contract JSON must contain an object")
    return IbkrFlexFieldContract.model_validate(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--field-contract",
        type=Path,
        required=True,
        help="Draft field contract JSON or provider manifest JSON.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="New private directory for redacted fixture candidates.",
    )
    parser.add_argument(
        "statements",
        type=Path,
        nargs="+",
        help="Real Flex XML statements from one frozen query template.",
    )
    args = parser.parse_args()

    try:
        contract = _load_contract(args.field_contract)
        report = redact_ibkr_flex_statements(
            args.statements,
            contract=contract,
            output_dir=args.output_dir,
        )
    except (
        IbkrEvidenceRedactionError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"IBKR evidence redaction failed: {exc}", file=sys.stderr)
        return 1

    print(
        "Wrote "
        f"{report['fixture_count']} redacted fixture candidate(s) to "
        f"{args.output_dir}; human privacy and provider-contract review "
        "remain required."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
