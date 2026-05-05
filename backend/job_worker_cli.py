"""
Trading Noobs Backend - Job Worker CLI
"""
from __future__ import annotations

import argparse
import socket
from datetime import datetime

from database import SessionLocal
from services.derived_refresh_handlers import build_default_job_handlers
from services.job_service import JobHandler, recover_stale_running_jobs, run_next_due_job


def run_worker_batch(
    *,
    session_factory=SessionLocal,
    queue_name: str = "default",
    worker_id: str | None = None,
    handlers: dict[str, JobHandler] | None = None,
    limit: int = 1,
    now: datetime | None = None,
    recover_stale: bool = False,
    stale_after_seconds: int = 300,
    retry_delay_seconds: int = 60,
) -> int:
    db = session_factory()
    processed = 0
    worker_id = worker_id or f"{socket.gethostname()}:job-worker"
    handlers = handlers if handlers is not None else build_default_job_handlers(db)
    try:
        if recover_stale:
            recovered = recover_stale_running_jobs(
                db,
                queue_name=queue_name,
                stale_after_seconds=stale_after_seconds,
                retry_delay_seconds=retry_delay_seconds,
                now=now,
            )
            if recovered:
                db.commit()
        for _ in range(limit):
            job_run = run_next_due_job(
                db,
                queue_name=queue_name,
                worker_id=worker_id,
                handlers=handlers,
                now=now,
            )
            if job_run is None:
                break
            db.commit()
            processed += 1
        return processed
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run due jobs from the local job_runs table.")
    parser.add_argument("--queue", default="default", help="Queue name to consume.")
    parser.add_argument("--worker-id", default=None, help="Worker identifier stored on claimed jobs.")
    parser.add_argument("--limit", type=int, default=1, help="Maximum due jobs to process in this batch.")
    parser.add_argument("--recover-stale", action="store_true", help="Recover timed-out RUNNING jobs before processing.")
    parser.add_argument("--stale-after-seconds", type=int, default=300, help="RUNNING lock age before recovery.")
    parser.add_argument("--retry-delay-seconds", type=int, default=60, help="Delay before retrying recovered jobs.")
    args = parser.parse_args(argv)

    processed = run_worker_batch(
        queue_name=args.queue,
        worker_id=args.worker_id,
        limit=args.limit,
        recover_stale=args.recover_stale,
        stale_after_seconds=args.stale_after_seconds,
        retry_delay_seconds=args.retry_delay_seconds,
    )
    print(f"processed {processed} jobs from queue {args.queue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
