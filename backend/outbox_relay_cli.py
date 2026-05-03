"""
Trading Noobs Backend - Outbox Relay CLI
"""
from __future__ import annotations

import argparse

from database import SessionLocal
from services.outbox_service import relay_pending_outbox_events


def relay_once(*, session_factory=SessionLocal, limit: int = 100) -> int:
    db = session_factory()
    try:
        relayed = relay_pending_outbox_events(db, limit=limit)
        db.commit()
        return relayed
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Relay pending transactional outbox events into queued job runs.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of pending outbox rows to relay.")
    args = parser.parse_args(argv)

    relayed = relay_once(limit=args.limit)
    print(f"relayed {relayed} outbox events")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
