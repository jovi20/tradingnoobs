"""Legacy migration entrypoint.

Schema changes now run only through Alembic. This file remains so old
operator muscle-memory fails loudly instead of silently mutating databases.
"""

import sys


def migrate() -> None:
    raise SystemExit(
        "backend/ops/migrate_db.py is retired. "
        "Use `cd backend && alembic -c alembic.ini upgrade head` instead."
    )


if __name__ == "__main__":
    try:
        migrate()
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        raise
