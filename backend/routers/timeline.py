"""
Trading Noobs Backend - Timeline Home Router
"""
from __future__ import annotations

import asyncio
from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections import defaultdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import DerivedTimelineSnapshot, Position, PositionStatus, TradingAccount, User
from release_profile import RuntimeCapability, is_capability_enabled
from schemas import (
    ContextRail,
    ContextRailSelectedObject,
    ContextRailQuickFilter,
    DataSourceEnum,
    ExecutionDriftSummary,
    FreshnessStatusEnum,
    InboxSeverityEnum,
    JournalTimelineHomeResponse,
    LinkedObjectRef,
    LinkedObjectTypeEnum,
    MaturityEnum,
    RecommendedActionKindEnum,
    ReviewInbox,
    ReviewInboxAction,
    ReviewInboxCounts,
    ReviewInboxItem,
    ReviewInboxKindEnum,
    SummaryBar,
    TimelineAccountRef,
    TimelineEventCard,
    TimelineEventTypeEnum,
    TimelineFeed,
    TimelineGroup,
    TimelineGroupTypeEnum,
    TimelineHomeData,
    TimelineHomePageStateEnum,
    TimelineHomeResponse,
    TimelineAiAnnotation,
    TimelineImpactValue,
    TimelineInstrumentRef,
    TimelineViewEnum,
    TrustMeta,
    ValueStatusEnum,
    WeeklyDisciplineSnapshot,
)
from services.auth_service import get_current_user
from services.capability_service import is_effective_capability_enabled
from services.derived_timeline_read_service import list_recent_timeline_snapshots
from services.platform_config_service import get_feature_flag_enabled
from services.timeline_source_policy import get_timeline_source_mode
from routers.disabled_capabilities import raise_feature_disabled

if TYPE_CHECKING:
    from models import AIAnalysisResult, AISummary

TIMELINE_PREFIX = "/api/timeline"
TIMELINE_TAGS = ["Timeline"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _determine_page_state(active_account_count: int, position_count: int) -> TimelineHomePageStateEnum:
    if active_account_count == 0 and position_count == 0:
        return TimelineHomePageStateEnum.ZERO
    if active_account_count > 0 and position_count == 0:
        return TimelineHomePageStateEnum.EMPTY_CONFIGURED
    if position_count < 5:
        return TimelineHomePageStateEnum.SMALL_DATA
    return TimelineHomePageStateEnum.READY


def _determine_maturity(page_state: TimelineHomePageStateEnum) -> MaturityEnum:
    if page_state == TimelineHomePageStateEnum.READY:
        return MaturityEnum.STABLE
    return MaturityEnum.INSUFFICIENT_SAMPLE


def _trust_meta(
    *,
    as_of: str,
    source: DataSourceEnum = DataSourceEnum.DERIVED,
    maturity: MaturityEnum | None = None,
    value_status: ValueStatusEnum | None = None,
    note: str | None = None,
) -> TrustMeta:
    return TrustMeta(
        as_of=as_of,
        generated_at=as_of,
        freshness=FreshnessStatusEnum.FRESH,
        source=source,
        maturity=maturity,
        value_status=value_status,
        note=note,
    )


def _position_route(position: Position) -> str:
    return f"/positions/{position.public_id}"


def _position_title(position: Position) -> str:
    return position.symbol


def _instrument_ref(position: Position) -> TimelineInstrumentRef:
    asset_label = position.asset_metadata.name if position.asset_metadata and position.asset_metadata.name else position.symbol
    instrument_label = position.asset_metadata.instrument if position.asset_metadata and position.asset_metadata.instrument else position.exchange
    return TimelineInstrumentRef(
        asset_label=asset_label,
        instrument_label=instrument_label,
        symbol=position.symbol,
        href=_position_route(position),
    )


def _account_ref(position: Position) -> TimelineAccountRef | None:
    if not position.trading_account:
        return None
    return TimelineAccountRef(
        public_id=position.trading_account.public_id,
        label=position.trading_account.name,
    )


def _event_card(
    *,
    position: Position,
    event_type: TimelineEventTypeEnum,
    occurred_at: datetime,
    headline: str,
    summary: str,
    amount: float | None = None,
    confidence: float | None = None,
    checklist_summary: str | None = None,
    execution_quality: str | None = None,
) -> TimelineEventCard:
    execution_drift = None
    if execution_quality:
        execution_drift = ExecutionDriftSummary(
            has_drift=True,
            execution_quality=execution_quality.upper(),
        )

    impact_value = None
    if amount is not None:
        impact_value = TimelineImpactValue(amount=amount)

    return TimelineEventCard(
        event_public_id=f"{position.public_id}:{event_type.value.lower()}:{occurred_at.isoformat()}",
        thread_public_id=position.public_id,
        event_type=event_type,
        occurred_at=occurred_at.isoformat().replace("+00:00", "Z"),
        headline=headline,
        summary=summary,
        impact_value=impact_value,
        instrument=_instrument_ref(position),
        account=_account_ref(position),
        confidence=confidence,
        checklist_summary=checklist_summary,
        href=_position_route(position),
        execution_drift=execution_drift,
        trust=None,
    )


def _build_review_inbox(positions: list[Position], as_of: str) -> ReviewInbox:
    items: list[ReviewInboxItem] = []
    for position in positions:
        if position.closed_at and not (position.trade_review or "").strip():
            occurred_at = position.closed_at.isoformat().replace("+00:00", "Z")
            items.append(
                ReviewInboxItem(
                    public_id=f"inbox:{position.public_id}:missing_review",
                    kind=ReviewInboxKindEnum.MISSING_REVIEW,
                    severity=InboxSeverityEnum.WARNING,
                    summary=f"{position.symbol} 已平仓，但还没有写复盘",
                    reason="Closed position without completed review artifact",
                    recommended_action=ReviewInboxAction(
                        kind=RecommendedActionKindEnum.START_REVIEW,
                        label="开始复盘",
                        href=_position_route(position),
                    ),
                    linked_object=LinkedObjectRef(
                        object_type=LinkedObjectTypeEnum.TRADING_POSITION,
                        public_id=position.public_id,
                        label=_position_title(position),
                        href=_position_route(position),
                    ),
                    occurred_at=occurred_at,
                    trust=_trust_meta(
                        as_of=as_of,
                        source=DataSourceEnum.DERIVED,
                        maturity=MaturityEnum.INSUFFICIENT_SAMPLE,
                        value_status=ValueStatusEnum.FINAL,
                    ),
                )
            )

    high_priority = sum(1 for item in items if item.severity in {InboxSeverityEnum.WARNING, InboxSeverityEnum.CRITICAL})
    return ReviewInbox(
        counts=ReviewInboxCounts(total=len(items), high_priority=high_priority),
        items=sorted(items, key=lambda item: item.occurred_at, reverse=True),
        trust=_trust_meta(
            as_of=as_of,
            source=DataSourceEnum.DERIVED,
            maturity=MaturityEnum.INSUFFICIENT_SAMPLE if items else None,
            value_status=ValueStatusEnum.FINAL,
        ),
    )


def _build_snapshot_review_inbox(snapshots: list[DerivedTimelineSnapshot], as_of: str) -> ReviewInbox:
    items: list[ReviewInboxItem] = []
    for snapshot in snapshots:
        snapshot_json = snapshot.snapshot_json or {}
        if snapshot_json.get("review_status") != "CLOSED_PENDING_REVIEW":
            continue

        position_title = snapshot_json.get("position_title") or snapshot.trading_position_public_id
        occurred_at_value = snapshot_json.get("position_event_occurred_at")
        if occurred_at_value:
            occurred_at_iso = str(occurred_at_value).replace("+00:00", "Z")
        else:
            occurred_at = snapshot.refreshed_at or snapshot.updated_at or snapshot.created_at or datetime.now(timezone.utc)
            if occurred_at.tzinfo is None:
                occurred_at = occurred_at.replace(tzinfo=timezone.utc)
            occurred_at_iso = occurred_at.isoformat().replace("+00:00", "Z")

        href = f"/positions/{snapshot.trading_position_public_id}"
        items.append(
            ReviewInboxItem(
                public_id=f"inbox:{snapshot.trading_position_public_id}:missing_review",
                kind=ReviewInboxKindEnum.MISSING_REVIEW,
                severity=InboxSeverityEnum.WARNING,
                summary=f"{position_title} 已平仓，但复盘尚未完成",
                reason="生命周期快照显示该持仓已平仓，仍缺少复盘记录",
                recommended_action=ReviewInboxAction(
                    kind=RecommendedActionKindEnum.START_REVIEW,
                    label="开始复盘",
                    href=href,
                ),
                linked_object=LinkedObjectRef(
                    object_type=LinkedObjectTypeEnum.TRADING_POSITION,
                    public_id=snapshot.trading_position_public_id,
                    label=position_title,
                    href=href,
                ),
                occurred_at=occurred_at_iso,
                trust=_trust_meta(
                    as_of=as_of,
                    source=DataSourceEnum.DERIVED,
                    maturity=MaturityEnum.EARLY_SIGNAL,
                    value_status=ValueStatusEnum.FINAL,
                ),
            )
        )

    high_priority = sum(1 for item in items if item.severity in {InboxSeverityEnum.WARNING, InboxSeverityEnum.CRITICAL})
    return ReviewInbox(
        counts=ReviewInboxCounts(total=len(items), high_priority=high_priority),
        items=sorted(items, key=lambda item: item.occurred_at, reverse=True),
        trust=_trust_meta(
            as_of=as_of,
            source=DataSourceEnum.DERIVED,
            maturity=MaturityEnum.EARLY_SIGNAL if items else None,
            value_status=ValueStatusEnum.FINAL,
        ),
    )


def _get_latest_losing_streak(positions: list[Position]) -> list[Position]:
    closed_positions = sorted(
        [position for position in positions if position.closed_at],
        key=lambda position: position.closed_at,
    )
    current_streak: list[Position] = []
    best_streak: list[Position] = []

    for position in closed_positions:
        pnl = float(position.realized_pnl or 0)
        if pnl < 0:
            current_streak.append(position)
            if len(current_streak) >= len(best_streak):
                best_streak = list(current_streak)
        else:
            current_streak = []

    if len(current_streak) >= len(best_streak):
        best_streak = current_streak

    return best_streak if len(best_streak) >= 2 else []


def _append_losing_streak_inbox_item(items: list[ReviewInboxItem], positions: list[Position], as_of: str) -> None:
    streak = _get_latest_losing_streak(positions)
    if not streak:
        return

    last_position = streak[-1]
    total_loss = sum(float(position.realized_pnl or 0) for position in streak)
    items.append(
        ReviewInboxItem(
            public_id=f"inbox:{last_position.public_id}:losing_streak",
            kind=ReviewInboxKindEnum.LOSING_STREAK,
            severity=InboxSeverityEnum.WARNING,
            summary=f"连续 {len(streak)} 笔亏损，需要回看执行节奏",
            reason=f"最近连续亏损 {len(streak)} 笔，累计 {total_loss:.2f}",
            recommended_action=ReviewInboxAction(
                kind=RecommendedActionKindEnum.OPEN_POSITION_DETAIL,
                label="查看最近一笔",
                href=_position_route(last_position),
            ),
            linked_object=LinkedObjectRef(
                object_type=LinkedObjectTypeEnum.TRADING_POSITION,
                public_id=last_position.public_id,
                label=_position_title(last_position),
                href=_position_route(last_position),
            ),
            occurred_at=last_position.closed_at.isoformat().replace("+00:00", "Z"),
            trust=_trust_meta(
                as_of=as_of,
                source=DataSourceEnum.DERIVED,
                maturity=MaturityEnum.INSUFFICIENT_SAMPLE if len(streak) < 5 else MaturityEnum.EARLY_SIGNAL,
                value_status=ValueStatusEnum.FINAL,
            ),
        )
    )


def _build_data_stale_items(
    positions: list[Position],
    db: Session,
    as_of: str,
    *,
    actor_key: str,
) -> list[ReviewInboxItem]:
    items: list[ReviewInboxItem] = []
    open_positions = [position for position in positions if position.status == PositionStatus.OPEN]
    if not open_positions:
        return items

    from services.market_data_access import MarketDataService

    market_service = MarketDataService(db, actor_key=actor_key)
    for position in open_positions:
        try:
            asyncio.run(market_service.get_quote(position.symbol, position.exchange))
        except Exception as exc:
            reason = str(exc)
            lowered = reason.lower()
            should_surface = (
                "timed out" in lowered
                or "empty data" in lowered
                or "unauthorized" in lowered
                or "invalid symbol" in lowered
                or "returned empty data" in lowered
            )
            if not should_surface:
                continue
            occurred_at = (position.updated_at or position.opened_at).isoformat().replace("+00:00", "Z")
            items.append(
                ReviewInboxItem(
                    public_id=f"inbox:{position.public_id}:data_stale",
                    kind=ReviewInboxKindEnum.DATA_STALE,
                    severity=InboxSeverityEnum.WARNING,
                    summary=f"{position.symbol} 行情数据暂时不可用",
                    reason=reason,
                    recommended_action=ReviewInboxAction(
                        kind=RecommendedActionKindEnum.OPEN_POSITION_DETAIL,
                        label="查看交易详情",
                        href=_position_route(position),
                    ),
                    linked_object=LinkedObjectRef(
                        object_type=LinkedObjectTypeEnum.TRADING_POSITION,
                        public_id=position.public_id,
                        label=_position_title(position),
                        href=_position_route(position),
                    ),
                    occurred_at=occurred_at,
                    trust=_trust_meta(
                        as_of=as_of,
                        source=DataSourceEnum.SYNCED,
                        maturity=MaturityEnum.INSUFFICIENT_SAMPLE,
                        value_status=ValueStatusEnum.ESTIMATED,
                    ),
                )
            )
    return items


def _risk_review_kind(alert_kind: str) -> ReviewInboxKindEnum | None:
    if alert_kind == "DAILY_LOSS_LIMIT":
        return ReviewInboxKindEnum.DAILY_LOSS_LIMIT
    if alert_kind == "CONCENTRATION":
        return ReviewInboxKindEnum.PORTFOLIO_CONCENTRATION
    if alert_kind == "DRAWDOWN":
        return ReviewInboxKindEnum.DRAWDOWN_ALERT
    return None


def _build_risk_review_inbox_items(
    *,
    risk_summary: dict,
    user: User,
    as_of: str,
) -> list[ReviewInboxItem]:
    items: list[ReviewInboxItem] = []
    for alert in risk_summary.get("alerts", []):
        review_kind = _risk_review_kind(str(alert.get("kind", "")))
        if review_kind is None:
            continue

        alert_trust = alert.get("trust") if isinstance(alert.get("trust"), dict) else {}
        value_status = alert_trust.get("value_status")
        items.append(
            ReviewInboxItem(
                public_id=f"inbox:{alert['public_id']}",
                kind=review_kind,
                severity=InboxSeverityEnum(alert["severity"]),
                summary=alert["summary"],
                reason=alert["reason"],
                recommended_action=ReviewInboxAction(
                    kind=RecommendedActionKindEnum.OPEN_DASHBOARD,
                    label=alert.get("recommended_action", {}).get("label", "查看组合风险"),
                    href=alert.get("recommended_action", {}).get("href", "/dashboard"),
                ),
                linked_object=LinkedObjectRef(
                    object_type=LinkedObjectTypeEnum.PORTFOLIO,
                    public_id=user.public_id or f"user:{user.id}",
                    label="Portfolio Risk",
                    href="/dashboard",
                ),
                occurred_at=risk_summary.get("as_of") or as_of,
                trust=TrustMeta(
                    as_of=as_of,
                    generated_at=as_of,
                    freshness=FreshnessStatusEnum(alert_trust.get("freshness", FreshnessStatusEnum.FRESH.value)),
                    source=DataSourceEnum(alert_trust.get("source", DataSourceEnum.DERIVED.value)),
                    maturity=MaturityEnum.EARLY_SIGNAL,
                    value_status=(
                        ValueStatusEnum(value_status)
                        if value_status
                        else ValueStatusEnum.ESTIMATED
                    ),
                    source_refs=alert.get("source_refs", []),
                    note="Portfolio risk alert",
                ),
            )
        )
    return items


def _list_ai_summaries(db: Session, *, user_id: int) -> list[AISummary]:
    from models import AISummary

    return (
        db.query(AISummary)
        .filter(AISummary.user_id == user_id)
        .order_by(AISummary.created_at.desc())
        .limit(5)
        .all()
    )


def _list_ai_analysis_results(db: Session, *, user_id: int) -> list[AIAnalysisResult]:
    from models import AIAnalysisResult

    return (
        db.query(AIAnalysisResult)
        .filter(AIAnalysisResult.user_id == user_id)
        .order_by(AIAnalysisResult.created_at.desc())
        .limit(5)
        .all()
    )


def _list_insight_runs(db: Session, *, user_id: int) -> list[dict]:
    from services.insight_artifact_service import InsightArtifactService

    return InsightArtifactService(db).list_runs(user_id=user_id, limit=5)


def _load_llm_runtime_config(db: Session) -> dict[str, str | None]:
    from services.platform_config_service import get_llm_runtime_config

    return get_llm_runtime_config(db)


def _load_portfolio_risk_summary(db: Session, *, user_id: int) -> dict:
    from services.risk_alert_service import build_portfolio_risk_summary

    return build_portfolio_risk_summary(db, user_id)


def _build_timeline_events(positions: list[Position], ai_summaries: list[AISummary]) -> list[TimelineEventCard]:
    events: list[TimelineEventCard] = []
    for position in positions:
        events.append(
            _event_card(
                position=position,
                event_type=TimelineEventTypeEnum.OPEN,
                occurred_at=position.opened_at,
                headline=f"{position.symbol} 开仓",
                summary=f"{position.direction.value} 仓位已建立，当前数量 {float(position.total_quantity or 0):g}",
            )
        )
        if position.closed_at:
            events.append(
                _event_card(
                    position=position,
                    event_type=TimelineEventTypeEnum.CLOSE,
                    occurred_at=position.closed_at,
                    headline=f"{position.symbol} 平仓",
                    summary="这笔交易已经完成，结果已结算。",
                    amount=float(position.realized_pnl or 0),
                )
            )
        if (position.trade_review or "").strip():
            review_time = position.updated_at or position.closed_at or position.opened_at
            events.append(
                _event_card(
                    position=position,
                    event_type=TimelineEventTypeEnum.REVIEW_COMPLETED,
                    occurred_at=review_time,
                    headline=f"{position.symbol} 已完成复盘",
                    summary=(position.trade_review or "").strip()[:120],
                )
            )
        if position.checklist_responses:
            missed = sum(1 for checked in position.checklist_responses.values() if checked is False)
            if missed > 0:
                events.append(
                    _event_card(
                        position=position,
                        event_type=TimelineEventTypeEnum.CHECKLIST_MISS,
                        occurred_at=position.updated_at or position.opened_at,
                        headline=f"{position.symbol} Checklist Miss",
                        summary=f"这笔交易有 {missed} 项检查清单未命中。",
                        checklist_summary=f"{missed} 项未命中",
                    )
                )

    for summary in ai_summaries:
        summary_time = summary.created_at
        events.append(
            TimelineEventCard(
                event_public_id=f"ai-summary:{summary.id}",
                thread_public_id=f"ai-summary:{summary.id}",
                event_type=TimelineEventTypeEnum.AI_INSIGHT,
                occurred_at=summary_time.isoformat().replace("+00:00", "Z"),
                headline="AI 今日总结",
                summary=summary.content[:120],
                instrument=TimelineInstrumentRef(
                    asset_label="Trading Noobs",
                    instrument_label="AI Summary",
                    symbol="AI",
                    href="/insights",
                ),
                href="/insights",
                trust=None,
            )
        )

    return sorted(events, key=lambda event: event.occurred_at, reverse=True)


def _build_materialized_timeline_events(
    snapshots: list[DerivedTimelineSnapshot],
    *,
    as_of: str,
) -> list[TimelineEventCard]:
    events: list[TimelineEventCard] = []
    action_labels = {
        TimelineEventTypeEnum.OPEN: "开仓",
        TimelineEventTypeEnum.ADD: "加仓",
        TimelineEventTypeEnum.REDUCE: "减仓",
        TimelineEventTypeEnum.CLOSE: "平仓",
    }
    for snapshot in snapshots:
        snapshot_json = snapshot.snapshot_json or {}
        position_title = snapshot_json.get("position_title") or snapshot.trading_position_public_id
        lifecycle_node_count = snapshot_json.get("lifecycle_node_count")
        event_type = TimelineEventTypeEnum.OPEN
        try:
            event_type = TimelineEventTypeEnum(snapshot_json.get("position_event_type") or TimelineEventTypeEnum.OPEN.value)
        except ValueError:
            event_type = TimelineEventTypeEnum.OPEN
        occurred_at_value = snapshot_json.get("position_event_occurred_at")
        if occurred_at_value:
            occurred_at_iso = str(occurred_at_value).replace("+00:00", "Z")
        else:
            occurred_at = snapshot.refreshed_at or snapshot.updated_at or snapshot.created_at or datetime.now(timezone.utc)
            if occurred_at.tzinfo is None:
                occurred_at = occurred_at.replace(tzinfo=timezone.utc)
            occurred_at_iso = occurred_at.isoformat().replace("+00:00", "Z")
        events.append(
            TimelineEventCard(
                event_public_id=f"derived-timeline:{snapshot.public_id}",
                thread_public_id=snapshot.trading_position_public_id,
                event_type=event_type,
                occurred_at=occurred_at_iso,
                headline=f"{position_title} {action_labels.get(event_type, '生命周期更新')}",
                summary=f"生命周期快照已更新，共 {lifecycle_node_count or 0} 个事件节点。",
                instrument=TimelineInstrumentRef(
                    asset_label=position_title,
                    instrument_label="交易生命周期",
                    symbol=position_title,
                    href=f"/positions/{snapshot.trading_position_public_id}",
                ),
                href=f"/positions/{snapshot.trading_position_public_id}",
                trust=_trust_meta(
                    as_of=as_of,
                    source=DataSourceEnum.DERIVED,
                    maturity=MaturityEnum.EARLY_SIGNAL,
                    value_status=ValueStatusEnum.FINAL,
                ),
            )
        )
    return events


def _build_ai_insight_events(ai_results: list[AIAnalysisResult]) -> list[TimelineEventCard]:
    events: list[TimelineEventCard] = []
    for result in ai_results:
        if not (result.ai_insights or "").strip():
            continue
        events.append(
            TimelineEventCard(
                event_public_id=f"ai-analysis:{result.id}",
                thread_public_id=f"ai-analysis:{result.analysis_type}",
                event_type=TimelineEventTypeEnum.AI_INSIGHT,
                occurred_at=result.created_at.isoformat().replace("+00:00", "Z"),
                headline=f"AI 分析：{result.analysis_type}",
                summary=result.ai_insights[:120],
                instrument=TimelineInstrumentRef(
                    asset_label="Trading Noobs",
                    instrument_label="AI Analysis",
                    symbol="AI",
                    href="/insights",
                ),
                href="/insights",
                trust=None,
            )
        )
    return events


def _build_ai_insight_events_from_runs(runs: list[dict]) -> list[TimelineEventCard]:
    events: list[TimelineEventCard] = []
    for run in runs:
        for artifact in run.get("artifacts", []):
            if not artifact.get("summary"):
                continue
            artifact_public_id = artifact["public_id"]
            artifact_trust = artifact.get("trust_meta") if isinstance(artifact.get("trust_meta"), dict) else {}
            occurred_at = artifact.get("created_at") or run["started_at"]
            events.append(
                TimelineEventCard(
                    event_public_id=f"insight-artifact:{artifact_public_id}",
                    thread_public_id=run["public_id"],
                    event_type=TimelineEventTypeEnum.AI_INSIGHT,
                    occurred_at=occurred_at,
                    headline=artifact.get("title") or f"AI 分析：{run['run_type']}",
                    summary=artifact["summary"][:120],
                    instrument=TimelineInstrumentRef(
                        asset_label="Trading Noobs",
                        instrument_label="Insight Artifact",
                        symbol="AI",
                        href=f"/insights/{artifact_public_id}",
                    ),
                    ai_annotation=TimelineAiAnnotation(
                        artifact_public_id=artifact_public_id,
                        summary=artifact["summary"][:120],
                        href=f"/insights/{artifact_public_id}",
                    ),
                    href=f"/insights/{artifact_public_id}",
                    trust=TrustMeta(
                        as_of=occurred_at,
                        generated_at=occurred_at,
                        freshness=FreshnessStatusEnum(artifact_trust.get("freshness", FreshnessStatusEnum.FRESH.value)),
                        source=DataSourceEnum(artifact_trust.get("source", DataSourceEnum.AI_GENERATED.value)),
                        maturity=(
                            MaturityEnum(artifact_trust["maturity"])
                            if artifact_trust.get("maturity")
                            else None
                        ),
                        value_status=(
                            ValueStatusEnum(artifact_trust["value_status"])
                            if artifact_trust.get("value_status")
                            else ValueStatusEnum.FINAL
                        ),
                        source_refs=artifact_trust.get("source_refs", []),
                        note=artifact_trust.get("note"),
                    ),
                )
            )
    return events


def _build_losing_streak_events(positions: list[Position]) -> list[TimelineEventCard]:
    streak = _get_latest_losing_streak(positions)
    if not streak:
        return []

    last_position = streak[-1]
    total_loss = sum(float(position.realized_pnl or 0) for position in streak)
    return [
        _event_card(
            position=last_position,
            event_type=TimelineEventTypeEnum.LOSING_STREAK_ALERT,
            occurred_at=last_position.closed_at,
            headline=f"连续 {len(streak)} 笔亏损",
            summary=f"最近连续亏损 {len(streak)} 笔，累计 {total_loss:.2f}，建议优先复盘。",
            amount=total_loss,
        )
    ]


def _build_data_stale_events(inbox_items: list[ReviewInboxItem], positions: list[Position]) -> list[TimelineEventCard]:
    position_map = {position.public_id: position for position in positions}
    events: list[TimelineEventCard] = []
    for item in inbox_items:
        if item.kind != ReviewInboxKindEnum.DATA_STALE:
            continue
        position = position_map.get(item.linked_object.public_id)
        if not position:
            continue
        occurred_at = datetime.fromisoformat(item.occurred_at.replace("Z", "+00:00"))
        events.append(
            _event_card(
                position=position,
                event_type=TimelineEventTypeEnum.DATA_STALE,
                occurred_at=occurred_at,
                headline=f"{position.symbol} 数据延迟",
                summary=item.reason,
            )
        )
    return events


def _build_sync_exception_events(
    ai_results: list[AIAnalysisResult],
    llm_config: dict[str, str | None],
) -> list[TimelineEventCard]:
    if not ai_results:
        return []
    if llm_config.get("api_url") and llm_config.get("api_key"):
        return []

    latest = ai_results[0]
    return [
        TimelineEventCard(
            event_public_id=f"sync-exception:llm:{latest.id}",
            thread_public_id="sync-exception:llm",
            event_type=TimelineEventTypeEnum.SYNC_EXCEPTION,
            occurred_at=latest.created_at.isoformat().replace("+00:00", "Z"),
            headline="LLM 配置缺失",
            summary="系统存在 AI 分析结果，但当前 LLM 运行配置不完整，新的 AI 任务可能无法继续生成。",
            instrument=TimelineInstrumentRef(
                asset_label="Trading Noobs",
                instrument_label="Platform Config",
                symbol="OPS",
                href="/settings",
            ),
            href="/settings",
            trust=None,
        )
    ]


def _filter_events(events: list[TimelineEventCard], view: TimelineViewEnum) -> list[TimelineEventCard]:
    if view == TimelineViewEnum.ALL:
        return events
    if view == TimelineViewEnum.TRADING:
        allowed = {
            TimelineEventTypeEnum.OPEN,
            TimelineEventTypeEnum.ADD,
            TimelineEventTypeEnum.REDUCE,
            TimelineEventTypeEnum.CLOSE,
        }
        return [event for event in events if event.event_type in allowed]
    if view == TimelineViewEnum.REVIEW:
        allowed = {
            TimelineEventTypeEnum.REVIEW_COMPLETED,
            TimelineEventTypeEnum.CHECKLIST_MISS,
        }
        return [event for event in events if event.event_type in allowed]
    if view == TimelineViewEnum.AI:
        return [event for event in events if event.event_type == TimelineEventTypeEnum.AI_INSIGHT]
    if view == TimelineViewEnum.EXCEPTION:
        allowed = {
            TimelineEventTypeEnum.CHECKLIST_MISS,
            TimelineEventTypeEnum.LOSING_STREAK_ALERT,
            TimelineEventTypeEnum.DATA_STALE,
            TimelineEventTypeEnum.SYNC_EXCEPTION,
        }
        return [event for event in events if event.event_type in allowed]
    return events


def _encode_timeline_cursor(event: TimelineEventCard) -> str:
    return urlsafe_b64encode(event.event_public_id.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_timeline_cursor(cursor: str) -> str:
    try:
        padding = "=" * (-len(cursor) % 4)
        return urlsafe_b64decode(f"{cursor}{padding}".encode("ascii")).decode("utf-8")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid timeline cursor") from exc


def _sort_timeline_events(events: list[TimelineEventCard]) -> list[TimelineEventCard]:
    return sorted(events, key=lambda event: (event.occurred_at, event.event_public_id), reverse=True)


def _paginate_timeline_events(
    events: list[TimelineEventCard],
    *,
    cursor: str | None,
    limit: int | None,
) -> tuple[list[TimelineEventCard], str | None]:
    sorted_events = _sort_timeline_events(events)
    start_index = 0

    if cursor:
        cursor_event_public_id = _decode_timeline_cursor(cursor)
        for index, event in enumerate(sorted_events):
            if event.event_public_id == cursor_event_public_id:
                start_index = index + 1
                break
        else:
            raise HTTPException(status_code=400, detail="Invalid timeline cursor")

    if limit is None:
        return sorted_events[start_index:], None

    page = sorted_events[start_index:start_index + limit]
    next_cursor = None
    if page and start_index + limit < len(sorted_events):
        next_cursor = _encode_timeline_cursor(page[-1])

    return page, next_cursor


def _group_events(events: list[TimelineEventCard]) -> list[TimelineGroup]:
    grouped: dict[str, list[TimelineEventCard]] = defaultdict(list)
    for event in events:
        group_key = event.occurred_at[:10]
        grouped[group_key].append(event)

    groups: list[TimelineGroup] = []
    for group_key in sorted(grouped.keys(), reverse=True):
        groups.append(
            TimelineGroup(
                group_key=group_key,
                group_label=group_key,
                group_type=TimelineGroupTypeEnum.DAY,
                items=grouped[group_key],
            )
        )
    return groups


def _build_context_rail(
    *,
    positions: list[Position],
    view: TimelineViewEnum,
    review_completion_rate: float | None,
    closed_count: int,
    selected_object_public_id: str | None,
    as_of: str,
    include_ai_view: bool,
) -> ContextRail:
    selected_object = None
    if selected_object_public_id:
        selected_position = next((position for position in positions if position.public_id == selected_object_public_id), None)
        if selected_position:
            subtitle = None
            if selected_position.trading_account:
                subtitle = selected_position.trading_account.name
            selected_object = ContextRailSelectedObject(
                object_type=LinkedObjectTypeEnum.TRADING_POSITION,
                public_id=selected_position.public_id,
                title=selected_position.symbol,
                subtitle=subtitle,
                href=_position_route(selected_position),
            )

    quick_filters = [
        ContextRailQuickFilter(key=option.value, label=option.value.title(), active=option == view)
        for option in TimelineViewEnum
        if include_ai_view or option != TimelineViewEnum.AI
    ]

    weekly_snapshot = None
    if closed_count > 0:
        rate = 0 if review_completion_rate is None else int(round(review_completion_rate * 100))
        weekly_snapshot = WeeklyDisciplineSnapshot(
            headline="本周纪律画像",
            summary=f"已平仓交易 {closed_count} 笔，复盘完成率 {rate}%。",
            trust=_trust_meta(
                as_of=as_of,
                source=DataSourceEnum.DERIVED,
                maturity=MaturityEnum.INSUFFICIENT_SAMPLE if closed_count < 5 else MaturityEnum.EARLY_SIGNAL,
                value_status=ValueStatusEnum.FINAL,
            ),
        )

    return ContextRail(
        selected_object=selected_object,
        weekly_discipline_snapshot=weekly_snapshot,
        quick_filters=quick_filters,
        related_items=[],
        trust=_trust_meta(
            as_of=as_of,
            source=DataSourceEnum.DERIVED,
            maturity=MaturityEnum.INSUFFICIENT_SAMPLE if closed_count < 5 else MaturityEnum.EARLY_SIGNAL,
            value_status=ValueStatusEnum.FINAL,
        ),
    )


def _get_timeline_home(
    *,
    view: TimelineViewEnum,
    cursor: str | None,
    limit: int | None,
    selected_object_public_id: str | None,
    current_user: User,
    db: Session,
    include_optional_capabilities: bool,
):
    active_account_count = (
        db.query(func.count(TradingAccount.id))
        .filter(
            TradingAccount.user_id == current_user.id,
            TradingAccount.is_active == True,
        )
        .scalar()
        or 0
    )

    positions = (
        db.query(Position)
        .join(
            TradingAccount,
            Position.account_id == TradingAccount.id,
        )
        .filter(
            Position.user_id == current_user.id,
            TradingAccount.user_id == current_user.id,
        )
        .order_by(Position.opened_at.desc())
        .all()
    )
    position_count = len(positions)

    reviewed_closed_count = (
        sum(1 for position in positions if position.closed_at and (position.trade_review or "").strip())
    )

    closed_count = (
        sum(1 for position in positions if position.closed_at)
    )

    page_state = _determine_page_state(active_account_count, position_count)
    review_completion_rate = None
    if closed_count > 0:
        review_completion_rate = reviewed_closed_count / closed_count

    as_of = _utc_now_iso()
    actor_key = current_user.public_id
    ai_insights_enabled = False
    market_enabled = False
    risk_cards_enabled = False
    if include_optional_capabilities:
        ai_insights_enabled = is_effective_capability_enabled(
            db,
            RuntimeCapability.AI_INSIGHTS,
            actor_key=actor_key,
        )
        market_enabled = is_effective_capability_enabled(
            db,
            RuntimeCapability.MARKET,
            actor_key=actor_key,
        )
        risk_cards_enabled = is_effective_capability_enabled(
            db,
            RuntimeCapability.RISK_CARDS,
            actor_key=actor_key,
        )
    if view == TimelineViewEnum.AI and not ai_insights_enabled:
        raise_feature_disabled(RuntimeCapability.AI_INSIGHTS.value)
    legacy_mixed_feed_enabled = get_feature_flag_enabled(
        db,
        "timeline_legacy_mixed_feed_enabled",
        actor_key=actor_key,
    )
    source_mode = get_timeline_source_mode(legacy_mixed_feed_enabled=legacy_mixed_feed_enabled)
    snapshot_only_enabled = source_mode == "SNAPSHOT_ONLY"
    source_mode_note = (
        "审计快照视图"
        if snapshot_only_enabled
        else "已启用旧版混合回退"
    )
    meta = _trust_meta(
        as_of=as_of,
        source=DataSourceEnum.DERIVED,
        maturity=_determine_maturity(page_state),
        value_status=ValueStatusEnum.ESTIMATED,
        note=source_mode_note,
    )
    timeline_snapshots = list_recent_timeline_snapshots(db, user_id=current_user.id, limit=50)

    if snapshot_only_enabled:
        review_inbox = _build_snapshot_review_inbox(timeline_snapshots, as_of)
        inbox_items = list(review_inbox.items)
    else:
        review_inbox = _build_review_inbox(positions, as_of)
        inbox_items = list(review_inbox.items)
        _append_losing_streak_inbox_item(inbox_items, positions, as_of)
        if market_enabled:
            inbox_items.extend(
                _build_data_stale_items(
                    positions,
                    db,
                    as_of,
                    actor_key=actor_key,
                )
            )

    if risk_cards_enabled:
        inbox_items.extend(
            _build_risk_review_inbox_items(
                risk_summary=_load_portfolio_risk_summary(db, user_id=current_user.id),
                user=current_user,
                as_of=as_of,
            )
        )

    review_inbox = ReviewInbox(
        counts=ReviewInboxCounts(
            total=len(inbox_items),
            high_priority=sum(
                1 for item in inbox_items if item.severity in {InboxSeverityEnum.WARNING, InboxSeverityEnum.CRITICAL}
            ),
        ),
        items=sorted(inbox_items, key=lambda item: item.occurred_at, reverse=True),
        trust=review_inbox.trust,
    )

    materialized_timeline_events = _build_materialized_timeline_events(
        timeline_snapshots,
        as_of=as_of,
    )
    artifact_events: list[TimelineEventCard] = []
    if ai_insights_enabled:
        insight_runs = _list_insight_runs(db, user_id=current_user.id)
        artifact_events = _build_ai_insight_events_from_runs(insight_runs)

    if snapshot_only_enabled:
        timeline_events = materialized_timeline_events + artifact_events
    else:
        ai_summaries: list[AISummary] = []
        optional_ai_events: list[TimelineEventCard] = []
        sync_exception_events: list[TimelineEventCard] = []
        if ai_insights_enabled:
            ai_summaries = _list_ai_summaries(db, user_id=current_user.id)
            ai_results = _list_ai_analysis_results(db, user_id=current_user.id)
            optional_ai_events = artifact_events or _build_ai_insight_events(ai_results)
            if ai_results:
                sync_exception_events = _build_sync_exception_events(
                    ai_results,
                    _load_llm_runtime_config(db),
                )

        data_stale_events = (
            _build_data_stale_events(inbox_items, positions)
            if market_enabled
            else []
        )
        timeline_events = (
            _build_timeline_events(positions, ai_summaries)
            + materialized_timeline_events
            + optional_ai_events
            + _build_losing_streak_events(positions)
            + data_stale_events
            + sync_exception_events
        )
    if not ai_insights_enabled:
        timeline_events = [
            event
            for event in timeline_events
            if event.event_type != TimelineEventTypeEnum.AI_INSIGHT
        ]
    if not include_optional_capabilities:
        journal_event_types = {
            TimelineEventTypeEnum.OPEN,
            TimelineEventTypeEnum.ADD,
            TimelineEventTypeEnum.REDUCE,
            TimelineEventTypeEnum.CLOSE,
            TimelineEventTypeEnum.REVIEW_COMPLETED,
            TimelineEventTypeEnum.CHECKLIST_MISS,
            TimelineEventTypeEnum.LOSING_STREAK_ALERT,
        }
        timeline_events = [
            event for event in timeline_events if event.event_type in journal_event_types
        ]
    filtered_events = _filter_events(timeline_events, view)
    paged_events, next_cursor = _paginate_timeline_events(filtered_events, cursor=cursor, limit=limit)
    grouped_events = _group_events(paged_events)
    context_rail = _build_context_rail(
        positions=positions,
        view=view,
        review_completion_rate=review_completion_rate,
        closed_count=closed_count,
        selected_object_public_id=selected_object_public_id,
        as_of=as_of,
        include_ai_view=ai_insights_enabled,
    )

    return TimelineHomeResponse(
        data=TimelineHomeData(
            page_state=page_state,
            summary_bar=SummaryBar(
                period_label="THIS_WEEK",
                trade_count=position_count,
                review_completion_rate=review_completion_rate,
                priority_alert_count=review_inbox.counts.high_priority,
                trust=meta,
            ),
            review_inbox=review_inbox,
            timeline=TimelineFeed(
                active_view=view,
                next_cursor=next_cursor,
                groups=grouped_events,
                trust=_trust_meta(
                    as_of=as_of,
                    source=DataSourceEnum.DERIVED,
                    maturity=_determine_maturity(page_state),
                    value_status=ValueStatusEnum.FINAL,
                    note=source_mode_note,
                ),
            ),
            context_rail=context_rail,
        ),
        meta=meta,
    )


def get_timeline_home(
    view: TimelineViewEnum = TimelineViewEnum.ALL,
    cursor: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=100),
    selected_object_public_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_timeline_home(
        view=view,
        cursor=cursor,
        limit=limit,
        selected_object_public_id=selected_object_public_id,
        current_user=current_user,
        db=db,
        include_optional_capabilities=True,
    )


def get_journal_timeline_home(
    view: str = Query(
        default=TimelineViewEnum.ALL.value,
        json_schema_extra={"enum": ["ALL", "TRADING", "REVIEW", "EXCEPTION"]},
    ),
    cursor: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=100),
    selected_object_public_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Journal-only contract that still returns the stable hard-off for AI."""
    normalized_view = view.strip().upper()
    if normalized_view == TimelineViewEnum.AI.value:
        raise_feature_disabled(RuntimeCapability.AI_INSIGHTS.value)
    try:
        parsed_view = TimelineViewEnum(normalized_view)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Unsupported timeline view") from exc
    return _get_timeline_home(
        view=parsed_view,
        cursor=cursor,
        limit=limit,
        selected_object_public_id=selected_object_public_id,
        current_user=current_user,
        db=db,
        include_optional_capabilities=False,
    )


def build_router(
    *,
    include_ai_contract: bool,
    include_optional_event_contract: bool = False,
) -> APIRouter:
    """Publish a deployment-owned Timeline schema without runtime schema drift."""
    published_router = APIRouter(prefix=TIMELINE_PREFIX, tags=TIMELINE_TAGS)
    if include_ai_contract:
        published_router.add_api_route(
            "/home",
            get_timeline_home,
            methods=["GET"],
            response_model=TimelineHomeResponse,
        )
    elif include_optional_event_contract:
        published_router.add_api_route(
            "/home",
            get_journal_timeline_home,
            methods=["GET"],
            response_model=TimelineHomeResponse,
            response_model_exclude_none=True,
        )
    else:
        published_router.add_api_route(
            "/home",
            get_journal_timeline_home,
            methods=["GET"],
            response_model=JournalTimelineHomeResponse,
            response_model_exclude_none=True,
        )
    return published_router


router = build_router(
    include_ai_contract=is_capability_enabled(RuntimeCapability.AI_INSIGHTS),
    include_optional_event_contract=any(
        is_capability_enabled(capability)
        for capability in (
            RuntimeCapability.MARKET,
            RuntimeCapability.RISK_CARDS,
        )
    ),
)
