"""
Trading Noobs Backend - Derived Refresh Job Handlers
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import DerivedTimelineSnapshot, JobRun
from release_profile import RuntimeCapability
from routers.disabled_capabilities import raise_feature_disabled
from services.capability_service import is_effective_capability_enabled
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

    lifecycle = build_trading_position_lifecycle_payload(db, truth_position)
    position_event_public_id = payload.get("position_event_public_id")
    source_node = next(
        (
            node
            for node in lifecycle["lifecycle_thread"]["nodes"]
            if node.get("related_event_public_id") == position_event_public_id
        ),
        None,
    )
    position_event_occurred_at = None
    if source_node and source_node.get("occurred_at"):
        occurred_at = source_node["occurred_at"]
        if isinstance(occurred_at, datetime):
            if occurred_at.tzinfo is None:
                occurred_at = occurred_at.replace(tzinfo=timezone.utc)
            position_event_occurred_at = occurred_at.isoformat().replace("+00:00", "Z")
        else:
            position_event_occurred_at = str(occurred_at)
    result = {
        "handler": "derived.timeline.refresh",
        "source": "truth.lifecycle.bridge",
        "trading_position_public_id": position_public_id,
        "position_event_public_id": position_event_public_id,
        "position_event_type": payload.get("position_event_type"),
        "position_event_occurred_at": position_event_occurred_at,
        "position_title": lifecycle["position_summary"]["title"],
        "review_status": lifecycle["review_status"],
        "lifecycle_node_count": len(lifecycle["lifecycle_thread"]["nodes"]),
    }
    snapshot = (
        db.query(DerivedTimelineSnapshot)
        .filter(
            DerivedTimelineSnapshot.user_id == job_run.user_id,
            DerivedTimelineSnapshot.trading_position_public_id == position_public_id,
        )
        .first()
    )
    if snapshot is None:
        snapshot = DerivedTimelineSnapshot(
            user_id=job_run.user_id,
            trading_position_public_id=position_public_id,
        )
    snapshot.source = result["source"]
    snapshot.snapshot_json = result
    snapshot.refreshed_by_job_run_public_id = job_run.public_id
    snapshot.refreshed_at = job_run.started_at or datetime.now(timezone.utc)
    db.add(snapshot)
    db.flush()
    return result


def build_default_job_handlers(db: Session):
    handlers = {
        "derived.timeline.refresh": lambda job_run: refresh_timeline_read_model(db, job_run),
    }
    if is_effective_capability_enabled(db, RuntimeCapability.MARKET):
        from services.market_data_job_handlers import build_market_data_job_handlers

        for key, handler in build_market_data_job_handlers(db).items():
            def guarded_market_handler(job_run, *, _handler=handler):
                if not is_effective_capability_enabled(db, RuntimeCapability.MARKET):
                    raise_feature_disabled(RuntimeCapability.MARKET.value)
                return _handler(job_run)

            handlers[key] = guarded_market_handler
    return handlers
