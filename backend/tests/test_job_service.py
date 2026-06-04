from services.job_service import JobService
from models import IdempotencyKey, JobRun


def test_enqueue_job_reuses_existing_run_for_same_idempotency_key(db_session):
    service = JobService(db_session)

    first = service.enqueue_job(
        job_key="derived.refresh_position",
        payload={"position_public_id": "01JTESTPOSITIONPUBLICID000"},
        idempotency_scope="position-refresh",
        idempotency_key="01JTESTPOSITIONPUBLICID000",
        locked_resource="TradingPosition:01JTESTPOSITIONPUBLICID000",
    )
    second = service.enqueue_job(
        job_key="derived.refresh_position",
        payload={"position_public_id": "01JTESTPOSITIONPUBLICID000"},
        idempotency_scope="position-refresh",
        idempotency_key="01JTESTPOSITIONPUBLICID000",
        locked_resource="TradingPosition:01JTESTPOSITIONPUBLICID000",
    )

    assert second.public_id == first.public_id
    assert db_session.query(IdempotencyKey).count() == 1
    assert db_session.query(JobRun).count() == 1
    assert first.status == "QUEUED"
    assert first.locked_resource == "TradingPosition:01JTESTPOSITIONPUBLICID000"


def test_job_status_returns_public_contract_with_event_lines(db_session):
    service = JobService(db_session)
    run = service.enqueue_job(
        job_key="insights.generate",
        payload={"run_type": "WEEKLY_REVIEW"},
        idempotency_scope="insight-run",
        idempotency_key="01JINSIGHTJOBTASK700000000",
        locked_resource="InsightRun:01JINSIGHTJOBTASK700000000",
    )

    status = service.get_job_run_status(job_run_public_id=run.public_id)

    assert status["public_id"] == run.public_id
    assert "id" not in status
    assert status["status"] == "QUEUED"
    assert status["job_key"] == "insights.generate"
    assert status["events"][0]["event_type"] == "QUEUED"
    assert "id" not in status["events"][0]
