"""
Backfill legacy positions into the new trading truth tables.
"""
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import SessionLocal
from services.legacy_truth_sync_service import sync_all_legacy_positions_to_truth


def main(argv: list[str]) -> int:
    position_ids = [int(arg) for arg in argv] if argv else None
    db = SessionLocal()
    try:
        summary = sync_all_legacy_positions_to_truth(db, position_ids)
        print("Trading truth backfill summary:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
