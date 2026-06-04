from datetime import datetime, timezone

from fastapi.testclient import TestClient

from database import get_db
from main import app
from services.auth_service import create_access_token, create_user
from services.insight_artifact_service import InsightArtifactService


def test_v1_insight_runs_expose_auditable_artifacts(db_session):
    user = create_user(db_session, "insight-api@example.com", "strong-password")
    token = create_access_token({"sub": user.public_id})
    service = InsightArtifactService(db_session)
    run = service.start_run(
        user_id=user.id,
        run_type="WEEKLY_REVIEW",
        input_refs=["TradingPosition:01JPOSITIONTASK7000000000"],
        prompt_version="weekly-review-v1",
        started_at=datetime(2026, 6, 4, tzinfo=timezone.utc),
    )
    artifact = service.add_artifact(
        run_public_id=run.public_id,
        artifact_type="AI_CONCLUSION",
        title="Evidence-linked conclusion",
        summary="A concise artifact summary.",
        evidence_refs=["01JEVIDENCETASK70000000000"],
        payload={"discipline_score": 0.82},
        chart_schema={"schema_version": "chart.v1", "chart_type": "bar"},
        trust_meta={
            "as_of": "2026-06-04T00:00:00+00:00",
            "freshness": "FRESH",
            "source": "AI_GENERATED",
            "maturity": "EARLY_SIGNAL",
            "value_status": "ESTIMATED",
            "generated_by": "test",
            "source_refs": ["01JEVIDENCETASK70000000000"],
        },
    )
    db_session.commit()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        list_response = client.get(
            "/api/v1/insights/runs",
            headers={"Authorization": f"Bearer {token}"},
        )
        detail_response = client.get(
            f"/api/v1/insights/runs/{run.public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    runs = list_response.json()
    assert runs[0]["public_id"] == run.public_id
    assert "id" not in runs[0]

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["public_id"] == run.public_id
    assert detail["artifacts"][0]["public_id"] == artifact.public_id
    assert detail["artifacts"][0]["evidence_refs"] == ["01JEVIDENCETASK70000000000"]
    assert detail["artifacts"][0]["chart_schema"]["schema_version"] == "chart.v1"
    assert "id" not in detail["artifacts"][0]
