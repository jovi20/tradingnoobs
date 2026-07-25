"""Preview JRN-006 ledger divergence without mutating by default."""
from __future__ import annotations

import argparse
import json

from database import SessionLocal
from models import TradingAccount
from services.account_reconciliation_service import (
    preview_account_reconciliation,
    preview_all_account_reconciliation,
    refresh_accounting_health,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-public-id")
    parser.add_argument(
        "--apply-health",
        action="store_true",
        help="Persist only the health state implied by the invariant preview.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.account_public_id:
            account = db.query(TradingAccount).filter(
                TradingAccount.public_id == args.account_public_id,
            ).one()
            previews = [
                refresh_accounting_health(
                    db,
                    account=account,
                    apply=args.apply_health,
                )
                if args.apply_health
                else preview_account_reconciliation(db, account=account)
            ]
        else:
            previews = preview_all_account_reconciliation(db)
            if args.apply_health:
                previews = [
                    refresh_accounting_health(
                        db,
                        account=db.query(TradingAccount).filter(
                            TradingAccount.public_id == preview.account_public_id,
                        ).one(),
                        apply=True,
                    )
                    for preview in previews
                ]

        if args.apply_health:
            db.commit()
        else:
            db.rollback()
        print(json.dumps(
            {
                "mode": "APPLY_HEALTH" if args.apply_health else "PREVIEW",
                "accounts": [preview.to_dict() for preview in previews],
            },
            indent=2,
            sort_keys=True,
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
