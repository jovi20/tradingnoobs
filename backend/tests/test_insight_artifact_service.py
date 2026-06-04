from datetime import datetime, timezone

from services.insight_artifact_service import InsightArtifactService


def test_insight_run_artifacts_are_auditable_and_evidence_linked(db_session):
    service = InsightArtifactService(db_session)
    as_of = datetime(2026, 6, 4, tzinfo=timezone.utc)

    run = service.start_run(
        user_id=1,
        run_type="WEEKLY_REVIEW",
        input_refs=["TradingPosition:01JPOSITIONTASK7000000000"],
        prompt_version="weekly-review-v1",
        started_at=as_of,
    )
    artifact = service.add_artifact(
        run_public_id=run.public_id,
        artifact_type="AI_CONCLUSION",
        title="Execution drift improved",
        summary="The user reduced late entries this week.",
        evidence_refs=["01JEVIDENCETASK70000000000"],
        payload={"discipline_score": 0.82},
        chart_schema={
            "schema_version": "chart.v1",
            "chart_type": "bar",
            "x": {"field": "bucket", "label": "Bucket"},
            "y": {"field": "count", "label": "Count"},
            "series": [{"field": "count", "label": "Trades"}],
        },
        trust_meta={
            "as_of": as_of.isoformat(),
            "freshness": "FRESH",
            "source": "AI_GENERATED",
            "maturity": "EARLY_SIGNAL",
            "value_status": "ESTIMATED",
            "generated_by": "insight_artifact_service",
            "source_refs": ["01JEVIDENCETASK70000000000"],
        },
    )

    hydrated = service.get_run_with_artifacts(user_id=1, run_public_id=run.public_id)

    assert run.public_id
    assert artifact.public_id
    assert hydrated["public_id"] == run.public_id
    assert "id" not in hydrated
    assert hydrated["artifacts"][0]["public_id"] == artifact.public_id
    assert hydrated["artifacts"][0]["evidence_refs"] == ["01JEVIDENCETASK70000000000"]
    assert hydrated["artifacts"][0]["chart_schema"]["schema_version"] == "chart.v1"
    assert hydrated["artifacts"][0]["trust_meta"]["source"] == "AI_GENERATED"
