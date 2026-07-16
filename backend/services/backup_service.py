from datetime import datetime, timezone
from pathlib import Path
import shutil

from sqlalchemy.engine import make_url


class BackupProviderNotConfigured(Exception):
    pass


def detect_database_backend(database_url: str) -> str:
    driver = make_url(database_url).drivername.lower()
    if driver.startswith("sqlite"):
        return "sqlite"
    if driver.startswith("postgresql") or driver.startswith("postgres"):
        return "postgresql"
    return driver.split("+", 1)[0]


def create_sqlite_backup(database_url: str, backup_dir: str = "backend/backups", now: datetime | None = None) -> dict:
    url = make_url(database_url)
    database_path = url.database
    if not database_path or database_path == ":memory:":
        raise ValueError("SQLite backup requires a file-backed database")

    source_path = Path(database_path)
    if not source_path.exists():
        raise FileNotFoundError(f"SQLite database file not found: {source_path}")

    created_at = now or datetime.now(timezone.utc)
    backup_id = f"sqlite-{created_at.strftime('%Y%m%dT%H%M%S%fZ')}"
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)
    destination_path = backup_path / f"{backup_id}.db"

    shutil.copy2(source_path, destination_path)

    return {
        "status": "SUCCESS",
        "backup_id": backup_id,
        "path": str(destination_path),
        "database_backend": "sqlite",
        "created_at": created_at,
        "message": "SQLite database backup completed.",
    }


def trigger_database_backup(database_url: str, backup_dir: str = "backend/backups") -> dict:
    database_backend = detect_database_backend(database_url)
    if database_backend == "sqlite":
        return create_sqlite_backup(database_url, backup_dir=backup_dir)
    if database_backend == "postgresql":
        raise BackupProviderNotConfigured("PostgreSQL backup provider is not configured")
    raise BackupProviderNotConfigured(f"{database_backend} backup provider is not configured")


def list_database_backups(backup_dir: str = "backend/backups", limit: int = 20) -> list[dict]:
    backup_path = Path(backup_dir)
    if not backup_path.exists():
        return []

    items = []
    for path in backup_path.iterdir():
        if not path.is_file():
            continue
        stat = path.stat()
        backup_id = path.stem
        database_backend = backup_id.split("-", 1)[0] if "-" in backup_id else "unknown"
        items.append(
            {
                "backup_id": backup_id,
                "path": str(path),
                "database_backend": database_backend,
                "created_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc),
                "size_bytes": stat.st_size,
            }
        )

    return sorted(items, key=lambda item: item["created_at"], reverse=True)[:limit]
