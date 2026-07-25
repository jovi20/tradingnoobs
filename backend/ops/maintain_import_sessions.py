#!/usr/bin/env python3
"""Expire import previews, clean retained rows, and remove orphan uploads."""
from __future__ import annotations

import argparse
import json

from database import SessionLocal
from services.generic_import_service import (
    cleanup_terminal_import_rows,
    expire_due_import_sessions,
    scavenge_orphan_import_files,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expire-batch-size", type=int, default=100)
    parser.add_argument("--row-batch-size", type=int, default=1000)
    parser.add_argument("--orphan-age-seconds", type=int, default=3600)
    args = parser.parse_args()
    if min(
        args.expire_batch_size,
        args.row_batch_size,
        args.orphan_age_seconds,
    ) <= 0:
        parser.error("batch sizes and orphan age must be positive")

    db = SessionLocal()
    try:
        expired = expire_due_import_sessions(
            db,
            batch_size=args.expire_batch_size,
        )
        rows_deleted = cleanup_terminal_import_rows(
            db,
            batch_size=args.row_batch_size,
        )
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()

    orphans_deleted = scavenge_orphan_import_files(
        older_than_seconds=args.orphan_age_seconds,
    )
    print(
        json.dumps(
            {
                "expired_sessions": expired,
                "normalized_rows_deleted": rows_deleted,
                "orphan_files_deleted": orphans_deleted,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
