from __future__ import annotations

from typing import Any


def _allocation_item_dict(item: Any) -> dict:
    if isinstance(item, dict):
        return {
            "name": item.get("name"),
            "value": float(item.get("value") or 0),
            "percent": float(item.get("percent") or 0),
        }
    return {
        "name": getattr(item, "name", None),
        "value": float(getattr(item, "value", 0) or 0),
        "percent": float(getattr(item, "percent", 0) or 0),
    }


def build_dashboard_allocation_chart_payload(
    *,
    dimension: str,
    data_path: str,
    title: str,
    allocation: list[Any],
) -> dict:
    data = [_allocation_item_dict(item) for item in allocation]
    return {
        "chart_schema": {
            "schema_version": "chart.v1",
            "chart_type": "bar",
            "data_path": data_path,
            "dimensions": [{"field": "name", "label": title}],
            "series": [{"field": "value", "label": "Value"}],
            "options": {"dimension": dimension},
        },
        "data": data,
        "empty_state": {
            "is_empty": len(data) == 0,
            "reason": "NO_ALLOCATION_DATA" if len(data) == 0 else None,
        },
        "trust_meta": {
            "freshness": "FRESH",
            "source": "DASHBOARD_DERIVED_READ_MODEL",
            "source_refs": ["dashboard:stats", f"dashboard:allocation:{dimension}"],
        },
    }


def build_dashboard_chart_payloads(
    *,
    core_type_allocation: list[Any],
    market_allocation: list[Any],
    risk_level_allocation: list[Any],
) -> dict:
    return {
        "core_type": build_dashboard_allocation_chart_payload(
            dimension="CORE_TYPE",
            data_path="core_type_allocation",
            title="Asset type allocation",
            allocation=core_type_allocation,
        ),
        "market": build_dashboard_allocation_chart_payload(
            dimension="MARKET",
            data_path="market_allocation",
            title="Market allocation",
            allocation=market_allocation,
        ),
        "risk_level": build_dashboard_allocation_chart_payload(
            dimension="RISK",
            data_path="risk_level_allocation",
            title="Risk allocation",
            allocation=risk_level_allocation,
        ),
    }


def build_analysis_chart_schema(*, analysis_type: str, raw_data: dict | None) -> dict | None:
    raw_data = raw_data or {}
    if raw_data.get("stats"):
        dimension_label = "Strategy" if analysis_type == "strategy_health" else "Segment"
        return {
            "schema_version": "chart.v1",
            "chart_type": "bar",
            "data_path": "raw_data.stats",
            "dimensions": [{"field": "name", "label": dimension_label}],
            "series": [{"field": "avg_pnl", "label": "Average PnL"}],
            "options": {"analysis_type": analysis_type},
        }
    if analysis_type == "checklist_effect" and (
        raw_data.get("checklist_completed") or raw_data.get("checklist_ignored")
    ):
        return {
            "schema_version": "chart.v1",
            "chart_type": "bar",
            "data_path": "raw_data",
            "dimensions": [{"field": "name", "label": "Checklist state"}],
            "series": [{"field": "avg_pnl", "label": "Average PnL"}],
            "options": {"analysis_type": analysis_type},
        }
    return None
