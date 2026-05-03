"""
Trading Noobs Backend - Derived Refresh Job Handlers
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from models import JobRun
from services.trading_position_read_service import (
    build_trading_position_lifecycle_payload,
    resolve_truth_position_by_public_id,
)


def refresh_timeline_read_model(db: Session, job_run: JobRun) -> dict:
    payload = job_run.payload or {}
    position_public_id = payload.get("trading_position_public_id")
    if not position_public_id:
        raise ValueError("derived.timeline.refresh requires trading_position_public_id")
    if not job_run.user_id:
        raise ValueError("derived.timeline.refresh requires job_run.user_id")

    truth_position = resolve_truth_position_by_public_id(db, job_run.user_id, position_public_id)
    if not truth_position:
        raise ValueError(f"TradingPosition not found for public_id {position_public_id}")

    lifecycle = build_trading_position_lifecycle_payload(truth_position)
    return {
        "handler": "derived.timeline.refresh",
        "source": "truth.lifecycle.bridge",
        "trading_position_public_id": position_public_id,
        "position_event_public_id": payload.get("position_event_public_id"),
        "position_title": lifecycle["position_summary"]["title"],
        "review_status": lifecycle["review_status"],
        "lifecycle_node_count": len(lifecycle["lifecycle_thread"]["nodes"]),
    }


def build_default_job_handlers(db: Session):
    return {
        "derived.timeline.refresh": lambda job_run: refresh_timeline_read_model(db, job_run),
    }
